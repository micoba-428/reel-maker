"""
Google Drive API ストレージレイヤー
ローカルファイルシステムと同じインタフェースで Drive にアクセス
"""

import io
import json
import os
import tempfile
from typing import List, Optional, Dict

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
        if not credentials_info:
            raise ValueError("認証情報が必要です（credentials_info または credentials_path）")

        creds = service_account.Credentials.from_service_account_info(
            credentials_info, scopes=SCOPES,
        )
        self._service = build("drive", "v3", credentials=creds)
        self._folder_cache: Dict[str, str] = {}  # path -> folder_id
        self._root_name = root_folder_name
        self._root_id = self._find_root_folder()

    # ── 内部 ──────────────────────────────────────────────────────────────
    def _find_root_folder(self) -> str:
        """共有された reel_maker フォルダIDを取得."""
        q = (f"name = '{self._root_name}' and "
             f"mimeType = 'application/vnd.google-apps.folder' and "
             f"trashed = false")
        resp = self._service.files().list(
            q=q,
            fields="files(id, name, owners)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
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
        resp = self._service.files().list(
            q=q, fields="files(id)",
            supportsAllDrives=True, includeItemsFromAllDrives=True,
        ).execute()
        files = resp.get("files", [])
        if files:
            fid = files[0]["id"]
        else:
            meta = {
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent],
            }
            fid = self._service.files().create(
                body=meta, fields="id", supportsAllDrives=True,
            ).execute()["id"]
        self._folder_cache[cache_key] = fid
        return fid

    # ── 公開API ───────────────────────────────────────────────────────────
    def root_id(self) -> str:
        return self._root_id

    def folder_id(self, name: str) -> str:
        """root配下の名前付きフォルダIDを取得（無ければ作成）"""
        return self._get_or_create_folder(name)

    def list_files(self, folder_name: str) -> List[dict]:
        """指定フォルダのファイル一覧（id, name, mimeType, modifiedTime）"""
        folder_id = self._get_or_create_folder(folder_name)
        q = f"'{folder_id}' in parents and trashed = false"
        all_files = []
        page_token = None
        while True:
            resp = self._service.files().list(
                q=q,
                fields="nextPageToken, files(id, name, mimeType, modifiedTime, size)",
                pageToken=page_token,
                supportsAllDrives=True, includeItemsFromAllDrives=True,
                orderBy="modifiedTime",
            ).execute()
            all_files.extend(resp.get("files", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        # ディレクトリは除外
        return [f for f in all_files
                if f.get("mimeType") != "application/vnd.google-apps.folder"]

    def download_to_temp(self, file_id: str, suffix: str = "") -> str:
        """ファイルを /tmp に DL してパスを返す."""
        req = self._service.files().get_media(fileId=file_id, supportsAllDrives=True)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        downloader = MediaIoBaseDownload(tmp, req)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        tmp.close()
        return tmp.name

    def upload(self, local_path: str, folder_name: str,
               filename: Optional[str] = None) -> str:
        """ローカル→Drive アップロード. ファイルIDを返す."""
        folder_id = self._get_or_create_folder(folder_name)
        name = filename or os.path.basename(local_path)
        media = MediaFileUpload(local_path, resumable=True)
        meta = {"name": name, "parents": [folder_id]}
        result = self._service.files().create(
            body=meta, media_body=media,
            fields="id", supportsAllDrives=True,
        ).execute()
        return result["id"]

    def upload_bytes(self, file_bytes: bytes, filename: str,
                     folder_name: str, mime_type: str = "application/octet-stream") -> str:
        """バイト列を直接Drive にアップロード（カメラロールから）. ファイルIDを返す."""
        folder_id = self._get_or_create_folder(folder_name)
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=True)
        meta = {"name": filename, "parents": [folder_id]}
        result = self._service.files().create(
            body=meta, media_body=media,
            fields="id", supportsAllDrives=True,
        ).execute()
        return result["id"]

    def move(self, file_id: str, new_folder_name: str,
             new_name: Optional[str] = None) -> None:
        """ファイルを別フォルダに移動（必要ならリネーム）"""
        new_parent = self._get_or_create_folder(new_folder_name)
        # 現在の親を取得
        current = self._service.files().get(
            fileId=file_id, fields="parents",
            supportsAllDrives=True,
        ).execute()
        prev_parents = ",".join(current.get("parents", []))
        body = {}
        if new_name:
            body["name"] = new_name
        self._service.files().update(
            fileId=file_id,
            removeParents=prev_parents,
            addParents=new_parent,
            body=body,
            fields="id, parents",
            supportsAllDrives=True,
        ).execute()

    def delete(self, file_id: str) -> None:
        self._service.files().delete(
            fileId=file_id, supportsAllDrives=True,
        ).execute()

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
    if creds_info is None:
        raise RuntimeError(
            "サービスアカウント認証情報が見つかりません。"
            "Streamlit Secrets または service_account.json を設定してください。"
        )
    return DriveStorage(credentials_info=creds_info)
