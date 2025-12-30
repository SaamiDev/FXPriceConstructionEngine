import os


class SCPDeleteService:

    def __init__(self, base_path: str):
        self.base_path = base_path

    def delete(self, scp_id: str) -> bool:
        """
        Borra todos los artefactos asociados a un SCP.
        Devuelve True si se borra algo.
        """
        deleted = False

        paths = [
            os.path.join(
                self.base_path,
                "resources", "scp", "history", "parsed",
                f"{scp_id}.json"
            ),
            os.path.join(
                self.base_path,
                "resources", "scp", "spot_construction",
                f"{scp_id}.json"
            )
        ]

        for path in paths:
            if os.path.exists(path):
                os.remove(path)
                deleted = True

        return deleted