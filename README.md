# SwitchBlade Card

SwitchBlade Card is a Windows tray app for generating OAuth tokens for multiple environments. It runs in the system tray, opens a configuration window for PRD/SDB/STG settings, and can copy tokens/UUIDs to the clipboard.

## Features

- Tray menu actions for PRD, SDB, STG tokens and UUID generation
- Configuration window with environment settings
- Optional custom CA bundle path for HTTPS verification
- Tray notifications and human-readable HTTP logs

## Requirements

- Windows 10/11
- Python 3.10+ (virtualenv recommended)

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Run

```powershell
python main.py
```

## Configuration

Open the tray menu and click "Configuracoes" to set:

- URL
- Client ID
- Client Secret
- CA Bundle Path (optional)
- Start with Windows

Settings are stored in `config.json`. HTTP failures are logged in `logs/http.log` (newest entries at the top).

## Build (EXE)

```powershell
python -m pip install pyinstaller
pyinstaller --onefile --noconsole --name SwitchBladeCard main.py
```

The executable will be at `dist/SwitchBladeCard.exe`.

## Contributing

1. Fork the repo and create a feature branch.
2. Keep changes small and focused.
3. Test the tray app on Windows.
4. Open a PR with a clear description.

## Troubleshooting

- SSL errors: Provide a valid CA bundle path or install your corporate root certificate.
- Logs: Use the tray menu "Ver Logs" to open the log file.
