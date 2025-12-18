import os
import tkinter as tk
from UI.styles.theme import apply_theme

class MainWindow(tk.Tk):
    def __init__(self, controller):
        super().__init__()

        self.title("FX Price Construction Engine")
        self.geometry("1000x800")
        apply_theme(self)

        self.controller = controller

        self._set_app_icon()   # 👈 AQUÍ
        self.init_ui()

    def _set_app_icon(self):
        """
        Establece el icono de la ventana (barra superior / taskbar)
        """
        try:
            icon_path = os.path.join(
                os.getcwd(),
                "resources",
                "assets",
                "app_icon.png"
            )

            icon = tk.PhotoImage(file=icon_path)
            self.iconphoto(True, icon)

            # ⚠️ MUY IMPORTANTE: guardar referencia
            self._icon_ref = icon

        except Exception as e:
            print(f"[WARN] No se pudo cargar el icono: {e}")

    def init_ui(self):
        from UI.screens.HomeScreen import HomeScreen
        HomeScreen(self, controller=self.controller)
