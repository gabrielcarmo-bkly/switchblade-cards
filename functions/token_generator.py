import json
from pathlib import Path

import certifi
import requests

from functions.app_logging import log_exception, log_http_failure

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"


def _load_config():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError("Config file not found. Save settings first.")

    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Config file is invalid JSON.") from exc


def generate_token(env_name):
    config = _load_config()
    cert_path = (config.get("cert_path") or "").strip()
    env = config.get(env_name, {})
    url = (env.get("url") or "").strip()
    client_id = (env.get("client_id") or "").strip()
    client_secret = (env.get("client_secret") or "").strip()

    if not url or not client_id or not client_secret:
        raise ValueError(f"Missing settings for {env_name}.")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }

    curl_parts = [
        "curl --location",
        f"'{url}'",
        "--header 'Content-Type: application/x-www-form-urlencoded'",
        f"--data-urlencode 'client_id={client_id}'",
        f"--data-urlencode 'client_secret={client_secret}'",
        "--data-urlencode 'grant_type=client_credentials'",
    ]
    if cert_path:
        curl_parts.append(f"--cacert '{cert_path}'")
    curl_command = " ".join(curl_parts)

    try:
        verify_path = cert_path if cert_path else certifi.where()
        response = requests.post(url, headers=headers, data=data, timeout=15, verify=verify_path)
    except requests.RequestException as exc:
        log_exception(env_name, url, str(exc), curl_command=curl_command)
        raise RuntimeError(f"Request failed: {exc}") from exc

    if response.status_code >= 400:
        log_http_failure(
            env_name,
            url,
            response.status_code,
            response.text,
            response.headers,
            curl_command=curl_command,
        )
        raise RuntimeError(f"HTTP {response.status_code}: {response.text}")

    try:
        payload = response.json()
    except ValueError as exc:
        log_exception(env_name, url, f"Invalid JSON response: {exc}", curl_command=curl_command)
        raise RuntimeError("Invalid JSON response.") from exc
    token = payload.get("access_token")
    if not token:
        log_exception(env_name, url, "No access_token in response.", curl_command=curl_command)
        raise RuntimeError("No access_token in response.")

    return token
