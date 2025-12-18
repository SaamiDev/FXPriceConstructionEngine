import tkinter as tk
from UI.styles.theme import PRIMARY, FONT_FAMILY, FONT_SIZE_NORMAL

class StyledButton(tk.Button):
    def __init__(self, master, text, command=None, bg=PRIMARY, **kwargs):
        super().__init__(
            master,
            text=text,
            command=command,
            bg=bg,
            fg="white",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL, "bold"),
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            activebackground=bg,
            activeforeground="white",
            **kwargs  # Esto permite width, height y cualquier opción de Tkinter
        )