import re
from decimal import Decimal, getcontext

# Precisión suficiente para FX / spreads
getcontext().prec = 18

def decimal_serializer(obj):
    if isinstance(obj, Decimal):
        return format(obj, "f")  # sin notación científica
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

# -------------------- ATOMS --------------------

def parse_atom(val: str):
    val = val.strip()

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

    # Números (usar Decimal para evitar notación científica)
    try:
        if "." in val or "e" in val.lower():
            return Decimal(val)
        return int(val)
    except Exception:
        return val


# -------------------- HELPERS --------------------

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


# -------------------- PARSING --------------------

def parse_value(val: str):
    val = val.strip()

    # Map estilo {a=b, c=d}
    if val.startswith("{") and val.endswith("}"):
        return parse_map(val[1:-1])

    # Contenedor [...]
    if val.startswith("[") and val.endswith("]"):
        inner = split_top_level(val[1:-1])

        # Detectar bloques tipo Class [...]
        has_block = any(
            re.match(r'^\w+\s*\[', item.strip())
            for item in inner
        )

        # Detectar key=value puro (no bloque)
        has_kv_only = all(
            "=" in item and not re.match(r'^\w+\s*\[', item.strip())
            for item in inner
        )

        # LISTA de bloques (SCPDetails, Rung, etc.)
        if has_block:
            return [parse_value(item) for item in inner]

        # MAPA key=value (XCalc, etc.)
        if has_kv_only:
            obj = {}
            for item in inner:
                k, v = item.split("=", 1)
                obj[k.strip()] = parse_value(v.strip())
            return obj

        # Fallback: lista simple
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
            result[k.strip()] = parse_value(v.strip())
    return result


def parse_block(s: str):
    """
    Parsea ClassName[ ... ] → dict con __type__
    """
    m = re.match(r'^(\w+)\s*\[(.*)\]$', s.strip(), re.DOTALL)
    if not m:
        return s

    cls, body = m.groups()
    result = {"__type__": cls}

    for part in split_top_level(body):
        if "=" in part:
            k, v = part.split("=", 1)
            result[k.strip()] = parse_value(v.strip())

    return result
