
import tkinter as tk
from UI.styles.desk_theme import *

class Header(tk.Frame):
    def __init__(self, parent, title, on_back=None):
        super().__init__(
            parent,
            bg=BG_PANEL,
            height=48,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        self.pack(fill="x")

        if on_back:
            back = tk.Label(
                self,
                text="← Back",
                fg=ACCENT_LINK,
                bg=BG_PANEL,
                font=FONT_BOLD,
                cursor="hand2"
            )
            back.pack(side="left", padx=14)
            back.bind("<Button-1>", lambda e: on_back())

        tk.Label(
            self,
            text=title.upper(),
            fg=TEXT_PRIMARY,
            bg=BG_PANEL,
            font=FONT_BOLD
        ).pack(side="left", padx=12)