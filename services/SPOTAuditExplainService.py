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
        pa = self.rung.get("priceAdjustment", {})
        core = self.rung.get("core", {})

        if not adj:
            return (
                "TOM ADJUSTMENT\n"
                "--------------\n"
                "No existen ajustes TOM configurados para este rung."
            )

        bid_core = Decimal(core.get("bid"))
        ask_core = Decimal(core.get("ask"))
        bid_spread = Decimal(str(adj.get("bidSpread", "0")))
        ask_spread = Decimal(str(adj.get("askSpread", "0")))

        bid_adj = Decimal(pa.get("bid"))
        ask_adj = Decimal(pa.get("ask"))

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
        ms = self.rung.get("midSpread", {})
        bid = Decimal(self.rung["priceAdjustment"]["bid"])
        ask = Decimal(self.rung["priceAdjustment"]["ask"])

        return (
            "MID / SPREAD\n"
            "------------\n"
            "Cálculo del Mid y Spread a partir del precio ajustado:\n"
            f"Mid = (Bid_adj + Ask_adj) / 2\n"
            f"    = ({bid} + {ask}) / 2\n"
            f"    = {ms.get('mid')}\n\n"
            f"Spread = Ask_adj - Bid_adj\n"
            f"       = {ask} - {bid}\n"
            f"       = {ms.get('spread')}"
        )

    def _rung_modifier_section(self) -> str:
        rm = self.rung.get("rungModifier")
        rm_value = Decimal(str(self.rung.get("RMValue", "0")))
        pa_rm = self.rung.get("priceAfterRungModifier")
        ms = self.rung.get("midSpread", {})

        if not rm or not pa_rm:
            return (
                "RUNG MODIFIER\n"
                "-------------\n"
                "No existe ningún Rung Modifier activo para este escenario."
            )

        spread = Decimal(str(ms.get("spread")))
        spread_rm = spread * rm_value

        return (
            "RUNG MODIFIER\n"
            "-------------\n"
            f"Rung Modifier activo:\n{rm}\n"
            f"Valor aplicado = {rm_value}\n\n"
            "Tipo de modificador: MULTIPLY\n"
            "El spread se ajusta multiplicándolo por el factor configurado:\n\n"
            f"Spread_RM = Spread * RMValue\n"
            f"          = {spread} * {rm_value}\n"
            f"          = {spread_rm}\n\n"
            "El precio se recalcula de forma simétrica alrededor del Mid:\n"
            "Bid_RM = Mid - (Spread_RM / 2)\n"
            "Ask_RM = Mid + (Spread_RM / 2)\n\n"
            "Resultado:\n"
            f"- Bid_RM = {pa_rm.get('bid')}\n"
            f"- Ask_RM = {pa_rm.get('ask')}"
        )

    def _min_spread_section(self) -> str:
        min_spread = self.rung.get("minSpread")
        pa_rm = self.rung.get("priceAfterRungModifier")

        if not min_spread or not pa_rm:
            return None

        bid_rm = Decimal(pa_rm["bid"])
        ask_rm = Decimal(pa_rm["ask"])
        spread_rm = ask_rm - bid_rm
        min_spread_d = Decimal(str(min_spread))

        if spread_rm < min_spread_d:
            pa_ms = self.rung.get("priceAfterMinSpread")
            return (
                "MIN SPREAD\n"
                "----------\n"
                f"Spread_RM = Ask_RM - Bid_RM = {spread_rm}\n"
                f"MinSpread configurado = {min_spread_d}\n\n"
                "Dado que Spread_RM < MinSpread, se recalcula el precio alrededor del Mid:\n"
                f"- Bid_final = {pa_ms.get('bid')}\n"
                f"- Ask_final = {pa_ms.get('ask')}"
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