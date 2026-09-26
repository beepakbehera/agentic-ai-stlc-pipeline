#!/usr/bin/env python3
"""Set GitHub Actions repo secrets from local .env + pipeline config (one-off setup)."""
import base64
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()
try:
    import nacl.public
    import nacl.encoding
except ImportError:
    print("PyNaCl missing - installing: pip install pynacl")
    sys.exit(1)

from config.settings import get_settings

s = get_settings()
TOKEN = s.github_token.get_secret_value()
OWNER, REPO = s.github_repo_owner, s.github_repo_name
BASE = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/secrets"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
}

# Collect secret values: from settings / .env, plus the workflow's input texts
config = json.loads(Path("pipeline_config_saucedemo.json").read_text(encoding="utf-8"))

SECRETS = {
    "NEMOTRON_API_KEY": s.nemotron_api_key.get_secret_value(),
    "NEMOTRON_MODEL": s.nemotron_model,
    "NEMOTRON_BASE_URL": s.nemotron_base_url,
    "JIRA_BASE_URL": s.jira_base_url,
    "JIRA_EMAIL": s.jira_email,
    "JIRA_API_TOKEN": s.jira_api_token.get_secret_value(),
    "JIRA_PROJECT_KEY": s.jira_project_key,
    "JIRA_ISSUE_TYPE": s.jira_issue_type,
    "GITHUB_TOKEN": TOKEN,
    "BASE_URL": s.base_url or "https://www.saucedemo.com/",
    "REQUIREMENTS": config["requirements"],
    "ACCEPTANCE_CRITERIA": config["acceptance_criteria"],
    "APPLICATION_CONTEXT": config["application_context"],
}


def encrypt(public_key: str, secret_value: str) -> str:
    pk = nacl.public.PublicKey(public_key.encode("utf-8"), encoder=nacl.encoding.Base64Encoder())
    box = nacl.public.SealedBox(pk)
    encrypted = box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")


def main():
    client = httpx.Client(headers=HEADERS, timeout=30)
    # 1. Get repo public key
    r = client.get(f"{BASE}/public-key")
    r.raise_for_status()
    data = r.json()
    key_id, public_key = data["key_id"], data["key"]
    print(f"Public key fetched (id={key_id})")

    # 2. Put each secret
    ok, fail = [], []
    for name, value in SECRETS.items():
        if not value:
            fail.append((name, "empty value"))
            continue
        payload = {
            "encrypted_value": encrypt(public_key, str(value)),
            "key_id": key_id,
        }
        pr = client.put(f"{BASE}/{name}", json=payload)
        (ok if pr.status_code in (201, 204) else fail).append(
            (name, pr.status_code) if pr.status_code in (201, 204) else (name, pr.status_code, pr.text[:100])
        )
    print(f"SET OK ({len(ok)}):", ", ".join(n for n, *_ in ok))
    if fail:
        print("FAILED:", fail)


if __name__ == "__main__":
    main()
