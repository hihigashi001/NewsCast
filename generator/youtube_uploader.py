#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
YouTube アップロードモジュール
YouTube Data API v3 を使用して動画をアップロードします。
"""

import os
import pickle
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError


class YouTubeUploader:
    """YouTube に動画をアップロードするクラス"""

    # OAuth 2.0 スコープ
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

    # YouTube API サービス名とバージョン
    API_SERVICE_NAME = "youtube"
    API_VERSION = "v3"

    def __init__(self, credentials_path: Optional[str] = None):
        """
        YouTubeUploader を初期化

        Args:
            credentials_path: OAuth 認証情報ファイルのパス
        """
        self.credentials_path = credentials_path
        self.youtube = self._get_authenticated_service()

    def _get_authenticated_service(self):
        """認証済みの YouTube サービスを取得"""
        credentials = None

        # 環境変数から認証情報を取得（GitHub Actions 用）
        if os.getenv("YOUTUBE_REFRESH_TOKEN"):
            credentials = self._get_credentials_from_env()

        # ローカル用: token.pickle から読み込み
        token_path = Path(__file__).parent / "token.pickle"
        if credentials is None and token_path.exists():
            with open(token_path, "rb") as token:
                credentials = pickle.load(token)

        # 認証情報の更新が必要な場合
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())

        # 認証情報がない場合はエラー
        if credentials is None:
            raise ValueError(
                "YouTube 認証情報が見つかりません。\n"
                "環境変数 YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN を設定するか、\n"
                "token.pickle ファイルを generator ディレクトリに配置してください。"
            )

        return build(
            self.API_SERVICE_NAME,
            self.API_VERSION,
            credentials=credentials,
        )

    def _get_credentials_from_env(self) -> Credentials:
        """環境変数から認証情報を取得"""
        client_id = os.getenv("YOUTUBE_CLIENT_ID")
        client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
        refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN")

        if not all([client_id, client_secret, refresh_token]):
            return None

        return Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
        )

    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: Optional[list] = None,
        category_id: str = "27",  # Education カテゴリ
        privacy_status: str = "public",
        thumbnail_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        動画を YouTube にアップロード

        Args:
            video_path: 動画ファイルのパス
            title: 動画タイトル
            description: 動画の説明文
            tags: タグのリスト
            category_id: カテゴリID（27 = Education）
            privacy_status: 公開設定（public, unlisted, private）
            thumbnail_path: サムネイル画像のパス

        Returns:
            アップロード結果（video_id, url など）
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"動画ファイルが見つかりません: {video_path}")

        # 動画メタデータ
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags or [],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        # メディアファイル
        media = MediaFileUpload(
            video_path,
            chunksize=1024 * 1024,  # 1MB チャンク
            resumable=True,
        )

        try:
            # 動画をアップロード
            request = self.youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    print(f"アップロード進捗: {int(status.progress() * 100)}%")

            video_id = response["id"]
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            print(f"✅ アップロード完了: {video_url}")

            # サムネイルをアップロード
            if thumbnail_path and os.path.exists(thumbnail_path):
                self.set_thumbnail(video_id, thumbnail_path)

            return {
                "video_id": video_id,
                "url": video_url,
                "title": title,
                "response": response,
            }

        except HttpError as e:
            print(f"❌ YouTube API エラー: {e}")
            raise

    def set_thumbnail(self, video_id: str, thumbnail_path: str) -> bool:
        """
        動画のサムネイルを設定

        Args:
            video_id: 動画ID
            thumbnail_path: サムネイル画像のパス

        Returns:
            成功したかどうか
        """
        try:
            self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path),
            ).execute()

            print(f"✅ サムネイル設定完了: {video_id}")
            return True

        except HttpError as e:
            print(f"⚠️ サムネイル設定エラー: {e}")
            return False

    def generate_video_description(
        self,
        topics: list,
        date: Optional[datetime] = None,
    ) -> str:
        """
        動画の説明文を生成

        Args:
            topics: ニューストピックのリスト
            date: 動画の日付

        Returns:
            説明文
        """
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%Y年%m月%d日")

        topics_text = "\n".join([f"📰 {topic}" for topic in topics])

        description = f"""
🎧 NewsCast - {date_str}

英語学習者（B1レベル）のためのニュースポッドキャストです。
Steve と Nancy が日本の最新ニュースを分かりやすく英語で解説します。

📌 今日のトピック:
{topics_text}

---

🔔 チャンネル登録お願いします！
毎日新しいエピソードを配信中です。

#英語学習 #ニュース #ポッドキャスト #英語リスニング #B1英語
"""
        return description.strip()

    def generate_video_title(
        self,
        topics: list,
        date: Optional[datetime] = None,
    ) -> str:
        """
        動画タイトルを生成

        Args:
            topics: ニューストピックのリスト
            date: 動画の日付

        Returns:
            タイトル
        """
        if date is None:
            date = datetime.now()

        date_str = date.strftime("%m/%d")

        # 最初のトピックを短縮
        main_topic = topics[0] if topics else "Daily News"
        if len(main_topic) > 30:
            main_topic = main_topic[:27] + "..."

        return f"【{date_str}】{main_topic} | NewsCast English"


def create_oauth_token():
    """
    OAuth トークンを作成するヘルパー関数（ローカル実行用）

    client_secrets.json を用意して実行すると、
    ブラウザで認証後に token.pickle が生成されます。
    """
    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

    credentials_path = Path(__file__).parent / "client_secrets.json"
    token_path = Path(__file__).parent / "token.pickle"

    if not credentials_path.exists():
        print("❌ client_secrets.json が見つかりません")
        print("Google Cloud Console からダウンロードしてください")
        return

    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
    credentials = flow.run_local_server(port=8080)

    with open(token_path, "wb") as token:
        pickle.dump(credentials, token)

    print(f"✅ トークンを保存しました: {token_path}")
    print(f"   Refresh Token: {credentials.refresh_token}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--create-token":
        create_oauth_token()
    else:
        print("YouTubeUploader モジュールのテスト")
        print()
        print("使用方法:")
        print("  --create-token: OAuth トークンを作成（ローカル実行用）")
        print()

        try:
            uploader = YouTubeUploader()
            print("✅ YouTubeUploader の初期化に成功しました")
        except Exception as e:
            print(f"⚠️ YouTubeUploader の初期化に失敗: {e}")
