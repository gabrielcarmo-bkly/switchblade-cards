import json
import threading
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import pystray
from winotify import Notification

from functions.app_logging import open_log_file

ASSETS_DIR = Path(__file__).resolve().parent / "icons"
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


def ensure_tray_icon():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    icon_path = ASSETS_DIR / "tray.ico"
    if icon_path.exists():
        return icon_path

    lock_path = ASSETS_DIR / "icon.png"
    if lock_path.exists():
        icon = Image.open(lock_path).convert("RGBA").resize((64, 64), Image.LANCZOS)
        icon.save(icon_path, format="ICO")
        return icon_path

    size = 64
    image = Image.new("RGBA", (size, size), (30, 30, 30, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((4, 4, size - 4, size - 4), outline=(230, 230, 230, 255), width=3)

    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    text = "VC"
    if font is not None:
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        draw.text(((size - text_w) // 2, (size - text_h) // 2), text, fill=(255, 255, 255, 255), font=font)

    image.save(icon_path, format="ICO")
    return icon_path


class TrayApp:
    _required_fields = ("url", "client_id", "client_secret")

    def __init__(self, tk_controller):
        self.tk_controller = tk_controller
        self._icon = None
        self._toast_app_id = "SwitchBlade Card"
        self._icon_path = ensure_tray_icon()
        self._icon_image = Image.open(self._icon_path)
        self._icon_lock = threading.Lock()
        self.tk_controller.set_notifier(self.show_notification)

    def _create_menu(self):
        return pystray.Menu(
            pystray.MenuItem("Gerar Token PRD", lambda _icon, _item: self.tk_controller.generate_token("PRD"),
                             enabled=lambda _item: self._is_env_ready("PRD")),
            pystray.MenuItem("Gerar Token SDB", lambda _icon, _item: self.tk_controller.generate_token("SDB"),
                             enabled=lambda _item: self._is_env_ready("SDB")),
            pystray.MenuItem("Gerar Token STG", lambda _icon, _item: self.tk_controller.generate_token("STG"),
                             enabled=lambda _item: self._is_env_ready("STG")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Gerar UUID", lambda _icon, _item: self.tk_controller.generate_uuid()),
            pystray.MenuItem("Gerar CPF", lambda _icon, _item: self.tk_controller.generate_cpf()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Marcar Ponto", lambda _icon, _item: self.tk_controller.schedule_time_entry_reminder()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Configuracoes", lambda _icon, _item: self.tk_controller.show_config()),
            pystray.MenuItem("Ver Logs", lambda _icon, _item: self._open_logs()),
            pystray.MenuItem("Sair", lambda _icon, _item: self.quit()),
        )

    def _is_env_ready(self, env_name):
        data = self._load_config()
        env = data.get(env_name, {})
        for field in self._required_fields:
            value = (env.get(field) or "").strip()
            if not value:
                return False
        return True

    def _load_config(self):
        if not CONFIG_PATH.exists():
            return {}

        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _open_logs(self):
        try:
            open_log_file()
        except Exception as exc:
            self.show_notification("Logs", str(exc), level="error")

    def show_notification(self, title, message, level="info"):
        def _notify():
            try:
                toast = Notification(
                    app_id=self._toast_app_id,
                    title=title,
                    msg=message,
                    icon=str(self._icon_path),
                )
                toast.show()
            except Exception:
                pass

        threading.Thread(target=_notify, daemon=True).start()

    def quit(self):
        if self._icon is not None:
            with self._icon_lock:
                self._icon.stop()
        self.tk_controller.shutdown()

    def run(self):
        menu = self._create_menu()
        self._icon = pystray.Icon("SwitchBladeCard", self._icon_image, "SwitchBlade Card", menu)
        self._icon.run()
