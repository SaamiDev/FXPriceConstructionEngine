import os
import tkinter as tk
from tkinter import messagebox, scrolledtext

from UI.components.StyledButton import StyledButton
from UI.components.Header import Header

from UI.styles.desk_theme import (
    BG_MAIN,
    BG_CARD,
    BG_INPUT,
    TEXT_SECONDARY,
    TEXT_INPUT,
    TEXT_CURSOR,
    SELECTION_BG,
    BORDER,
    FONT_NORMAL,
    FONT_MONO,
    ACCENT_LINK,
)
from services.SCPParserService import parse_block


class TraceImportScreen(tk.Frame):
    def __init__(self, master, controller=None):
        super().__init__(master, bg=BG_MAIN)
        self.controller = controller
        self.pack(fill="both", expand=True)
        self.create_widgets()

    # ================= UI =================

    def create_widgets(self):
        Header(
            parent=self,
            title="Importar Traza SCP",
            on_back=self.go_back
        )

        container = tk.Frame(self, bg=BG_MAIN)
        container.pack(fill="both", expand=True, padx=40, pady=20)

        tk.Label(
            container,
            text=(
                "Pega aquí la traza SCP completa tal y como aparece en los logs "
                "de pricing (Spot / RFS / RFQ)."
            ),
            font=FONT_NORMAL,
            fg=TEXT_SECONDARY,
            bg=BG_MAIN,
            wraplength=900,
            justify="left"
        ).pack(anchor="w", pady=(0, 15))

        card = tk.Frame(
            container,
            bg=BG_CARD,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        card.pack(fill="both", expand=True)

        self.text_area = scrolledtext.ScrolledText(
            card,
            font=FONT_MONO,
            bg=BG_INPUT,
            fg=TEXT_INPUT,
            insertbackground=TEXT_CURSOR,
            selectbackground=SELECTION_BG,
            relief="flat",
            bd=0,
            wrap="none"
        )
        self.text_area.pack(fill="both", expand=True, padx=12, pady=12)

        StyledButton(
            container,
            "Guardar SCP",
            command=self.save_scp,
            bg=ACCENT_LINK
        ).pack(anchor="center", pady=20)

    # ================= NAV =================

    def go_back(self):
        for widget in self.master.winfo_children():
            widget.destroy()

        from UI.screens.HomeScreen import HomeScreen
        HomeScreen(self.master, controller=self.controller)

    # ================= LOGIC =================

    def save_scp(self):
        content = self.text_area.get("1.0", tk.END).strip()

        if not content:
            messagebox.showwarning(
                "Atención",
                "No hay traza SCP para guardar."
            )
            return

        try:
            parsed_tmp = parse_block(content)
            scp_id = parsed_tmp.get("id")

            if not scp_id:
                raise ValueError("No se pudo extraer el ID del SCP")

            base_dir = os.path.join(
                os.getcwd(),
                "resources",
                "scp",
                "history"
            )
            raw_dir = os.path.join(base_dir, "raw")
            os.makedirs(raw_dir, exist_ok=True)

            raw_path = os.path.join(raw_dir, f"{scp_id}.txt")

            # Guardar siempre en memoria
            if self.controller:
                self.controller.last_raw_scp = content
                self.controller.active_scp_id = scp_id

            # ── SCP duplicado ──
            if os.path.exists(raw_path):
                messagebox.showinfo(
                    "Traza existente",
                    f"La traza SCP con ID {scp_id} ya existe.\n\n"
                    "Se usará para el desglose."
                )
                self.go_back()
                return

            # ── SCP nuevo ──
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write(content)

            messagebox.showinfo(
                "Importación correcta",
                f"SCP importado correctamente.\n\nID: {scp_id}"
            )

            self.go_back()

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo guardar la traza SCP:\n{e}"
            )