import os
import json
import tkinter as tk
from tkinter import messagebox
from decimal import Decimal

from UI.components.StyledButton import StyledButton
from UI.styles.theme import BACKGROUND, FONT_FAMILY
from services.SCPParserService import parse_block


class HomeScreen(tk.Frame):

    # ---------- JSON serializer ----------
    @staticmethod
    def decimal_serializer(obj):
        if isinstance(obj, Decimal):
            return format(obj, "f")
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    def __init__(self, master, controller=None):
        super().__init__(master, bg=BACKGROUND)
        self.controller = controller
        self.pack(fill="both", expand=True)
        self.create_widgets()

    def create_widgets(self):
        tk.Label(
            self,
            text="FX Price Construction",
            font=(FONT_FAMILY, 18, "bold"),
            bg=BACKGROUND
        ).pack(pady=(30, 20))

        button_frame = tk.Frame(self, bg=BACKGROUND)
        button_frame.pack()

        btn_width = 20
        btn_height = 2

        StyledButton(
            button_frame, "Buscar Traza",
            command=self.on_search,
            width=btn_width, height=btn_height
        ).grid(row=0, column=0, padx=10)

        StyledButton(
            button_frame, "Desglosar Spot",
            command=self.on_spot,
            width=btn_width, height=btn_height
        ).grid(row=0, column=1, padx=10)

        StyledButton(
            button_frame, "Importar Traza SCP",
            command=self.open_trace_import,
            width=btn_width, height=btn_height
        ).grid(row=0, column=2, padx=10)

    # ---------------- EVENTOS ----------------

    def on_search(self):
        print("Botón Buscar Traza pulsado")

    def on_spot(self):
        """
        Ejecuta el parser SCP y guarda raw + parsed
        en history/raw y history/parsed usando el mismo ID
        """
        try:
            base_dir = os.path.join(os.getcwd(), "resources", "scp", "history")
            raw_dir = os.path.join(base_dir, "raw")
            parsed_dir = os.path.join(base_dir, "parsed")

            os.makedirs(raw_dir, exist_ok=True)
            os.makedirs(parsed_dir, exist_ok=True)

            # ⚠️ La traza debe venir del Importar Traza
            # Aquí asumimos que TraceImportScreen la deja accesible
            # por ejemplo en self.controller.last_raw_scp
            raw_scp = getattr(self.controller, "last_raw_scp", None)

            if not raw_scp:
                messagebox.showwarning(
                    "Traza no encontrada",
                    "No hay ninguna traza SCP cargada.\n\n"
                    "Importa primero una traza SCP."
                )
                return

            # 🧠 Parsear
            parsed_scp = parse_block(raw_scp)

            scp_id = parsed_scp.get("id")
            if not scp_id:
                raise ValueError("No se pudo extraer el ID del SCP")

            # Guardar RAW
            raw_path = os.path.join(raw_dir, f"{scp_id}.txt")
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write(raw_scp)

            # Guardar PARSED
            parsed_path = os.path.join(parsed_dir, f"{scp_id}.json")
            with open(parsed_path, "w", encoding="utf-8") as f:
                json.dump(
                    parsed_scp,
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=HomeScreen.decimal_serializer
                )

            messagebox.showinfo(
                "Spot desglosado",
                "Traza SCP procesada correctamente.\n\n"
                f"RAW: {raw_path}\n"
                f"PARSED: {parsed_path}"
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Error al desglosar el Spot:\n{e}"
            )

    def open_trace_import(self):
        for widget in self.master.winfo_children():
            widget.destroy()
        from UI.screens.TraceImportScreen import TraceImportScreen
        TraceImportScreen(self.master, controller=self.controller)
