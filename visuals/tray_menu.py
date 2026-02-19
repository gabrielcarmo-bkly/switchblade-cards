import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import win32api
import win32con
import win32gui

from functions.app_logging import open_log_file

ASSETS_DIR = Path(__file__).resolve().parent / "icons"
CACHE_DIR = ASSETS_DIR / "_cache"
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


def load_menu_bitmap(file_name, size=16):
    src_path = ASSETS_DIR / file_name
    if not src_path.exists():
        return None

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{src_path.stem}_{size}.bmp"
    if not cache_path.exists():
        icon = Image.open(src_path).convert("RGBA").resize((size, size), Image.LANCZOS)
        background = Image.new("RGB", (size, size), (255, 255, 255))
        background.paste(icon, mask=icon.split()[3])
        background.save(cache_path, format="BMP")

    hbm = win32gui.LoadImage(
        0,
        str(cache_path),
        win32con.IMAGE_BITMAP,
        size,
        size,
        win32con.LR_LOADFROMFILE,
    )
    return hbm


class TrayApp:
    WM_TRAYICON = win32con.WM_USER + 20
    ID_TOKEN_PRD = 1001
    ID_TOKEN_SDB = 1002
    ID_TOKEN_STG = 1003
    ID_UUID = 1004
    ID_CONFIG = 1005
    ID_LOGS = 1006
    ID_EXIT = 1007

    _required_fields = ("url", "client_id", "client_secret")

    def __init__(self, tk_controller):
        self.tk_controller = tk_controller
        self.hwnd = None
        self._hicon = None
        self._bitmaps = []
        self._actions = {}
        self._register_window()
        self._create_tray_icon()
        self.tk_controller.set_notifier(self.show_notification)

    def _register_window(self):
        wc = win32gui.WNDCLASS()
        wc.lpszClassName = "SwitchBladeCardTrayWindow"
        wc.lpfnWndProc = self._wnd_proc
        win32gui.RegisterClass(wc)
        self.hwnd = win32gui.CreateWindow(
            wc.lpszClassName,
            "SwitchBladeCardTray",
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            win32gui.GetModuleHandle(None),
            None,
        )

    def _create_tray_icon(self):
        icon_path = ensure_tray_icon()
        self._hicon = win32gui.LoadImage(
            0,
            str(icon_path),
            win32con.IMAGE_ICON,
            0,
            0,
            win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE,
        )

        flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
        nid = (self.hwnd, 0, flags, self.WM_TRAYICON, self._hicon, "SwitchBlade Card")
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, nid)

    def _create_menu(self):
        self._actions = {
            self.ID_TOKEN_PRD: lambda: self.tk_controller.generate_token("PRD"),
            self.ID_TOKEN_SDB: lambda: self.tk_controller.generate_token("SDB"),
            self.ID_TOKEN_STG: lambda: self.tk_controller.generate_token("STG"),
            self.ID_UUID: self.tk_controller.generate_uuid,
            self.ID_CONFIG: self.tk_controller.show_config,
            self.ID_LOGS: self._open_logs,
            self.ID_EXIT: self.quit,
        }

        menu = win32gui.CreatePopupMenu()

        win32gui.AppendMenu(menu, win32con.MF_STRING, self.ID_TOKEN_PRD, "Gerar Token PRD")
        win32gui.AppendMenu(menu, win32con.MF_STRING, self.ID_TOKEN_SDB, "Gerar Token SDB")
        win32gui.AppendMenu(menu, win32con.MF_STRING, self.ID_TOKEN_STG, "Gerar Token STG")
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, self.ID_UUID, "Gerar UUID")
        win32gui.AppendMenu(menu, win32con.MF_SEPARATOR, 0, "")
        win32gui.AppendMenu(menu, win32con.MF_STRING, self.ID_CONFIG, "Configuracoes")
        win32gui.AppendMenu(menu, win32con.MF_STRING, self.ID_LOGS, "Ver Logs")
        win32gui.AppendMenu(menu, win32con.MF_STRING, self.ID_EXIT, "Sair")

        self._apply_env_enabled(menu, self.ID_TOKEN_PRD, "PRD")
        self._apply_env_enabled(menu, self.ID_TOKEN_SDB, "SDB")
        self._apply_env_enabled(menu, self.ID_TOKEN_STG, "STG")

        self._set_menu_icon(menu, self.ID_TOKEN_PRD, "circle_green.png")
        self._set_menu_icon(menu, self.ID_TOKEN_SDB, "circle_yellow.png")
        self._set_menu_icon(menu, self.ID_TOKEN_STG, "circle_red.png")
        self._set_menu_icon(menu, self.ID_UUID, "numbers_1234.png")
        self._set_menu_icon(menu, self.ID_CONFIG, "wrench.png")
        self._set_menu_icon(menu, self.ID_LOGS, "documents.png")
        self._set_menu_icon(menu, self.ID_EXIT, "close.png")

        return menu

    def _apply_env_enabled(self, menu, item_id, env_name):
        if self._is_env_ready(env_name):
            win32gui.EnableMenuItem(menu, item_id, win32con.MF_BYCOMMAND | win32con.MF_ENABLED)
        else:
            win32gui.EnableMenuItem(menu, item_id, win32con.MF_BYCOMMAND | win32con.MF_GRAYED)

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

    def _set_menu_icon(self, menu, item_id, file_name):
        hbm = load_menu_bitmap(file_name)
        if hbm is not None:
            win32gui.SetMenuItemBitmaps(menu, item_id, win32con.MF_BYCOMMAND, hbm, hbm)
            self._bitmaps.append(hbm)

    def _open_logs(self):
        try:
            open_log_file()
        except Exception as exc:
            self.show_notification("Logs", str(exc), level="error")

    def _show_menu(self):
        menu = self._create_menu()
        pos = win32gui.GetCursorPos()
        win32gui.SetForegroundWindow(self.hwnd)
        win32gui.TrackPopupMenu(
            menu,
            win32con.TPM_LEFTALIGN | win32con.TPM_RIGHTBUTTON,
            pos[0],
            pos[1],
            0,
            self.hwnd,
            None,
        )
        win32gui.PostMessage(self.hwnd, win32con.WM_NULL, 0, 0)

    def _on_command(self, wparam):
        cmd_id = win32api.LOWORD(wparam)
        action = self._actions.get(cmd_id)
        if action:
            action()
        return 0

    def _on_tray_notify(self, lparam):
        if lparam == win32con.WM_RBUTTONUP:
            self._show_menu()
            return 0
        if lparam == win32con.WM_LBUTTONDBLCLK:
            self.tk_controller.show_config()
            return 0
        return 0

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == self.WM_TRAYICON:
            return self._on_tray_notify(lparam)
        if msg == win32con.WM_COMMAND:
            return self._on_command(wparam)
        if msg == win32con.WM_DESTROY:
            win32gui.PostQuitMessage(0)
            return 0
        return win32gui.DefWindowProc(hwnd, msg, wparam, lparam)

    def show_notification(self, title, message, level="info"):
        if not self.hwnd:
            return

        info_flag = getattr(win32con, "NIIF_INFO", 0x1)
        if level == "error":
            info_flag = getattr(win32con, "NIIF_ERROR", 0x3)

        flags = win32gui.NIF_INFO
        nid = (
            self.hwnd,
            0,
            flags,
            0,
            0,
            "",
            message,
            5000,
            title,
            info_flag,
        )
        win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY, nid)

    def quit(self):
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (self.hwnd, 0))
        if self._hicon:
            win32gui.DestroyIcon(self._hicon)
        for hbm in self._bitmaps:
            win32gui.DeleteObject(hbm)
        self.tk_controller.shutdown()
        win32gui.PostQuitMessage(0)

    def run(self):
        win32gui.PumpMessages()
