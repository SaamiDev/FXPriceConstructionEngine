from decimal import Decimal
from typing import Dict, Any


class SpotAuditExplainService:
    """
    Genera un explain de auditoría del desglose spot.
    Describe paso a paso los cálculos realizados, incluyendo
    fórmulas, valores intermedios y decisiones de aplicación.
    """

    def __init__(self, context: Dict[str, Any], notional: Dict[str, Any], rung: Dict[str, Any]):
        self.context = context
        self.notional = notional
        self.rung = rung

    # =========================================================
    # PUBLIC
    # =========================================================

    def build(self) -> str:
        sections = [
            self._context_section(),
            self._rung_selection_section(),
            self._spot_core_section(),
            self._tom_adjustment_section(),
            self._mid_spread_section(),
            self._rung_modifier_section(),
            self._min_spread_section(),
            self._final_price_section()
        ]
        return "\n\n".join(s for s in sections if s)

    # =========================================================
    # SECTIONS
    # =========================================================

    def _context_section(self) -> str:
        return (
            "CONTEXT\n"
            "-------\n"
            f"Se ha construido el precio para el par {self.context.get('ccyPair')} "
            f"bajo el modelo {self.context.get('prcModel')}.\n"
            f"El escenario de mercado aplicado es '{self.rung.get('volatilityScenario')}'."
        )

    def _rung_selection_section(self) -> str:
        return (
            "RUNG SELECTION\n"
            "--------------\n"
            f"Notional cliente = {self.notional.get('amount')}.\n"
            f"Se selecciona el Rung con importe {self._fmt(self.rung.get('amt'))}, "
            "al ser el primer rung cuyo nominal es mayor o igual al notional del cliente."
        )

    def _spot_core_section(self) -> str:
        core = self.rung.get("core", {})
        return (
            "SPOT CORE (CRL)\n"
            "---------------\n"
            "Precio base obtenido desde CRL:\n"
            f"Bid_core = {core.get('bid')}\n"
            f"Ask_core = {core.get('ask')}\n"
            "Este precio no incluye ajustes de mercado (TOM) ni comerciales (RM)."
        )

    def _tom_adjustment_section(self) -> str:
        adj = self.rung.get("adjustment")
        pa = self.rung.get("priceAdjustment") or {}
        core = self.rung.get("core", {})

        if not adj or not pa:
            return (
                "TOM ADJUSTMENT\n"
                "--------------\n"
                "No existen ajustes TOM configurados para este rung."
            )

        bid_core = self._safe_decimal(core.get("bid"))
        ask_core = self._safe_decimal(core.get("ask"))
        bid_spread = self._safe_decimal(adj.get("bidSpread"))
        ask_spread = self._safe_decimal(adj.get("askSpread"))

        bid_adj = self._safe_decimal(pa.get("bid"))
        ask_adj = self._safe_decimal(pa.get("ask"))

        return (
            "TOM ADJUSTMENT\n"
            "--------------\n"
            "Cálculo del precio ajustado con spreads TOM:\n\n"
            "Bid_adj = Bid_core + BidSpread\n"
            f"        = {bid_core} + {bid_spread}\n"
            f"        = {bid_adj}\n\n"
            "Ask_adj = Ask_core + AskSpread\n"
            f"        = {ask_core} + {ask_spread}\n"
            f"        = {ask_adj}"
        )

    def _mid_spread_section(self) -> str:
        pa = self.rung.get("priceAdjustment") or {}
        ms = self.rung.get("midSpread") or {}

        if not pa or not ms:
            return None

        bid = self._safe_decimal(pa.get("bid"))
        ask = self._safe_decimal(pa.get("ask"))
        mid = ms.get("mid")
        spread = ms.get("spread")

        return (
            "MID / SPREAD\n"
            "------------\n"
            "Cálculo del Mid y Spread a partir del precio ajustado:\n"
            "Mid = (Bid_adj + Ask_adj) / 2\n"
            f"    = ({bid} + {ask}) / 2\n"
            f"    = {mid}\n\n"
            "Spread = Ask_adj - Bid_adj\n"
            f"       = {ask} - {bid}\n"
            f"       = {spread}"
        )

    def _rung_modifier_section(self) -> str:
        rm = self.rung.get("rungModifier")
        rm_type = self.rung.get("RMType")
        rm_value = self._safe_decimal(self.rung.get("RMValue"))
        pa_rm = self.rung.get("priceAfterRungModifier")
        ms = self.rung.get("midSpread") or {}

        if not rm:
            return (
                "RUNG MODIFIER\n"
                "-------------\n"
                "No existe ningún Rung Modifier configurado para este rung."
            )

        if not isinstance(pa_rm, dict):
            return (
                "RUNG MODIFIER\n"
                "-------------\n"
                f"Rung Modifier configurado:\n{rm}\n"
                "El modificador no se ha aplicado al precio."
            )

        mid = self._safe_decimal(ms.get("mid"))
        spread = self._safe_decimal(ms.get("spread"))

        # =========================
        # ADDITIVE
        # =========================
        if rm_type == "ADDITIVE":
            new_spread = spread + rm_value
            half = new_spread / 2

            return (
                "RUNG MODIFIER\n"
                "-------------\n"
                f"Rung Modifier activo:\n{rm}\n"
                "Tipo de modificador: ADDITIVE\n"
                f"Valor aplicado = {rm_value}\n\n"

                "Fórmula aplicada:\n"
                "BID = Mid – ((Spread + RMValue) / 2)\n"
                "ASK = Mid + ((Spread + RMValue) / 2)\n\n"

                "Sustitución de valores:\n"
                f"BID = {mid} – (({spread} + {rm_value}) / 2)\n"
                f"ASK = {mid} + (({spread} + {rm_value}) / 2)\n\n"

                "Cálculo intermedio:\n"
                f"(Spread + RMValue) = {new_spread}\n"
                f"(Spread + RMValue) / 2 = {half}\n\n"

                "Resultado:\n"
                f"Bid_RM = {pa_rm.get('bid')}\n"
                f"Ask_RM = {pa_rm.get('ask')}"
            )

        # =========================
        # MULTIPLY
        # =========================
        if rm_type == "MULTIPLY":
            new_spread = rm_value * spread
            half = new_spread / 2

            return (
                "RUNG MODIFIER\n"
                "-------------\n"
                f"Rung Modifier activo:\n{rm}\n"
                "Tipo de modificador: MULTIPLY\n"
                f"Valor aplicado = {rm_value}\n\n"

                "Fórmula aplicada:\n"
                "BID = Mid – ((RMValue × Spread) / 2)\n"
                "ASK = Mid + ((RMValue × Spread) / 2)\n\n"

                "Sustitución de valores:\n"
                f"BID = {mid} – (({rm_value} × {spread}) / 2)\n"
                f"ASK = {mid} + (({rm_value} × {spread}) / 2)\n\n"

                "Cálculo intermedio:\n"
                f"(RMValue × Spread) = {new_spread}\n"
                f"(RMValue × Spread) / 2 = {half}\n\n"

                "Resultado:\n"
                f"Bid_RM = {pa_rm.get('bid')}\n"
                f"Ask_RM = {pa_rm.get('ask')}"
            )

        return (
            "RUNG MODIFIER\n"
            "-------------\n"
            f"Rung Modifier configurado:\n{rm}\n"
            "Tipo no reconocido. No se aplica ajuste."
        )

    def _min_spread_section(self) -> str:
        min_spread = self.rung.get("minSpread")
        pa_rm = self.rung.get("priceAfterRungModifier")

        if not min_spread or not isinstance(pa_rm, dict):
            return None

        bid_rm = self._safe_decimal(pa_rm.get("bid"))
        ask_rm = self._safe_decimal(pa_rm.get("ask"))
        spread_rm = ask_rm - bid_rm
        min_spread_d = self._safe_decimal(min_spread)

        if spread_rm < min_spread_d:
            pa_ms = self.rung.get("priceAfterMinSpread") or {}
            return (
                "MIN SPREAD\n"
                "----------\n"
                f"Spread_RM = Ask_RM - Bid_RM = {spread_rm}\n"
                f"MinSpread configurado = {min_spread_d}\n\n"
                "Dado que Spread_RM < MinSpread, se fuerza el spread mínimo:\n"
                f"Bid_final = {pa_ms.get('bid')}\n"
                f"Ask_final = {pa_ms.get('ask')}"
            )

        return (
            "MIN SPREAD\n"
            "----------\n"
            f"Spread_RM = Ask_RM - Bid_RM = {spread_rm}\n"
            f"MinSpread configurado = {min_spread_d}\n\n"
            "Dado que Spread_RM ≥ MinSpread, no es necesario aplicar ajuste adicional.\n"
            "El precio se mantiene."
        )

    def _final_price_section(self) -> str:
        final_price = (
            self.rung.get("priceAfterMinSpread")
            or self.rung.get("priceAfterRungModifier")
            or self.rung.get("priceAdjustment")
            or {}
        )

        return (
            "FINAL PRICE\n"
            "-----------\n"
            "Precio final tras aplicar todas las reglas:\n"
            f"Final Bid = {final_price.get('bid')}\n"
            f"Final Ask = {final_price.get('ask')}"
        )

    # =========================================================
    # HELPERS
    # =========================================================

    @staticmethod
    def _fmt(value) -> str:
        try:
            return f"{int(value):,}".replace(",", ".")
        except Exception:
            return str(value)

    @staticmethod
    def _safe_decimal(value, default="0") -> Decimal:
        try:
            if value is None:
                return Decimal(default)
            return Decimal(str(value))
        except Exception:
            return Decimal(default)