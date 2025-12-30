# services/SCPIndexService.py

import os
import json


class SCPIndexService:

    def __init__(self, base_path: str):
        self.base_path = base_path
        self.parsed_path = os.path.join(
            base_path,
            "resources",
            "scp",
            "history",
            "parsed"
        )

    def list_scps(self):
        if not os.path.exists(self.parsed_path):
            return []

        scps = []

        for file in os.listdir(self.parsed_path):
            if not file.endswith(".json"):
                continue

            scp_id = file.replace(".json", "")
            path = os.path.join(self.parsed_path, file)

            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                key = data.get("key", {})
                notional = key.get("notional", {})
                tom = data.get("tom", {})

                scps.append({
                    "scpId": scp_id,
                    "priceId": data.get("id", scp_id),
                    "ccyPair": key.get("ccyPair", "-"),
                    "notional": notional.get("amount", "-"),
                    "venue": key.get("venue", "-"),
                    # ✅ TIME CORRECTO (desde TOM)
                    "timestamp": tom.get("time", "-")
                })

            except Exception:
                # SCP corrupto o incompleto → se ignora
                continue

        # Orden descendente por timestamp ISO
        return sorted(
            scps,
            key=lambda x: x["timestamp"] or "",
            reverse=True
        )