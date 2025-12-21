import tkinter as tk
from UI.styles.theme import FONT_FAMILY


class Header(tk.Frame):
    def __init__(
        self,
        parent,
        title: str,
        on_back,
        bg="#F4F6F8",
        fg="#0A58CA",
        height=56
    ):
        super().__init__(parent, bg=bg, height=height)

        self.pack(fill="x", pady=(15, 10))
        self.pack_propagate(False)

        back_btn = tk.Label(
            self,
            text="← Volver",
            font=(FONT_FAMILY, 11, "bold"),
            bg=bg,
            fg=fg,
            cursor="hand2"
        )
        back_btn.pack(side="left", padx=(20, 10))
        back_btn.bind("<Button-1>", lambda e: on_back())

        title_lbl = tk.Label(
            self,
            text=title,
            font=(FONT_FAMILY, 16, "bold"),
            bg=bg
        )
        title_lbl.pack(side="left", padx=10)