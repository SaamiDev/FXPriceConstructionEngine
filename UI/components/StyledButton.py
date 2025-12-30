import tkinter as tk
from UI.styles.theme import FONT_FAMILY


class StyledButton(tk.Frame):
    def __init__(
        self,
        parent,
        text,
        command=None,
        bg="#FF8C00",
        hover="#FFA733",
        fg="white",
        width=180,
        height=42,
        font_size=11
    ):
        super().__init__(parent, bg=bg, width=width, height=height)

        self.command = command
        self.default_bg = bg
        self.hover_bg = hover

        self.pack_propagate(False)

        self.label = tk.Label(
            self,
            text=text,
            bg=bg,
            fg=fg,
            font=(FONT_FAMILY, font_size, "bold"),
            cursor="hand2"
        )
        self.label.pack(expand=True, fill="both")

        # Events
        self.label.bind("<Enter>", self._on_enter)
        self.label.bind("<Leave>", self._on_leave)
        self.label.bind("<Button-1>", self._on_click)

    def _on_enter(self, _):
        self.config(bg=self.hover_bg)
        self.label.config(bg=self.hover_bg)

    def _on_leave(self, _):
        self.config(bg=self.default_bg)
        self.label.config(bg=self.default_bg)

    def _on_click(self, _):
        if self.command:
            self.command()