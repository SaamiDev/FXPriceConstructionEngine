import tkinter as tk
from UI.styles.theme import apply_theme
from UI.screens.HomeScreen import HomeScreen

class MainWindow(tk.Tk):
    def __init__(self, controller):
        super().__init__()
        self.title("FX Price Construction Engine")
        self.geometry("1000x800")
        apply_theme(self)
        self.controller = controller
        self.init_ui()



    def init_ui(self):
        self.home_screen = HomeScreen(self, controller=self.controller)
