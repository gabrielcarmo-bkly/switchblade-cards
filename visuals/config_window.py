import json
import sys
import threading
import tkinter as tk
import winreg
from pathlib import Path
from tkinter import filedialog, ttk

from PIL import Image, ImageTk

from functions.generate_uuid import generate_uuid_to_clipboard
from functions.token_generator import generate_token

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"
ASSETS_DIR = Path(__file__).resolve().parent / "icons"
APP_NAME = "SwitchBlade Card"
STARTUP_VALUE_NAME = "SwitchBladeCard"
ENVIRONMENTS = ("PRD", "SDB", "STG")
FIELDS = (
    ("url", "URL"),
    ("client_id", "Client ID"),
    ("client_secret", "Client Secret"),
)


class TkController:
    def __init__(self):
        self.root = None
        self.config_window = None
        self.entries = {}
        self.cert_path_entry = None
        self.startup_var = None
        self._notifier = None
        self._header_icon = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait()

    def _run(self):
        self.root = tk.Tk()
        self.root.title("SwitchBlade Card")
        self.root.geometry("520x720")
        self.root.withdraw()
        self._ready.set()
        self.root.mainloop()

    def _call(self, func):
        if self.root is not None:
            self.root.after(0, func)

    def show_config(self):
        def _show():
            if self.config_window is None or not self.config_window.winfo_exists():
                win = tk.Toplevel(self.root)
                win.title("SwitchBlade Card")
                win.geometry("520x620")
                win.protocol("WM_DELETE_WINDOW", win.withdraw)

                container = ttk.Frame(win, padding=8)
                container.pack(fill=tk.BOTH, expand=True)

                content_wrapper = ttk.Frame(container)
                content_wrapper.pack(fill=tk.BOTH, expand=True)

                canvas = tk.Canvas(content_wrapper, highlightthickness=0)
                scrollbar = ttk.Scrollbar(content_wrapper, orient=tk.VERTICAL, command=canvas.yview)
                scrollable = ttk.Frame(canvas)

                scroll_window = canvas.create_window((0, 0), window=scrollable, anchor="nw")
                canvas.configure(yscrollcommand=scrollbar.set)

                def _sync_scroll_region(_event):
                    canvas.configure(scrollregion=canvas.bbox("all"))

                def _sync_width(event):
                    canvas.itemconfigure(scroll_window, width=event.width)

                def _on_mousewheel(event):
                    if event.delta == 0:
                        return
                    steps = int(-1 * (event.delta / 60))
                    if steps == 0:
                        steps = -1 if event.delta > 0 else 1
                    canvas.yview_scroll(steps, "units")

                def _bind_mousewheel(_event):
                    canvas.bind_all("<MouseWheel>", _on_mousewheel)

                def _unbind_mousewheel(_event):
                    canvas.unbind_all("<MouseWheel>")

                scrollable.bind("<Configure>", _sync_scroll_region)
                canvas.bind("<Configure>", _sync_width)
                canvas.bind("<Enter>", _bind_mousewheel)
                canvas.bind("<Leave>", _unbind_mousewheel)

                canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

                header_icon = self._load_header_icon()
                if header_icon is not None:
                    win.iconphoto(True, header_icon)
                header = ttk.Label(
                    scrollable,
                    text="Configuration",
                    image=header_icon,
                    compound="left",
                    font=("Segoe UI", 12, "bold"),
                )
                header.pack(anchor=tk.W)
                ttk.Label(scrollable, text="Configure PRD, SDB, and STG environments.").pack(anchor=tk.W, pady=(4, 12))

                cert_frame = ttk.LabelFrame(scrollable, text="Certificate", padding=10)
                cert_frame.pack(fill=tk.X, expand=False, pady=(0, 10))
                ttk.Label(cert_frame, text="CA Bundle Path").grid(row=0, column=0, sticky=tk.W, padx=(0, 8), pady=4)
                cert_entry = ttk.Entry(cert_frame)
                cert_entry.grid(row=0, column=1, sticky=tk.EW, pady=4)
                ttk.Button(cert_frame, text="Browse", command=self._browse_cert).grid(
                    row=0, column=2, padx=(8, 0), pady=4
                )
                cert_frame.grid_columnconfigure(1, weight=1)
                self.cert_path_entry = cert_entry

                startup_frame = ttk.LabelFrame(scrollable, text="Startup", padding=10)
                startup_frame.pack(fill=tk.X, expand=False, pady=(0, 10))
                self.startup_var = tk.BooleanVar(value=False)
                ttk.Checkbutton(
                    startup_frame,
                    text="Start with Windows",
                    variable=self.startup_var,
                ).pack(anchor=tk.W)

                form_container = ttk.Frame(scrollable)
                form_container.pack(fill=tk.BOTH, expand=True)

                self.entries = {}
                for env in ENVIRONMENTS:
                    frame = ttk.LabelFrame(form_container, text=f"{env} Settings", padding=10)
                    frame.pack(fill=tk.X, expand=False, pady=(0, 10))

                    row = 0
                    self.entries[env] = {}
                    for field_key, label in FIELDS:
                        ttk.Label(frame, text=label).grid(row=row, column=0, sticky=tk.W, padx=(0, 8), pady=4)
                        entry = ttk.Entry(frame)
                        entry.grid(row=row, column=1, sticky=tk.EW, pady=4)
                        frame.grid_columnconfigure(1, weight=1)
                        self.entries[env][field_key] = entry
                        row += 1

                button_row = ttk.Frame(container)
                button_row.pack(fill=tk.X, pady=(8, 2))
                ttk.Button(button_row, text="Salvar", command=self._save_and_close).pack(side=tk.RIGHT, padx=(0, 8))

                self._load_config()

                self.config_window = win
            else:
                self.config_window.deiconify()

            self.config_window.lift()
            self.config_window.focus_force()

        self._call(_show)

    def _browse_cert(self):
        if self.root is None:
            return

        path = filedialog.askopenfilename(
            title="Select CA Bundle",
            filetypes=(
                ("Certificate files", "*.pem *.crt *.cer"),
                ("All files", "*.*"),
            ),
        )
        if path and self.cert_path_entry is not None:
            self.cert_path_entry.delete(0, tk.END)
            self.cert_path_entry.insert(0, path)

    def _load_header_icon(self):
        if self._header_icon is not None:
            return self._header_icon

        icon_path = ASSETS_DIR / "icon.png"
        if not icon_path.exists():
            return None

        icon = Image.open(icon_path).convert("RGBA").resize((20, 20), Image.LANCZOS)
        self._header_icon = ImageTk.PhotoImage(icon)
        return self._header_icon

    def set_notifier(self, notifier):
        self._notifier = notifier

    def _notify(self, title, message, level="info"):
        if self._notifier is not None:
            self._notifier(title, message, level)

    def generate_uuid(self):
        def _generate():
            generate_uuid_to_clipboard(self.root)
            self._notify("UUID", "UUID copied to clipboard.")

        self._call(_generate)

    def generate_token(self, env_name):
        def _generate():
            try:
                token = generate_token(env_name)
            except Exception as exc:
                self._notify("Token Error", str(exc), level="error")
                return

            self.root.clipboard_clear()
            self.root.clipboard_append(token)
            self.root.update_idletasks()
            self._notify("Token Copied", f"Token for {env_name} copied to clipboard.")

        self._call(_generate)

    def _load_config(self):
        if not CONFIG_PATH.exists():
            return

        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return

        if self.cert_path_entry is not None:
            cert_path = data.get("cert_path", "")
            self.cert_path_entry.delete(0, tk.END)
            self.cert_path_entry.insert(0, cert_path)
        if self.startup_var is not None:
            self.startup_var.set(bool(data.get("auto_start", False)))

        for env in ENVIRONMENTS:
            env_data = data.get(env, {})
            for field_key, _label in FIELDS:
                value = env_data.get(field_key, "")
                entry = self.entries.get(env, {}).get(field_key)
                if entry is not None:
                    entry.delete(0, tk.END)
                    entry.insert(0, value)

    def _save_config(self):
        data = {}
        if self.cert_path_entry is not None:
            data["cert_path"] = self.cert_path_entry.get().strip()
        if self.startup_var is not None:
            data["auto_start"] = bool(self.startup_var.get())
        for env in ENVIRONMENTS:
            data[env] = {}
            for field_key, _label in FIELDS:
                entry = self.entries.get(env, {}).get(field_key)
                data[env][field_key] = entry.get().strip() if entry is not None else ""

        CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._apply_startup_setting(bool(data.get("auto_start", False)))

    def _save_and_close(self):
        self._save_config()
        if self.config_window is not None and self.config_window.winfo_exists():
            self.config_window.withdraw()

    def _apply_startup_setting(self, enabled):
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,
            )
        except OSError:
            return

        if enabled:
            command = self._startup_command()
            if command:
                winreg.SetValueEx(key, STARTUP_VALUE_NAME, 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, STARTUP_VALUE_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)

    def _startup_command(self):
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}"'

        main_path = Path(__file__).resolve().parent.parent / "main.py"
        return f'"{sys.executable}" "{main_path}"'

    def shutdown(self):
        def _shutdown():
            if self.config_window is not None and self.config_window.winfo_exists():
                self.config_window.destroy()
            if self.root is not None:
                self.root.quit()

        self._call(_shutdown)
