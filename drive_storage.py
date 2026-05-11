"""
Google Drive API ストレージレイヤー
ローカルファイルシステムと同じインタフェースで Drive にアクセス
"""

import io
import json
import mimetypes
import os
import shutil
import ssl
import tempfile
import time
from datetime import datetime, timezone
from typing import List, Optional, Dict
from urllib.error import URLError

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload, MediaIoBaseUpload


SCOPES = ["https://www.googleapis.com/auth/drive"]


class DriveStorage:
    """Google Drive をローカルFSのように使うラッパー."""

    def __init__(self, credentials_info: Optional[dict] = None,
                 credentials_path: Optional[str] = None,
                 root_folder_name: str = "reel_maker"):
        if credentials_info is None and credentials_path:
            with open(credentials_path) as f:
                credentials_info = json.load(f)
        self._folder_cache: Dict[str, str] = {}  # path -> folder_id
        self._root_name = root_folder_name
        self._local_root = self._detect_local_root()
        self._service = None
        use_drive_api = credentials_info and self._local_root and "CloudStorage" in self._local_root
        if use_drive_api:
            creds = service_account.Credentials.from_service_account_info(
                credentials_info, scopes=SCOPES,
            )
            self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
        self._root_id = self._find_root_folder() if self._service else None

    # ── 内部 ──────────────────────────────────────────────────────────────
    def _detect_local_root(self) -> Optional[str]:
        """ローカル/クラウド環境ごとの保存先."""
        configured = os.environ.get("REEL_MAKER_DATA_ROOT")
        if configured:
            os.makedirs(configured, exist_ok=True)
            return configured

        app_dir = os.path.dirname(os.path.abspath(__file__))
        parent = os.path.dirname(app_dir)
        if os.path.basename(app_dir) == "app" and os.path.basename(parent) == self._root_name:
            if "CloudStorage" in parent and os.path.isdir(parent):
                return parent

        fallback = os.path.join(tempfile.gettempdir(), self._root_name)
        os.makedirs(fallback, exist_ok=True)
        return fallback

    def _local_folder(self, folder_name: str) -> Optional[str]:
        if not self._local_root:
            return None
        folder = os.path.join(self._local_root, folder_name)
        os.makedirs(folder, exist_ok=True)
        return folder

    def _local_file_info(self, path: str) -> dict:
        stat = os.stat(path)
        mime_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
        modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        return {
            "id": path,
            "name": os.path.basename(path),
            "mimeType": mime_type,
            "modifiedTime": modified,
            "size": str(stat.st_size),
            "localPath": path,
        }

    def _execute(self, request, attempts: int = 4):
        """Drive APIリクエストを実行。SSL瞬断だけ短く再試行する."""
        last_error = None
        for i in range(attempts):
            try:
                return request.execute()
            except (ssl.SSLError, URLError, OSError) as e:
                last_error = e
                message = str(e).lower()
                retryable = (
                    "ssl" in message
                    or "decryption_failed" in message
                    or "bad record mac" in message
                    or "connection reset" in message
                    or "timed out" in message
                    or "temporarily unavailable" in message
                )
                if not retryable or i == attempts - 1:
                    raise
                time.sleep(0.6 * (i + 1))
        raise last_error

    def _find_root_folder(self) -> str:
        """共有された reel_maker フォルダIDを取得."""
        q = (f"name = '{self._root_name}' and "
             f"mimeType = 'application/vnd.google-apps.folder' and "
             f"trashed = false")
        resp = self._execute(self._service.files().list(
            q=q,
            fields="files(id, name, owners)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ))
        files = resp.get("files", [])
        if not files:
            raise RuntimeError(
                f"'{self._root_name}' フォルダが見つかりません。"
                "Drive で共有設定を確認してください"
            )
        return files[0]["id"]

    def _get_or_create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        parent = parent_id or self._root_id
        cache_key = f"{parent}/{name}"
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]

        q = (f"name = '{name}' and '{parent}' in parents and "
             f"mimeType = 'application/vnd.google-apps.folder' and trashed = false")
        resp = self._execute(self._service.files().list(
            q=q, fields="files(id)",
            supportsAllDrives=True, includeItemsFromAllDrives=True,
        ))
        files = resp.get("files", [])
        if files:
            fid = files[0]["id"]
        else:
            meta = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent],
            }
            fid = self._execute(self._service.files().create(
                body=meta, fields="id", supportsAllDrives=True,
            ))["id"]
        self._folder_cache[cache_key] = fid
        return fid

    # ── 公開API ───────────────────────────────────────────────────────────
    def root_id(self) -> str:
        return self._root_id or self._local_root or ""

    def folder_id(self, name: str) -> str:
        """root配下の名前付きフォルダIDを取得（無ければ作成）"""
        local_folder = self._local_folder(name)
        if local_folder:
            return local_folder
        return self._get_or_create_folder(name)

    def list_files(self, folder_name: str) -> List[dict]:
        """指定フォルダのファイル一覧（id, name, mimeType, modifiedTime）"""
        local_folder = self._local_folder(folder_name)
        if local_folder:
            files = []
            for name in os.listdir(local_folder):
                path = os.path.join(local_folder, name)
                if os.path.isfile(path):
                    files.append(self._local_file_info(path))
            return sorted(files, key=lambda f: f["modifiedTime"])

        folder_id = self._get_or_create_folder(folder_name)
        q = f"'{folder_id}' in parents and trashed = false"
        all_files = []
        page_token = None
        while True:
            resp = self._execute(self._service.files().list(
                q=q,
                fields="nextPageToken, files(id, name, mimeType, modifiedTime, size)",
                pageToken=page_token,
                supportsAllDrives=True, includeItemsFromAllDrives=True,
                orderBy="modifiedTime",
            ))
            all_files.extend(resp.get("files", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        # ディレクトリは除外
        return [f for f in all_files
                if f.get("mimeType") != "application/vnd.google-apps.folder"]

    def download_to_temp(self, file_id: str, suffix: str = "") -> str:
        """ファイルを /tmp に DL してパスを返す."""
        local_id = file_id.removeprefix("local:")
        if os.path.isfile(local_id):
            ext = suffix or os.path.splitext(local_id)[1]
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            tmp.close()
            shutil.copy2(local_id, tmp.name)
            return tmp.name

        req = self._service.files().get_media(fileId=file_id, supportsAllDrives=True)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        downloader = MediaIoBaseDownload(tmp, req)
        done = False
        while not done:
            _, done = self._download_next_chunk(downloader)
        tmp.close()
        return tmp.name

    def _download_next_chunk(self, downloader, attempts: int = 4):
        last_error = None
        for i in range(attempts):
            try:
                return downloader.next_chunk()
            except (ssl.SSLError, URLError, OSError) as e:
                last_error = e
                if i == attempts - 1:
                    raise
                time.sleep(0.6 * (i + 1))
        raise last_error

    def upload(self, local_path: str, folder_name: str,
               filename: Optional[str] = None) -> str:
        """ローカル→Drive アップロード. ファイルIDを返す."""
        local_folder = self._local_folder(folder_name)
        if local_folder:
            name = filename or os.path.basename(local_path)
            dest = os.path.join(local_folder, name)
            shutil.copy2(local_path, dest)
            return f"local:{dest}"

        folder_id = self._get_or_create_folder(folder_name)
        name = filename or os.path.basename(local_path)
        media = MediaFileUpload(local_path, resumable=True)
        meta = {"name": name, "parents": [folder_id]}
        result = self._execute(self._service.files().create(
            body=meta, media_body=media,
            fields="id", supportsAllDrives=True,
        ))
        return result["id"]

    def upload_bytes(self, file_bytes: bytes, filename: str,
                     folder_name: str, mime_type: str = "application/octet-stream") -> str:
        """写真アプリ/ブラウザから選択したファイルをDriveへ直接アップロード."""
        local_folder = self._local_folder(folder_name)
        if local_folder:
            dest = os.path.join(local_folder, filename)
            with open(dest, "wb") as f:
                f.write(file_bytes)
            return f"local:{dest}"

        folder_id = self._get_or_create_folder(folder_name)
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=True)
        meta = {"name": filename, "parents": [folder_id]}
        result = self._execute(self._service.files().create(
            body=meta, media_body=media,
            fields="id", supportsAllDrives=True,
        ))
        return result["id"]

    def move(self, file_id: str, new_folder_name: str,
             new_name: Optional[str] = None) -> None:
        """ファイルを別フォルダに移動（必要ならリネーム）"""
        local_id = file_id.removeprefix("local:")
        local_folder = self._local_folder(new_folder_name)
        if local_folder and os.path.isfile(local_id):
            dest = os.path.join(local_folder, new_name or os.path.basename(local_id))
            shutil.move(local_id, dest)
            return

        new_parent = self._get_or_create_folder(new_folder_name)
        # 現在の親を取得
        current = self._execute(self._service.files().get(
            fileId=file_id, fields="parents",
            supportsAllDrives=True,
        ))
        prev_parents = ",".join(current.get("parents", []))
        body = {}
        if new_name:
            body["name"] = new_name
        self._execute(self._service.files().update(
            fileId=file_id,
            removeParents=prev_parents,
            addParents=new_parent,
            body=body,
            fields="id, parents",
            supportsAllDrives=True,
        ))

    def delete(self, file_id: str) -> None:
        local_id = file_id.removeprefix("local:")
        if os.path.isfile(local_id):
            os.remove(local_id)
            return

        self._execute(self._service.files().delete(
            fileId=file_id, supportsAllDrives=True,
        ))

    def get_thumbnail_url(self, file_id: str) -> str:
        """ブラウザで表示できる Drive サムネイルURL."""
        return f"https://drive.google.com/thumbnail?id={file_id}&sz=w800"


def get_storage_from_streamlit():
    """Streamlit Cloud / ローカル両対応で DriveStorage を取得."""
    import streamlit as st
    creds_info = None
    # Streamlit Secrets 優先
    try:
        if "gcp_service_account" in st.secrets:
            creds_info = dict(st.secrets["gcp_service_account"])
    except Exception:
        pass
    # ローカルファイル fallback
    if creds_info is None:
        local_path = os.path.join(os.path.dirname(__file__), "service_account.json")
        if os.path.isfile(local_path):
            with open(local_path) as f:
                creds_info = json.load(f)
    return DriveStorage(credentials_info=creds_info)
