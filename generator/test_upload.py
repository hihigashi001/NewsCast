#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
YouTube アップロードテスト用スクリプト
既存の動画ファイルでアップロードだけをテストします。
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

import pytz

# .env.local を読み込む
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env.local"
load_dotenv(env_path)

from youtube_uploader import YouTubeUploader

JST = pytz.timezone("Asia/Tokyo")


def main():
    parser = argparse.ArgumentParser(description="YouTube アップロードテスト")
    parser.add_argument(
        "--video",
        type=str,
        help="動画ファイルのパス（省略時は最新のファイルを自動検出）",
    )
    parser.add_argument(
        "--thumbnail",
        type=str,
        help="サムネイルファイルのパス（省略時は最新のファイルを自動検出）",
    )
    parser.add_argument(
        "--title",
        type=str,
        help="動画タイトル（省略時は自動生成）",
    )
    parser.add_argument(
        "--private",
        action="store_true",
        help="非公開でアップロード",
    )

    args = parser.parse_args()

    output_dir = Path(__file__).parent / "output"

    # 動画ファイルを取得
    if args.video:
        video_path = Path(args.video)
    else:
        # 最新の動画ファイルを検索
        video_files = sorted(output_dir.glob("newscast_*.mp4"), reverse=True)
        if not video_files:
            print("❌ 動画ファイルが見つかりません")
            return 1
        video_path = video_files[0]
        print(f"📹 最新の動画を使用: {video_path.name}")

    if not video_path.exists():
        print(f"❌ 動画ファイルが存在しません: {video_path}")
        return 1

    # サムネイルファイルを取得
    if args.thumbnail:
        thumbnail_path = Path(args.thumbnail)
    else:
        # 動画と同じ日付のサムネイルを検索
        date_str = video_path.stem.replace("newscast_", "")
        thumbnail_path = output_dir / f"thumbnail_{date_str}.jpg"
        if not thumbnail_path.exists():
            thumbnail_path = None
            print("⚠️ サムネイルが見つかりません（スキップ）")
        else:
            print(f"🖼️ サムネイルを使用: {thumbnail_path.name}")

    # アップローダー初期化
    print()
    print("🔑 YouTube API 認証中...")
    try:
        uploader = YouTubeUploader()
        print("✅ 認証成功")
    except Exception as e:
        print(f"❌ 認証エラー: {e}")
        return 1

    # タイトルと説明文を生成
    now = datetime.now(JST)
    topics = ["テストアップロード"]

    title = args.title if args.title else uploader.generate_video_title(topics, now)
    description = uploader.generate_video_description(topics, now)

    privacy = "private" if args.private else "public"

    print()
    print("=" * 50)
    print(f"📤 アップロード開始")
    print(f"   タイトル: {title}")
    print(f"   公開状態: {privacy}")
    print("=" * 50)
    print()

    try:
        result = uploader.upload_video(
            video_path=str(video_path),
            title=title,
            description=description,
            tags=["テスト", "NewsCast"],
            thumbnail_path=str(thumbnail_path) if thumbnail_path else None,
            privacy_status=privacy,
        )

        print()
        print("🎉 アップロード成功！")
        print(f"   動画ID: {result['video_id']}")
        print(f"   URL: {result['url']}")
        return 0

    except Exception as e:
        print(f"❌ アップロードエラー: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
