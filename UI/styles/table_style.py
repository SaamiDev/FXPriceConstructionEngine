
from tkinter import ttk
from UI.styles.desk_theme import *

def apply_table_style():
    style = ttk.Style()
    style.theme_use("default")

    style.configure(
        "Treeview",
        background=BG_MAIN,
        foreground=TEXT_PRIMARY,
        fieldbackground=BG_MAIN,
        rowheight=22,
        font=FONT_MONO,
        borderwidth=0
    )

    style.configure(
        "Treeview.Heading",
        background=BG_PANEL,
        foreground=TEXT_PRIMARY,
        font=FONT_BOLD,
        borderwidth=0
    )

    style.map(
        "Treeview",
        background=[("selected", ACCENT_ACTIVE)],
        foreground=[("selected", "black")]
    )