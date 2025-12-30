import os
import json
from decimal import Decimal
from typing import Dict, Any, List


class SPOTConstructionService:

    def __init__(self, parsed_scp: Dict[str, Any], base_path: str):
        if not parsed_scp or "__type__" not in parsed_scp:
            raise ValueError("SCP inválido o no parseado")

        self.scp = parsed_scp
        self.key = parsed_scp.get("key", {})
        self.base_path = base_path

    # =========================
    # PUBLIC
    # =========================

    def build(self) -> Dict[str, Any]:
        return {
            "context": self._extract_context(),
            "client": self._extract_client(),
            "notional": self._extract_notional(),
            "rungs": self._extract_rungs_with_adjustments()
        }

    def save(self) -> str:
        scp_id = self.scp.get("id")
        if not scp_id:
            raise ValueError("El SCP no tiene ID")

        output_dir = os.path.join(
            self.base_path,
            "resources",
            "scp",
            "spot_construction"
        )
        os.makedirs(output_dir, exist_ok=True)

        output_path = os.path.join(output_dir, f"{scp_id}.json")

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.build(), f, indent=2, ensure_ascii=False)

        return output_path

    # =========================
    # EXTRACTORS
    # =========================

    def _extract_context(self) -> Dict[str, Any]:
        return {
            "ccyPair": self.key.get("ccyPair"),
            "venue": self.key.get("venue"),
            "group": self.key.get("group"),
            "smType": self.key.get("smType"),
            "prcModel": self.key.get("prcModel"),
            "priceCompetition": self.key.get("priceCompetition"),
        }

    def _extract_client(self) -> Dict[str, Any]:
        return {
            "venueClientId": self.key.get("venueClientId"),
            "venueAccountId": self.key.get("venueAccountId"),
            "venueUserId": self.key.get("venueUserId"),
        }

    def _extract_notional(self) -> Dict[str, Any]:
        notional = self.key.get("notional")
        if not notional:
            return {"amount": None, "side": None}

        return {
            "amount": str(notional.get("amount")),
            "side": notional.get("side"),
        }

    # =========================
    # RUNG LOGIC
    # =========================

    def _extract_rungs_with_adjustments(self) -> List[Dict[str, Any]]:
        core_rungs = self._extract_core_rungs()
        tom_index = self._index_tom_rungs()

        result = []

        for rung in core_rungs:
            amt = rung["amt"]
            core = rung["core"]
            tom = tom_index.get(amt)

            adjustment = None
            if tom:
                adjustment = {
                    "bidSpread": str(tom.get("bidSpread", "0")),
                    "askSpread": str(tom.get("askSpread", "0")),
                    "minSpread": str(tom.get("minSpread", "0")),
                    "source": "TOM"
                }

            # --- PRICE ADJ (CRL + TOM)
            price_adjustment = self._apply_adjustment(core, adjustment)

            # --- MID / SPREAD
            mid_spread = self._calculate_mid_and_spread(price_adjustment)

            # --- RUNG MODIFIER METADATA
            rm_info = self._extract_rung_modifier(amt)

            # --- PRICE AFTER RM (HEREDA SI NO HAY RM)
            price_after_rm = self._apply_rung_modifier_price(
                mid_spread,
                rm_info["RMType"],
                rm_info["RMValue"],
                fallback_price=price_adjustment
            )

            # --- MIN SPREAD EFECTIVO
            effective_min_spread = self._calculate_effective_min_spread(
                adjustment,
                rm_info["RMMin"]
            )

            # --- PRICE AFTER MIN SPREAD (HEREDA SI NO SE FUERZA)
            price_after_min_spread = self._apply_min_spread(
                price_after_rm,
                effective_min_spread
            )

            result.append({
                "amt": amt,
                "core": core,
                "adjustment": adjustment,
                "priceAdjustment": price_adjustment,
                "midSpread": mid_spread,
                "volatilityScenario": self._extract_volatility_scenario(),

                "rungModifier": rm_info["rungModifier"],
                "RMValue": rm_info["RMValue"],
                "RMType": rm_info["RMType"],
                "RMMin": rm_info["RMMin"],

                "priceAfterRungModifier": price_after_rm,
                "minSpread": effective_min_spread,
                "priceAfterMinSpread": price_after_min_spread
            })

        return result

    # =========================
    # PRICE ADJUSTMENT (TOM)
    # =========================

    def _apply_adjustment(self, core: Dict[str, str], adjustment: Dict[str, Any] | None) -> Dict[str, str]:
        bid = Decimal(core["bid"])
        ask = Decimal(core["ask"])

        if adjustment:
            bid += Decimal(adjustment.get("bidSpread", "0"))
            ask += Decimal(adjustment.get("askSpread", "0"))

        return {"bid": format(bid, "f"), "ask": format(ask, "f")}

    # =========================
    # CORE (CRL)
    # =========================

    def _extract_core_rungs(self) -> List[Dict[str, Any]]:
        rungs_data = []
        crl = self.scp.get("crl")
        if not crl:
            return rungs_data

        for rung in crl.get("rungs", []):
            try:
                rungs_data.append({
                    "amt": int(rung["amt"]),
                    "core": {
                        "bid": str(Decimal(rung["bidPrice"])),
                        "ask": str(Decimal(rung["askPrice"]))
                    }
                })
            except Exception:
                continue

        return rungs_data

    # =========================
    # TOM
    # =========================

    def _index_tom_rungs(self) -> Dict[int, Dict[str, Any]]:
        tom = self.scp.get("tom")
        if not tom:
            return {}

        index = {}
        for rung in tom.get("rungs", []):
            try:
                index[int(rung["amt"])] = rung
            except Exception:
                continue
        return index

    def _extract_volatility_scenario(self) -> str:
        return {
            "N": "Normal",
            "A": "Active",
            "B": "Busy",
            "F": "Fast"
        }.get(self.scp.get("tom", {}).get("mktMode", "N"), "Normal")

    # =========================
    # RUNG MODIFIER
    # =========================

    def _get_active_rung_position(self, amt: int) -> int:
        for idx, r in enumerate(self.scp.get("crl", {}).get("rungs", []), start=1):
            if int(r.get("amt")) == amt:
                return idx
        return 1

    def _extract_rung_modifier(self, amt: int) -> Dict[str, Any]:
        tmu = self.scp.get("tmu", {})
        scenario = self.scp.get("tom", {}).get("mktMode", "N")
        rms = tmu.get("rungmodifiers", {}).get(scenario)

        if not tmu.get("package") or not rms:
            return {
                "rungModifier": None,
                "RMValue": None,
                "RMType": None,
                "RMMin": None
            }

        rung_pos = self._get_active_rung_position(amt)

        for rm in rms:
            if rm.get("rung") == rung_pos:
                return {
                    "rungModifier": (
                        f"{tmu.get('package')}_{scenario}_FA "
                        f"(Rung {rung_pos} {rm.get('type')} {rm.get('value')})"
                    ),
                    "RMValue": str(rm.get("value")),
                    "RMType": rm.get("type"),
                    "RMMin": str(rm.get("min")) if rm.get("min") not in (None, 0, "0") else None
                }

        return {
            "rungModifier": None,
            "RMValue": None,
            "RMType": None,
            "RMMin": None
        }

    # =========================
    # PRICE AFTER RUNG MODIFIER
    # =========================

    def _apply_rung_modifier_price(
            self,
            mid_spread,
            rm_type,
            rm_value,
            fallback_price
    ):
        """
        Regla:
        - Si NO hay rung modifier → HEREDA priceAdjustment
        - Estamos en SPOT logic siempre
        """

        # ✅ NO RM → herencia directa y explícita
        if rm_type is None or rm_value is None:
            return {
                "bid": fallback_price["bid"],
                "ask": fallback_price["ask"]
            }

        mid = Decimal(mid_spread["mid"])
        spread = Decimal(mid_spread["spread"])
        rm_val = Decimal(rm_value)

        adjusted_spread = (
            spread + rm_val if rm_type == "ADDITIVE"
            else spread * rm_val
        )

        return {
            "bid": format(mid - adjusted_spread / 2, "f"),
            "ask": format(mid + adjusted_spread / 2, "f")
        }

    # =========================
    # MIN SPREAD
    # =========================

    def _calculate_effective_min_spread(self, tom_adj, rm_min):
        tom_min = Decimal(tom_adj.get("minSpread")) if tom_adj and tom_adj.get("minSpread") else Decimal("0")
        rm_min_val = Decimal(rm_min) if rm_min else Decimal("0")
        eff = max(tom_min, rm_min_val)
        return format(eff, "f")  # 🔥 nunca None

    def _apply_min_spread(self, price, min_spread):
        if Decimal(min_spread) == 0:
            return price

        bid = Decimal(price["bid"])
        ask = Decimal(price["ask"])
        min_sp = Decimal(min_spread)

        if ask - bid >= min_sp:
            return price

        mid = (bid + ask) / 2
        return {
            "bid": format(mid - min_sp / 2, "f"),
            "ask": format(mid + min_sp / 2, "f")
        }

    # =========================
    # MID / SPREAD
    # =========================

    def _calculate_mid_and_spread(self, price):
        bid = Decimal(price["bid"])
        ask = Decimal(price["ask"])
        mid = (bid + ask) / 2
        return {
            "mid": format(mid, "f"),
            "spread": format(ask - bid, "f")
        }