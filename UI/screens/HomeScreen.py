import tkinter as tk
import os
import json
from tkinter import messagebox

from UI.components.StyledButton import StyledButton
from UI.components.Header import Header
from UI.styles.desk_theme import (
    BG_MAIN,
    BG_PANEL,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    FONT_BOLD
)
from services.SCPParserService import parse_block, decimal_serializer


class HomeScreen(tk.Frame):
    def __init__(self, master, controller=None):
        super().__init__(master, bg=BG_MAIN)
        self.controller = controller
        self.pack(fill="both", expand=True)

        self.create_widgets()

    # ================= UI =================

    def create_widgets(self):
        # ── Header superior ──
        Header(
            parent=self,
            title="FX Price Construction",
            on_back=None
        )

        # ── Contenedor principal (arriba, NO centrado) ──
        content = tk.Frame(self, bg=BG_MAIN)
        content.pack(anchor="center", pady=(20, 0), fill="x")

        tk.Label(
            content,
            text="Pricing & Analysis",
            font=FONT_BOLD,
            fg=TEXT_SECONDARY,
            bg=BG_MAIN
        ).pack(anchor="center", padx=30, pady=(0, 20))



        # 👉 AQUÍ estaba el error: faltaba este frame
        button_frame = tk.Frame(content, bg=BG_MAIN)
        button_frame.pack(anchor="center", pady=(0, 20))

        # ── Botones (custom, no tk.Button) ──
        StyledButton(
            button_frame,
            "Buscar Traza",
            command=self.on_search
        ).grid(row=0, column=0, padx=8)

        StyledButton(
            button_frame,
            "Desglosar Spot",
            command=self.on_spot
        ).grid(row=0, column=1, padx=8)

        StyledButton(
            button_frame,
            "Importar Traza SCP",
            command=self.open_trace_import
        ).grid(row=0, column=2, padx=8)

        StyledButton(
            button_frame,
            "Ver CRL",
            command=self.open_crl_view
        ).grid(row=0, column=3, padx=8)

    # ================= EVENTOS =================

    def on_search(self):
        messagebox.showinfo(
            "Información",
            "Funcionalidad de búsqueda pendiente de implementar."
        )

    def on_spot(self):
        """
        Ejecuta el parser SCP usando la traza cargada
        en el controller y guarda raw + parsed
        """
        try:
            base_dir = os.path.join(os.getcwd(), "resources", "scp", "history")
            raw_dir = os.path.join(base_dir, "raw")
            parsed_dir = os.path.join(base_dir, "parsed")

            os.makedirs(raw_dir, exist_ok=True)
            os.makedirs(parsed_dir, exist_ok=True)

            raw_scp = getattr(self.controller, "last_raw_scp", None)

            if not raw_scp:
                messagebox.showwarning(
                    "Traza no encontrada",
                    "Importa primero una traza SCP."
                )
                return

            parsed_scp = parse_block(raw_scp)
            self.controller.last_parsed_scp = parsed_scp

            scp_id = parsed_scp.get("id")
            if not scp_id:
                raise ValueError("No se pudo extraer el ID del SCP")

            raw_path = os.path.join(raw_dir, f"{scp_id}.txt")
            parsed_path = os.path.join(parsed_dir, f"{scp_id}.json")

            if not os.path.exists(raw_path):
                with open(raw_path, "w", encoding="utf-8") as f:
                    f.write(raw_scp)

            with open(parsed_path, "w", encoding="utf-8") as f:
                json.dump(
                    parsed_scp,
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=decimal_serializer
                )

            messagebox.showinfo(
                "Proceso completado",
                f"SCP procesado correctamente.\n\nID: {scp_id}"
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Error al desglosar Spot:\n{e}"
            )

    # ================= NAV =================

    def open_trace_import(self):
        for widget in self.master.winfo_children():
            widget.destroy()

        from UI.screens.TraceImportScreen import TraceImportScreen
        TraceImportScreen(self.master, controller=self.controller)

    def open_crl_view(self):
        for widget in self.master.winfo_children():
            widget.destroy()

        from UI.screens.CRLScreen import CRLScreen
        CRLScreen(self.master, controller=self.controller)