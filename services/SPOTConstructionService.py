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
            json.dump(
                self.build(),
                f,
                indent=2,
                ensure_ascii=False,
                default=str
            )

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
                    "bidSpread": str(tom.get("bidSpread")),
                    "askSpread": str(tom.get("askSpread")),
                    "minSpread": str(tom.get("minSpread")),
                    "source": "TOM"
                }

            price_adjustment = self._apply_adjustment(core, adjustment)

            mid_spread = self._calculate_mid_and_spread(price_adjustment)

            result.append({
                "amt": amt,
                "core": core,
                "adjustment": adjustment,
                "priceAdjustment": price_adjustment,
                "midSpread": mid_spread
            })

        return result

    def _apply_adjustment(
        self,
        core: Dict[str, str],
        adjustment: Dict[str, Any] | None
    ) -> Dict[str, str]:
        """
        Price Adjustment = Spot Core + Adjustment (TOM)
        """
        bid = Decimal(core["bid"])
        ask = Decimal(core["ask"])

        if adjustment:
            bid += Decimal(adjustment.get("bidSpread", "0"))
            ask += Decimal(adjustment.get("askSpread", "0"))

        return {
            "bid": format(bid, "f"),
            "ask": format(ask, "f")
        }

    # =========================
    # CORE (CRL)
    # =========================

    def _extract_core_rungs(self) -> List[Dict[str, Any]]:
        """
        Core price SIEMPRE viene de CRL
        """
        rungs_data = []

        crl = self.scp.get("crl")
        if not crl:
            return rungs_data

        rungs = crl.get("rungs", [])
        if not rungs:
            return rungs_data

        for rung in rungs:
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
        """
        Devuelve un dict: { amt: tom_rung }
        """
        tom = self.scp.get("tom")
        if not tom:
            return {}

        tom_rungs = tom.get("rungs", [])
        index = {}

        for rung in tom_rungs:
            try:
                index[int(rung["amt"])] = rung
            except Exception:
                continue

        return index

    def _calculate_mid_and_spread(
                self,
                price: Dict[str, str]
        ) -> Dict[str, str]:
            bid = Decimal(price["bid"])
            ask = Decimal(price["ask"])

            mid = (bid + ask) / Decimal("2")
            spread = ask - bid

            return {
                "mid": format(mid, "f"),
                "spread": format(spread, "f")
            }