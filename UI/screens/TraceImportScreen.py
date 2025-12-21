import os
import json
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, scrolledtext

from UI.components.StyledButton import StyledButton
from UI.styles.theme import BACKGROUND, FONT_FAMILY
from services.SCPParserService import parse_block


class TraceImportScreen(tk.Frame):
    def __init__(self, master, controller=None):
        super().__init__(master, bg=BACKGROUND)
        self.controller = controller
        self.pack(fill="both", expand=True)
        self.create_widgets()

    def create_widgets(self):

        # ===== CONTENEDOR PRINCIPAL =====
        container = tk.Frame(self, bg=BACKGROUND)
        container.pack(fill="both", expand=True, padx=50)

        # ========== HEADER ==========
        header = tk.Frame(container, bg="#F4F6F8", height=56)
        header.pack(fill="x", pady=(15, 10))

        back_btn = tk.Label(
            header,
            text="← Volver",
            font=(FONT_FAMILY, 11, "bold"),
            bg="#F4F6F8",
            fg="#0A58CA",
            cursor="hand2"
        )
        back_btn.pack(side="left")
        back_btn.bind("<Button-1>", lambda e: self.go_back())

        tk.Label(
            header,
            text="Importar Traza SCP",
            font=(FONT_FAMILY, 16, "bold"),
            bg="#F4F6F8"
        ).pack(side="left", padx=15)

        # ========== BODY ==========
        body = tk.Frame(container, bg=BACKGROUND)
        body.pack(fill="both", expand=True, pady=(10, 30))

        tk.Label(
            body,
            text=(
                "Pega aquí la traza SCP completa tal y como aparece en los logs "
                "de pricing (Spot / RFS / RFQ)."
            ),
            font=(FONT_FAMILY, 11),
            bg=BACKGROUND,
            fg="#555",
            wraplength=900,
            justify="left"
        ).pack(anchor="w", pady=(0, 15))

        # ========== CARD ==========
        card = tk.Frame(
            body,
            bg="white",
            highlightbackground="#D0D5DD",
            highlightthickness=1
        )
        card.pack(fill="both", expand=True)

        # 👉 AQUÍ VA EL SCROLLEDTEXT (editable)
        self.text_area = scrolledtext.ScrolledText(
            card,
            font=(FONT_FAMILY, 10),
            relief="flat",
            bd=0,
            wrap="none"
        )
        self.text_area.pack(fill="both", expand=True, padx=10, pady=10)

        # ========== BOTÓN GUARDAR ==========
        self.save_button = StyledButton(
            body,
            "Guardar SCP",
            command=self.save_scp,
            bg="#198754",
            width=20,
            height=2
        )
        self.save_button.pack(pady=(20, 0))

    # ---------------- NAVEGACIÓN ----------------

    def go_back(self):
        """
        Vuelve a la pantalla inicial (HomeScreen)
        """
        for widget in self.master.winfo_children():
            widget.destroy()

        from UI.screens.HomeScreen import HomeScreen
        HomeScreen(self.master, controller=self.controller)

    # -------------------- FORMATO SCP --------------------
    # (lo dejo tal cual lo tenías, no se toca)

    def format_atom(self, v):
        if v is None:
            return "null"
        if isinstance(v, bool):
            return "T" if v else "F"
        if isinstance(v, float):
            return f"{v:.4f}"
        return str(v)

    def dict_to_scp(self, obj, indent=0):
        sp = "  " * indent

        if isinstance(obj, dict):
            if "__type__" in obj:
                cls = obj["__type__"]
                body = {k: v for k, v in obj.items() if k != "__type__"}

                lines = []
                for k, v in body.items():
                    lines.append(self.dict_to_scp({k: v}, indent + 1))

                return f"{sp}{cls}[\n" + "\n".join(lines) + f"\n{sp}]"

            lines = []
            for k, v in obj.items():
                if isinstance(v, dict) and "__type__" in v:
                    lines.append(f"{sp}{k}=" + self.dict_to_scp(v, indent))
                elif isinstance(v, list):
                    inner = "\n".join(
                        self.dict_to_scp(i, indent + 2) if isinstance(i, dict)
                        else f"{sp}    {self.format_atom(i)}"
                        for i in v
                    )
                    lines.append(f"{sp}{k}=[\n{inner}\n{sp}]")
                else:
                    lines.append(f"{sp}{k}={self.format_atom(v)}")

            return "\n".join(lines)

        return f"{sp}{self.format_atom(obj)}"

    # -------------------- GUARDAR SCP --------------------

    def save_scp(self):
        content = self.text_area.get("1.0", tk.END).strip()

        if not content:
            messagebox.showwarning("Atención", "No hay traza SCP para guardar.")
            return

        try:
            # Parsear SOLO para sacar el ID
            parsed_tmp = parse_block(content)
            scp_id = parsed_tmp.get("id")

            if not scp_id:
                raise ValueError("No se pudo extraer el ID del SCP")

            base_dir = os.path.join(os.getcwd(), "resources", "scp", "history")
            raw_dir = os.path.join(base_dir, "raw")
            os.makedirs(raw_dir, exist_ok=True)

            raw_path = os.path.join(raw_dir, f"{scp_id}.txt")

            # 🔒 DEDUPLICACIÓN AQUÍ (lugar correcto)
            if os.path.exists(raw_path):
                # 👉 AUNQUE SEA DUPLICADO, MARCAMOS SCP ACTIVO
                if self.controller:
                    self.controller.last_raw_scp = content
                    self.controller.active_scp_id = scp_id

                messagebox.showinfo(
                    "Traza duplicada",
                    f"Ya existe una traza SCP con ID:\n\n{scp_id}\n\n"
                    "Se usará esta traza para el desglose."
                )
                return

            # Guardar RAW
            with open(raw_path, "w", encoding="utf-8") as f:
                f.write(content)

            # Guardar en controller (solo si es NUEVA)
            if self.controller:
                self.controller.last_raw_scp = content
                self.controller.active_scp_id = scp_id

            messagebox.showinfo(
                "Éxito",
                "Traza SCP importada correctamente.\n\n"
                f"ID: {scp_id}\n"
                f"Archivo:\n{raw_path}"
            )

            self.text_area.delete("1.0", tk.END)

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo guardar la traza SCP:\n{e}"
            )


