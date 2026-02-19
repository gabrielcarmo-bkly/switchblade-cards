from visuals.config_window import TkController
from visuals.tray_menu import TrayApp


def main():
    tk_controller = TkController()
    app = TrayApp(tk_controller)
    app.run()


if __name__ == "__main__":
    main()
