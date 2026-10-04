"""Calls the Anthropic Messages API directly over HTTPS (no SDK needed)."""
import os
import requests

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-5-5"


class LLMError(Exception):
    pass


def write_summary(system_prompt: str, user_msg: str) -> dict:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise LLMError("ANTHROPIC_API_KEY is not set.")
    model = os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)
    body = {
        "model": model,
        "max_tokens": int(os.getenv("MAX_OUTPUT_TOKENS", "8000")),
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_msg}],
    }
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    try:
        r = requests.post(os.getenv("ANTHROPIC_API_URL", API_URL), json=body, headers=headers, timeout=300)
    except requests.RequestException as e:
        raise LLMError(f"Could not reach the Anthropic API: {e}")
    if r.status_code != 200:
        try:
            msg = r.json().get("error", {}).get("message", r.text)
        except ValueError:
            msg = r.text
        raise LLMError(f"Anthropic API error (HTTP {r.status_code}): {msg}")
    data = r.json()
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    return {
        "markdown": text,
        "model": data.get("model", model),
        "usage": data.get("usage", {}),
        "truncated": data.get("stop_reason") == "max_tokens",
    }
