from UI.MainWindow import MainWindow

class AppController:
    """
    Controller global de la aplicación.
    Aquí se guarda el estado compartido:
    - last_raw_scp
    - futuros flags / configs
    """
    def __init__(self):
        self.last_raw_scp = None


def main():
    controller = AppController()
    app = MainWindow(controller)
    app.mainloop()

if __name__ == '__main__':
    main()
