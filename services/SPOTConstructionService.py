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

        # 🔥 SCalc activo (UNO SOLO)
        self.active_scalc = self._extract_active_scalc()
        self.active_crl_amt = self._extract_active_crl_amt()

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
    # 🔥 SCALC (PPM) REAL
    # =========================
    def _extract_scalc_skew(self, amt: int) -> Dict[str, Any]:
        """
        Extrae información de skew desde SCalc.

        Regla:
        - Se intenta hacer match contra crlAmt == amt
        - Si no existe crlAmt (caso PPM), se devuelve skew neutro
        - NUNCA rompe el flujo (siempre devuelve dict)
        """

        client_prc = self.scp.get("clientPrc", [])

        # Seguridad total
        if not isinstance(client_prc, list):
            return {
                "aAutoSkew": None,
                "uBidTrSpot": None,
                "uAskTrSpot": None
            }

        for entry in client_prc:
            if not isinstance(entry, dict):
                continue

            scalc = entry.get("SCalc")
            if not isinstance(scalc, dict):
                continue

            # 🔹 Caso CRL rung → match por crlAmt
            crl_amt = scalc.get("crlAmt")
            if crl_amt is not None:
                try:
                    if int(Decimal(crl_amt)) != int(amt):
                        continue
                except Exception:
                    continue

            # 🔹 Caso PPM (no tiene crlAmt): no aplicar skew
            return {
                "aAutoSkew": scalc.get("aAutoSkew"),
                "uBidTrSpot": scalc.get("uBidTrSpot"),
                "uAskTrSpot": scalc.get("uAskTrSpot")
            }

        # 🔚 Fallback seguro
        return {
            "aAutoSkew": None,
            "uBidTrSpot": None,
            "uAskTrSpot": None
        }

    def _extract_active_scalc(self) -> Dict[str, Any] | None:
        for entry in self.scp.get("clientPrc", []):
            scalc = entry.get("SCalc")
            if isinstance(scalc, dict) and scalc.get("__type__") == "PPM":
                return scalc
        return None

    def _extract_active_crl_amt(self) -> int | None:
        if not self.active_scalc:
            return None
        try:
            return int(Decimal(self.active_scalc.get("crlAmt")))
        except Exception:
            return None

    # =========================
    # SKEW APPLY
    # =========================

    def _apply_skew_price(
        self,
        price_after_min_spread: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Regla REAL:
        - aAutoSkew == 0 o None → hereda priceAfterMinSpread
        - aAutoSkew != 0 → usa uBidTrSpot / uAskTrSpot
        """
        if not self.active_scalc:
            return price_after_min_spread

        a_auto = self.active_scalc.get("aAutoSkew")
        if a_auto in (None, 0, "0"):
            return price_after_min_spread

        bid = self.active_scalc.get("uBidTrSpot")
        ask = self.active_scalc.get("uAskTrSpot")

        if bid is None or ask is None:
            return price_after_min_spread

        return {
            "bid": format(Decimal(bid), "f"),
            "ask": format(Decimal(ask), "f")
        }

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

            price_adjustment = self._apply_adjustment(core, adjustment)
            mid_spread = self._calculate_mid_and_spread(price_adjustment)
            scalc_skew = self._extract_scalc_skew(amt) or {}
            rm_info = self._extract_rung_modifier(amt)

            price_after_rm = self._apply_rung_modifier_price(
                mid_spread,
                rm_info["RMType"],
                rm_info["RMValue"],
                fallback_price=price_adjustment
            )

            effective_min_spread = self._calculate_effective_min_spread(
                adjustment,
                rm_info["RMMin"]
            )

            price_after_min_spread = self._apply_min_spread(
                price_after_rm,
                effective_min_spread
            )

            # 🔥 SOLO EL RUNG ACTIVO TIENE SKEW / VOLUME
            if self.active_crl_amt and amt == self.active_crl_amt:
                price_after_skew = self._apply_skew_price(price_after_min_spread)
                a_auto_skew = self.active_scalc.get("aAutoSkew")
                skew_meta = self._extract_skew()
                volume_adj = self._extract_volume_adjustment()
            else:
                price_after_skew = price_after_min_spread
                a_auto_skew = None
                skew_meta = None
                volume_adj = None

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
                "priceAfterMinSpread": price_after_min_spread,

                "skew": self._extract_skew(),
                "aAutoSkew": scalc_skew.get("aAutoSkew"),
                "priceAfterSkew": price_after_skew,

                "volumeAdjustment": self._extract_volume_adjustment()
            })

        return result

    # =========================
    # META
    # =========================

    def _extract_volume_adjustment(self) -> Dict[str, Any]:
        tmu = self.scp.get("tmu", {})

        return {
            "package": tmu.get("package"),
            "applied": bool(tmu.get("package"))
        }

    def _extract_skew(self) -> Dict[str, Any]:
        skew = self.scp.get("skew", {})

        return {
            "package": skew.get("pkg"),
            "bPos": skew.get("bPos")
        }

    # =========================
    # CORE / TOM / RM / MATH
    # =========================

    def _apply_adjustment(self, core, adjustment):
        bid = Decimal(core["bid"])
        ask = Decimal(core["ask"])
        if adjustment:
            bid += Decimal(adjustment.get("bidSpread", "0"))
            ask += Decimal(adjustment.get("askSpread", "0"))
        return {"bid": format(bid, "f"), "ask": format(ask, "f")}

    def _extract_core_rungs(self):
        return [{
            "amt": int(r["amt"]),
            "core": {
                "bid": str(Decimal(r["bidPrice"])),
                "ask": str(Decimal(r["askPrice"]))
            }
        } for r in self.scp.get("crl", {}).get("rungs", [])]

    def _index_tom_rungs(self):
        return {int(r["amt"]): r for r in self.scp.get("tom", {}).get("rungs", [])}

    def _extract_volatility_scenario(self):
        return {"N": "Normal", "A": "Active", "B": "Busy", "F": "Fast"}.get(
            self.scp.get("tom", {}).get("mktMode", "N"), "Normal"
        )

    def _get_active_rung_position(self, amt):
        for i, r in enumerate(self.scp.get("crl", {}).get("rungs", []), 1):
            if int(r["amt"]) == amt:
                return i
        return 1

    def _extract_rung_modifier(self, amt):
        tmu = self.scp.get("tmu", {})
        rms = tmu.get("rungmodifiers", {}).get(
            self.scp.get("tom", {}).get("mktMode", "N")
        )
        if not tmu.get("package") or not rms:
            return dict.fromkeys(["rungModifier", "RMValue", "RMType", "RMMin"])

        pos = self._get_active_rung_position(amt)
        for rm in rms:
            if rm.get("rung") == pos:
                return {
                    "rungModifier": f"{tmu.get('package')}_FA (Rung {pos} {rm['type']} {rm['value']})",
                    "RMValue": str(rm["value"]),
                    "RMType": rm["type"],
                    "RMMin": str(rm["min"]) if rm.get("min") else None
                }
        return dict.fromkeys(["rungModifier", "RMValue", "RMType", "RMMin"])

    def _apply_rung_modifier_price(self, mid_spread, rm_type, rm_value, fallback_price):
        if not rm_type or not rm_value:
            return fallback_price
        mid = Decimal(mid_spread["mid"])
        spread = Decimal(mid_spread["spread"])
        rm = Decimal(rm_value)
        spread_adj = spread + rm if rm_type == "ADDITIVE" else spread * rm
        return {
            "bid": format(mid - spread_adj / 2, "f"),
            "ask": format(mid + spread_adj / 2, "f")
        }

    def _calculate_effective_min_spread(self, tom_adj, rm_min):
        tom_min = Decimal(tom_adj.get("minSpread")) if tom_adj else Decimal("0")
        rm_min = Decimal(rm_min) if rm_min else Decimal("0")
        return format(max(tom_min, rm_min), "f")

    def _apply_min_spread(self, price, min_spread):
        bid = Decimal(price["bid"])
        ask = Decimal(price["ask"])
        if ask - bid >= Decimal(min_spread):
            return price
        mid = (bid + ask) / 2
        return {
            "bid": format(mid - Decimal(min_spread) / 2, "f"),
            "ask": format(mid + Decimal(min_spread) / 2, "f")
        }

    def _calculate_mid_and_spread(self, price):
        bid = Decimal(price["bid"])
        ask = Decimal(price["ask"])
        return {
            "mid": format((bid + ask) / 2, "f"),
            "spread": format(ask - bid, "f")
        }
