#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NewsCast メイン処理
動画生成ワークフロー全体を統括します。
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# .env.local を読み込む
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env.local"
load_dotenv(env_path)

import pytz

import firebase_admin
from firebase_admin import credentials, firestore

from script_generator import ScriptGenerator
from audio_generator import get_audio_generator
from audio_mixer import AudioMixer
from video_generator import VideoGenerator
from youtube_uploader import YouTubeUploader


# 設定
JST = pytz.timezone("Asia/Tokyo")
OUTPUT_DIR = Path(__file__).parent / "output"


def initialize_firebase():
    """Firebase Admin SDK を初期化"""
    if not firebase_admin._apps:
        # GitHub Actions 用: 環境変数から読み込み
        if os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY"):
            service_account_info = json.loads(os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY"))
            cred = credentials.Certificate(service_account_info)
        else:
            # ローカル実行用: ファイルから読み込み
            cred = credentials.Certificate(
                Path(__file__).parent.parent / "serviceAccountKey.json"
            )

        firebase_admin.initialize_app(cred)

    return firestore.client()


def get_selected_news(db, limit: int = 3) -> list:
    """
    status='selected' のニュース記事を取得

    Args:
        db: Firestore クライアント
        limit: 取得する記事数

    Returns:
        ニュース記事のリスト（選択された記事のみ）
    """
    news_ref = db.collection("news")
    query = news_ref.where("status", "==", "selected").limit(limit)

    docs = query.stream()
    news_items = []

    for doc in docs:
        data = doc.to_dict()
        data["id"] = doc.id
        news_items.append(data)

    return news_items


def update_news_status(db, news_ids: list, status: str = "archived"):
    """
    ニュース記事のステータスを更新

    Args:
        db: Firestore クライアント
        news_ids: 更新する記事IDのリスト
        status: 新しいステータス
    """
    batch = db.batch()

    for news_id in news_ids:
        doc_ref = db.collection("news").document(news_id)
        batch.update(doc_ref, {"status": status})

    batch.commit()
    print(f"✅ {len(news_ids)} 件の記事を '{status}' に更新しました")


def generate_and_upload_video(
    news_items: list,
    dry_run: bool = False,
    use_fallback_tts: bool = False,
) -> dict:
    """
    動画を生成して YouTube にアップロード

    Args:
        news_items: ニュース記事のリスト
        dry_run: True の場合はアップロードをスキップ
        use_fallback_tts: True の場合は Google Cloud TTS を使用

    Returns:
        処理結果
    """
    # 出力ディレクトリを作成
    OUTPUT_DIR.mkdir(exist_ok=True)

    now = datetime.now(JST)
    date_str = now.strftime("%Y%m%d")

    print("=" * 60)
    print(f"NewsCast 動画生成開始 - {now.strftime('%Y年%m月%d日 %H:%M')}")
    print("=" * 60)
    print()

    # 1. スクリプト生成
    print("📝 ステップ 1/5: スクリプト生成...")
    script_generator = ScriptGenerator()
    script = script_generator.generate_script(news_items)

    # スクリプトを保存
    script_path = OUTPUT_DIR / f"script_{date_str}.json"
    with open(script_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    print(f"   スクリプト保存: {script_path}")

    # 2. 音声生成
    print("🎙️ ステップ 2/5: 音声生成...")
    # デフォルトでGemini TTS（高品質・感情対応）
    tts_engine = "edge" if use_fallback_tts else "gemini"
    audio_generator = get_audio_generator(engine=tts_engine)
    audio_data = audio_generator.generate_audio(script)

    # 一時ファイルに保存
    temp_audio_path = OUTPUT_DIR / f"temp_audio_{date_str}.wav"
    with open(temp_audio_path, "wb") as f:
        f.write(audio_data)
    print(f"   音声保存: {temp_audio_path}")

    # 3. 音声編集
    print("🎚️ ステップ 3/5: 音声編集...")
    audio_mixer = AudioMixer()

    # MP3 に変換
    main_audio_path = OUTPUT_DIR / f"main_audio_{date_str}.mp3"
    audio_mixer.convert_to_mp3(str(temp_audio_path), str(main_audio_path))

    # ニュースセクションにBGMを追加（イントロと同じ音量 0.15）
    bgm_news_path = audio_mixer.assets_dir / "bgm" / "bgm_news.mp3"
    if bgm_news_path.exists():
        main_with_bgm_path = OUTPUT_DIR / f"main_with_bgm_{date_str}.mp3"
        audio_mixer.add_background_music(
            speech_path=str(main_audio_path),
            bgm_path=str(bgm_news_path),
            output_path=str(main_with_bgm_path),
            bgm_volume=0.15,  # イントロと同じ音量
        )
        print(f"   BGM追加: {bgm_news_path.name}")
        main_audio_for_mix = str(main_with_bgm_path)
    else:
        print(f"   ⚠️ BGMファイルが見つかりません: {bgm_news_path}")
        main_audio_for_mix = str(main_audio_path)

    # イントロと結合
    final_audio_path = OUTPUT_DIR / f"final_audio_{date_str}.mp3"
    audio_mixer.mix_audio(main_audio_for_mix, str(final_audio_path))

    # 正規化
    normalized_audio_path = OUTPUT_DIR / f"normalized_audio_{date_str}.mp3"
    audio_mixer.normalize_audio(str(final_audio_path), str(normalized_audio_path))
    print(f"   最終音声: {normalized_audio_path}")

    # 4. 動画生成
    print("🎬 ステップ 4/5: 動画生成...")
    video_generator = VideoGenerator()

    topics = [item["title"] for item in news_items]
    video_path = OUTPUT_DIR / f"newscast_{date_str}.mp4"

    video_generator.generate_video(
        audio_path=str(normalized_audio_path),
        output_path=str(video_path),
        title="NewsCast",
        topics=topics,
        script=script,
    )
    print(f"   動画保存: {video_path}")

    # サムネイル生成
    thumbnail_path = OUTPUT_DIR / f"thumbnail_{date_str}.jpg"
    video_generator.generate_thumbnail(
        output_path=str(thumbnail_path),
        title="NewsCast",
        topics=topics,
    )
    print(f"   サムネイル: {thumbnail_path}")

    # 5. YouTube アップロード
    result = {
        "video_path": str(video_path),
        "thumbnail_path": str(thumbnail_path),
        "script_path": str(script_path),
        "topics": topics,
        "news_ids": [item["id"] for item in news_items],
    }

    if dry_run:
        print("⏭️ ステップ 5/5: アップロードスキップ（ドライラン）")
        result["dry_run"] = True
    else:
        print("📤 ステップ 5/5: YouTube アップロード...")
        uploader = YouTubeUploader()

        title = uploader.generate_video_title(topics, now)
        description = uploader.generate_video_description(topics, now)

        upload_result = uploader.upload_video(
            video_path=str(video_path),
            title=title,
            description=description,
            tags=[
                "英語学習",
                "ニュース",
                "ポッドキャスト",
                "英語リスニング",
                "B1英語",
                "NewsCast",
            ],
            thumbnail_path=str(thumbnail_path),
        )

        result["video_id"] = upload_result["video_id"]
        result["video_url"] = upload_result["url"]

    print()
    print("=" * 60)
    print("🎉 処理完了！")
    print("=" * 60)

    return result


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="NewsCast 動画生成")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="アップロードをスキップ（テスト用）",
    )
    parser.add_argument(
        "--use-fallback-tts",
        action="store_true",
        help="Edge TTS を使用（Gemini TTS の代わりに無料の Edge TTS を使う場合）",
    )
    parser.add_argument(
        "--skip-status-update",
        action="store_true",
        help="記事ステータスの更新をスキップ",
    )

    args = parser.parse_args()

    try:
        # Firebase 初期化
        print("🔥 Firebase 初期化中...")
        db = initialize_firebase()
        print("✅ Firebase 初期化完了")
        print()

        # 選択された記事を取得
        print("📰 選択された記事を取得中...")
        news_items = get_selected_news(db)

        if len(news_items) == 0:
            print("📭 選択された記事がありません。動画生成をスキップします。")
            return 0  # 正常終了

        if len(news_items) < 3:
            print(f"⚠️ 選択された記事が {len(news_items)} 件しかありません（3件必要）")
            print("📭 動画生成をスキップします。")
            return 0  # 正常終了

        print("   取得した記事:")
        for i, item in enumerate(news_items, 1):
            print(f"   {i}. [{item['category']}] {item['title']}")
        print()

        # 動画生成とアップロード
        result = generate_and_upload_video(
            news_items,
            dry_run=args.dry_run,
            use_fallback_tts=args.use_fallback_tts,
        )

        # 記事ステータスを更新
        if not args.skip_status_update and not args.dry_run:
            update_news_status(db, result["news_ids"], "archived")

        # 結果を表示
        print()
        print("📊 処理結果:")
        print(f"   動画: {result['video_path']}")
        if "video_url" in result:
            print(f"   URL: {result['video_url']}")

        return 0

    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
