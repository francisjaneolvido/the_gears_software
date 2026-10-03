"""
services/api_client.py
──────────────────────
HTTP client for the Tkinter app.
Replaces direct DB calls in admin_db_service.py.
"""

import requests
import json
import os


class APIClient:
    def __init__(self, base_url: str = None, token: str = None):
        self.base  = (base_url or os.getenv("FLASK_API_URL", "http://127.0.0.1:5000")).rstrip("/")
        self.token = token or os.getenv("TKINTER_API_TOKEN", "change-me-in-env")
        self.session = requests.Session()
        self.session.headers.update({"X-API-Token": self.token})

    def _get(self, path, params=None):
        resp = self.session.get(f"{self.base}{path}", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path, data):
        resp = self.session.post(f"{self.base}{path}", json=data, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _delete(self, path):
        resp = self.session.delete(f"{self.base}{path}", timeout=10)
        resp.raise_for_status()
        return resp.json()

    # ── Drafts ────────────────────────────────────────────────────────────

    def fetch_drafts(self, author_id: int = None) -> list:
        params = {"author_id": author_id} if author_id else {}
        rows   = self._get("/api/v1/drafts", params=params)

        result = []
        for d in rows:
            media_json = d.get("media_json", "")
            if not media_json and d.get("web_paths"):
                media_json = json.dumps({
                    "author":       d.get("author_name", ""),
                    "photographer": d.get("photographer", ""),
                    "file_paths":   d.get("web_paths", []),
                })

            result.append((
                d["id"],
                d["author_name"],
                d["category"],
                d["last_updated"],
                d["admin_email"],
                None,
                d["autosaved"],
                d["photographer"],
                d["headline"],
                d["content"],
                media_json,
            ))
        return result

    def save_draft(self, data: dict) -> dict:
        return self._post("/api/v1/drafts", data)

    def delete_draft(self, article_id: int) -> bool:
        result = self._delete(f"/api/v1/drafts/{article_id}")
        return result.get("deleted", False)

    def submit_for_review(self, data: dict) -> bool:
        result = self._post("/api/v1/drafts/submit", data)
        return result.get("submitted", False)

    # ── Categories ────────────────────────────────────────────────────────

    def fetch_categories(self) -> list:
        return self._get("/api/v1/categories")

    # ── Auth ──────────────────────────────────────────────────────────────

    def login(self, email: str, password: str) -> dict | None:
        try:
            return self._post("/api/v1/auth/login", {"email": email, "password": password})
        except requests.HTTPError as e:
            if e.response.status_code in (401, 404):
                return None
            raise

    # ── Avatar upload ─────────────────────────────────────────────────────

    def upload_avatar(self, file_path: str) -> str | None:
        """
        Upload a local image file to Flask /api/v1/upload.

        Returns the filename assigned by Flask (e.g. 'abc123_user_1.jpg')
        so the caller can store it as 'avatars/<filename>' in the DB.
        Returns None on any error.
        """
        if not os.path.exists(file_path):
            print(f"[upload_avatar] File not found: {file_path}")
            return None

        try:
            with open(file_path, "rb") as f:
                resp = self.session.post(
                    f"{self.base}/api/v1/upload",
                    files={"file": (os.path.basename(file_path), f)},
                    timeout=20,
                )
            resp.raise_for_status()
            filename = resp.json().get("filename")
            if filename:
                print(f"[upload_avatar] ✅ Uploaded: {filename}")
            return filename
        except Exception as e:
            print(f"[upload_avatar] ❌ Failed: {e}")
            return None