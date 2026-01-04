import re
from decimal import Decimal, getcontext

# Precisión suficiente para FX / spreads
getcontext().prec = 18


# ================= SERIALIZER =================

def decimal_serializer(obj):
    if isinstance(obj, Decimal):
        return format(obj, "f")  # sin notación científica
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# ================= NORMALIZADOR =================

_DECIMAL_EU_RE = re.compile(r'(\d+),(\d+)')


def normalize_numbers(val: str) -> str:
    """
    Convierte decimales europeos a formato estándar:
    0,80173  -> 0.80173
    17660840,23 -> 17660840.23
    """
    return _DECIMAL_EU_RE.sub(r'\1.\2', val)

def normalize_key(key: str) -> str:
    return key.replace("\n", "").replace("\r", "").replace(" ", "")

# ================= ATOMS =================

def parse_atom(val: str):
    val = val.strip()

    # Normalizar decimales europeos
    val = normalize_numbers(val)

    # Booleanos Java-style
    if val in ("T", "F"):
        return val == "T"

    # Booleanos string
    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False

    # null
    if val == "null":
        return None

    # amount:Q
    if re.match(r'^\d+(\.\d+)?:\s*[A-Z]$', val):
        amt, side = val.split(":")
        return {
            "amount": Decimal(amt.strip()),
            "side": side.strip()
        }

    # Números (Decimal siempre que haya punto)
    try:
        if "." in val or "e" in val.lower():
            return Decimal(val)
        return int(val)
    except Exception:
        return val


# ================= HELPERS =================

def split_top_level(s: str, sep=","):
    """
    Divide una cadena solo por separadores de nivel 0
    (respeta [], {})
    """
    parts = []
    buf = ""
    depth = 0

    for c in s:
        if c in "[{":
            depth += 1
        elif c in "]}":
            depth -= 1

        if c == sep and depth == 0:
            parts.append(buf.strip())
            buf = ""
        else:
            buf += c

    if buf.strip():
        parts.append(buf.strip())

    return parts


# ================= PARSING =================

def parse_value(val: str):
    val = val.strip()

    # Normalizar números ANTES de procesar estructura
    val = normalize_numbers(val)

    # Map estilo {a=b, c=d}
    if val.startswith("{") and val.endswith("}"):
        return parse_map(val[1:-1])

    # Contenedor [...]
    if val.startswith("[") and val.endswith("]"):
        inner = split_top_level(val[1:-1])

        has_block = any(
            re.match(r'^\w+\s*\[', item.strip())
            for item in inner
        )

        has_kv_only = all(
            "=" in item and not re.match(r'^\w+\s*\[', item.strip())
            for item in inner
        )

        # Lista de bloques (SCPDetails, Rung, etc.)
        if has_block:
            return [parse_value(item) for item in inner]

        # Mapa key=value
        if has_kv_only:
            obj = {}
            for item in inner:
                k, v = item.split("=", 1)
                obj[k.strip()] = parse_value(v.strip())
            return obj

        # Lista simple
        return [parse_value(item) for item in inner]

    # Bloque Class [...]
    if re.match(r'^\w+\s*\[', val):
        return parse_block(val)

    # Valor atómico
    return parse_atom(val)


def parse_map(s: str):
    result = {}
    for part in split_top_level(s):
        if "=" in part:
            k, v = part.split("=", 1)
            k = normalize_key(k.strip())   # 🔥 AQUÍ
            result[k] = parse_value(v.strip())
    return result



def parse_block(s: str):
    s = s.strip()

    m = re.match(r'^(\w+)\s*\[(.*)\]$', s, re.DOTALL)
    if not m:
        return s

    cls, body = m.groups()
    result = {"__type__": cls}

    for part in split_top_level(body):
        if "=" in part:
            k, v = part.split("=", 1)
            k = normalize_key(k.strip())   # 🔥 AQUÍ
            result[k] = parse_value(v.strip())

    return result
