import os
import json
from decimal import Decimal
from typing import Dict, Any, List


class SPOTConstructionService:

    def __init__(self, parsed_scp: Dict[str, Any], base_path: str):
        if not parsed_scp or parsed_scp.get("__type__") != "SCP":
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
            "rungs": self._extract_rungs_core_prices()
        }

    def save(self) -> str:
        """
        Construye y guarda el JSON del Spot Construction.
        Devuelve la ruta del fichero generado.
        """
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

        data = self.build()

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                indent=2,
                ensure_ascii=False
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
        notional = self.key.get("notional") or {}

        return {
            "amount": str(notional.get("amount")) if notional.get("amount") is not None else None,
            "side": notional.get("side"),
        }

    def _extract_rungs_core_prices(self) -> List[Dict[str, Any]]:
        rungs_data: List[Dict[str, Any]] = []

        # 1️⃣ Intentar CRL único
        crl = self.scp.get("crl")
        if crl and crl.get("rungs"):
            rungs = crl["rungs"]

        # 2️⃣ Intentar lista de CRLs (coger el final)
        elif self.scp.get("crls"):
            crls = self.scp["crls"]
            rungs = crls[-1].get("rungs", [])

        # 3️⃣ Fallback: clientPrc (casos legacy)
        else:
            client_prc = self.scp.get("clientPrc", [])
            rungs = client_prc[0].get("rungs", []) if client_prc else []

        for rung in rungs:
            rungs_data.append({
                "amt": int(rung.get("amt")),
                "core": {
                    "bid": str(Decimal(rung.get("bidPrice"))),
                    "ask": str(Decimal(rung.get("askPrice")))
                }
            })

        return rungs_data