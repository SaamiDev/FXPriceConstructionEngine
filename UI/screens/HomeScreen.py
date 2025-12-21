import tkinter as tk
import os
import json
from tkinter import messagebox

from UI.components.StyledButton import StyledButton
from UI.styles.theme import BACKGROUND, FONT_FAMILY
from services.SCPParserService import parse_block, decimal_serializer


class HomeScreen(tk.Frame):
    def __init__(self, master, controller=None):
        super().__init__(master, bg=BACKGROUND)
        self.controller = controller
        self.pack(fill="both", expand=True)

        self.create_background()
        self.create_widgets()

    # ---------------- BACKGROUND ----------------

    def create_background(self):
        self.canvas = tk.Canvas(
            self,
            bg=BACKGROUND,
            highlightthickness=0
        )
        self.canvas.place(relx=0, rely=0, relwidth=1, relheight=1)

        img_path = os.path.join(
            os.getcwd(),
            "resources",
            "assets",
            "logo_bg.png"
        )

        if os.path.exists(img_path):
            self.bg_image = tk.PhotoImage(file=img_path)
            self.bg_img_id = self.canvas.create_image(
                0, 0,
                image=self.bg_image,
                anchor="center"
            )
            self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        if hasattr(self, "bg_img_id"):
            self.canvas.coords(
                self.bg_img_id,
                event.width // 2,
                event.height // 2
            )

    # ---------------- UI ----------------

    def create_widgets(self):
        content = tk.Frame(self, bg=BACKGROUND)
        content.place(relx=0.5, rely=0.05, anchor="n")

        tk.Label(
            content,
            text="FX Price Construction",
            font=(FONT_FAMILY, 18, "bold"),
            bg=BACKGROUND
        ).pack(pady=(20, 20))

        button_frame = tk.Frame(content, bg=BACKGROUND)
        button_frame.pack()

        btn_width = 20
        btn_height = 2

        StyledButton(
            button_frame,
            "Buscar Traza",
            command=self.on_search,
            width=btn_width,
            height=btn_height
        ).grid(row=0, column=0, padx=10)

        StyledButton(
            button_frame,
            "Desglosar Spot",
            command=self.on_spot,
            width=btn_width,
            height=btn_height
        ).grid(row=0, column=1, padx=10)

        StyledButton(
            button_frame,
            "Importar Traza SCP",
            command=self.open_trace_import,
            width=btn_width,
            height=btn_height
        ).grid(row=0, column=2, padx=10)

        StyledButton(
            button_frame,
            "Ver CRL",
            command=self.open_crl_view,
            width=btn_width,
            height=btn_height
        ).grid(row=0, column=3, padx=10)

    # ---------------- EVENTOS ----------------

    def on_search(self):
        messagebox.showinfo(
            "Info",
            "Funcionalidad 'Buscar Traza' pendiente."
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

            # Traza cargada desde Importar SCP
            raw_scp = getattr(self.controller, "last_raw_scp", None)

            if not raw_scp:
                messagebox.showwarning(
                    "Traza no encontrada",
                    "Importa primero una traza SCP."
                )
                return

            # 🧠 Parsear SCP
            parsed_scp = parse_block(raw_scp)
            self.controller.last_parsed_scp = parsed_scp

            scp_id = parsed_scp.get("id")
            if not scp_id:
                raise ValueError("No se pudo extraer el ID del SCP")

            raw_path = os.path.join(raw_dir, f"{scp_id}.txt")
            parsed_path = os.path.join(parsed_dir, f"{scp_id}.json")

            # Guardar RAW solo si no existe
            if not os.path.exists(raw_path):
                with open(raw_path, "w", encoding="utf-8") as f:
                    f.write(raw_scp)

            # Guardar PARSED usando serializer Decimal
            with open(parsed_path, "w", encoding="utf-8") as f:
                json.dump(
                    parsed_scp,
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=decimal_serializer
                )

            messagebox.showinfo(
                "Spot desglosado",
                f"SCP procesado correctamente.\n\nID: {scp_id}"
            )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Error al desglosar Spot:\n{e}"
            )

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
