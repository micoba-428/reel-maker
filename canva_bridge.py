"""
Canva Connect API bridge.
Handles design search, thumbnail fetching, export, and download.
User needs a Personal Access Token from https://www.canva.com/developers/
"""

import os
import time
import requests
from pathlib import Path
from typing import Optional, List


class CanvaBridge:
    BASE_URL = "https://api.canva.com/rest/v1"

    def __init__(self, token: str):
        self._token = token.strip()
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        })

    # ── Connectivity check ────────────────────────────────────────
    def ping(self) -> dict:
        """Verify token validity by fetching the authed user's profile."""
        resp = self._session.get(f"{self.BASE_URL}/users/me/profile")
        if resp.status_code == 401:
            raise PermissionError("トークンが無効です。Canva Developer Portalで確認してください。")
        resp.raise_for_status()
        return resp.json().get("profile", {})

    # ── Design search ─────────────────────────────────────────────
    def search_designs(self, query: str = None, limit: int = 24) -> List[dict]:
        """Return list of design dicts from the user's Canva account."""
        params = {"ownership": "owned", "sort_by": "modified_descending"}
        if query and query.strip():
            params["query"] = query.strip()
            params["sort_by"] = "relevance"

        resp = self._session.get(f"{self.BASE_URL}/designs", params=params)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return items[:limit]

    # ── Export + download ─────────────────────────────────────────
    def export_and_download(self, design_id: str, dest_dir: str,
                            pages: List[int] = None) -> List[str]:
        """
        Export a Canva design and download each page to dest_dir.
        Returns list of local file paths.

        - Video designs → exported as MP4
        - All others → exported as PNG (high quality)
        """
        os.makedirs(dest_dir, exist_ok=True)

        # Detect design type to choose export format
        design_info = self._get_design(design_id)
        design_type = design_info.get("design_type", {}).get("type", "")
        is_video = design_type in ("video", "instagram_reel", "tiktok")

        if is_video:
            fmt = {"type": "mp4", "quality": "1080p"}
        else:
            fmt = {"type": "png", "width": 1080, "lossless": False, "export_quality": "pro"}
            if pages:
                fmt["pages"] = pages

        # Create export job
        payload = {"design_id": design_id, "format": fmt}
        resp = self._session.post(f"{self.BASE_URL}/exports", json=payload)
        resp.raise_for_status()
        job = resp.json().get("job", {})
        job_id = job.get("id")
        if not job_id:
            raise RuntimeError(f"エクスポートジョブの作成に失敗: {resp.text}")

        # Poll until complete
        download_urls = self._poll_export(job_id)

        # Download each file
        ext = "mp4" if is_video else "png"
        local_paths = []
        for i, url in enumerate(download_urls, start=1):
            filename = f"canva_{design_id}_p{i}.{ext}"
            dest_path = os.path.join(dest_dir, filename)
            self._download_file(url, dest_path)
            local_paths.append(dest_path)

        return local_paths

    # ── Thumbnail helper ──────────────────────────────────────────
    def get_thumbnail_url(self, design: dict) -> Optional[str]:
        """Extract thumbnail URL from a design dict."""
        thumb = design.get("thumbnail")
        if thumb:
            return thumb.get("url")
        return None

    # ── Internal ──────────────────────────────────────────────────
    def _get_design(self, design_id: str) -> dict:
        resp = self._session.get(f"{self.BASE_URL}/designs/{design_id}")
        resp.raise_for_status()
        return resp.json().get("design", {})

    def _poll_export(self, job_id: str, timeout: int = 60) -> List[str]:
        """Poll export job until success. Returns list of download URLs."""
        for _ in range(timeout):
            time.sleep(1)
            resp = self._session.get(f"{self.BASE_URL}/exports/{job_id}")
            resp.raise_for_status()
            job = resp.json().get("job", {})
            status = job.get("status")

            if status == "success":
                urls = job.get("urls", [])
                if not urls:
                    raise RuntimeError("エクスポート完了しましたがダウンロードURLが空です")
                return urls

            if status in ("failed", "cancelled"):
                raise RuntimeError(f"エクスポート失敗: {job}")

        raise TimeoutError(f"エクスポートがタイムアウトしました (job_id={job_id})")

    def _download_file(self, url: str, dest_path: str):
        with self._session.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
