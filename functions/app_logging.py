import os
from datetime import datetime
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "http.log"


def _timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _write_block(lines):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    new_block = "\n".join(lines) + "\n\n"
    existing = ""
    if LOG_PATH.exists():
        existing = LOG_PATH.read_text(encoding="utf-8")
    LOG_PATH.write_text(new_block + existing, encoding="utf-8")


def log_http_failure(env_name, url, status, response_text, response_headers=None, curl_command=None):
    headers_text = ""
    if response_headers:
        headers_text = "\n".join(f"{key}: {value}" for key, value in response_headers.items())

    lines = [
        f"[{_timestamp()}] HTTP failure",
        f"Environment: {env_name}",
        f"URL: {url}",
        f"Status: {status}",
    ]
    if curl_command:
        lines.append("Request Curl:")
        lines.append(curl_command)
    if headers_text:
        lines.append("Response Headers:")
        lines.append(headers_text)
    lines.append("Response Body:")
    lines.append(response_text or "<empty>")
    lines.append("-" * 60)
    _write_block(lines)


def log_exception(env_name, url, error, curl_command=None):
    lines = [
        f"[{_timestamp()}] Request exception",
        f"Environment: {env_name}",
        f"URL: {url}",
        f"Error: {error}",
    ]
    if curl_command:
        lines.append("Request Curl:")
        lines.append(curl_command)
    lines.append("-" * 60)
    _write_block(lines)


def ensure_log_file():
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not LOG_PATH.exists():
        LOG_PATH.write_text("", encoding="utf-8")


def open_log_file():
    ensure_log_file()
    os.startfile(LOG_PATH)
