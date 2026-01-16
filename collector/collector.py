#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Yahoo! ニュース RSS からニュースを収集し、Firestore に保存するスクリプト
"""

import feedparser
import firebase_admin
from firebase_admin import credentials, firestore
import hashlib
import os
import json


# Firebase Admin SDK の初期化
def initialize_firebase():
    """Firebase Admin SDK を初期化"""
    if not firebase_admin._apps:
        # サービスアカウントキーの読み込み
        # GitHub Actions 用: 環境変数から読み込み
        if os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY"):
            service_account_info = json.loads(os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY"))
            cred = credentials.Certificate(service_account_info)
        else:
            # ローカル実行用: ファイルから読み込み
            cred = credentials.Certificate("serviceAccountKey.json")

        firebase_admin.initialize_app(cred)

    return firestore.client()


# Yahoo! ニュース RSS のカテゴリ URL
RSS_FEEDS = {
    "主要": "https://news.yahoo.co.jp/rss/topics/top-picks.xml",
    "国内": "https://news.yahoo.co.jp/rss/topics/domestic.xml",
    "国際": "https://news.yahoo.co.jp/rss/topics/world.xml",
    "経済": "https://news.yahoo.co.jp/rss/topics/business.xml",
    "エンタメ": "https://news.yahoo.co.jp/rss/topics/entertainment.xml",
    "スポーツ": "https://news.yahoo.co.jp/rss/topics/sports.xml",
    "IT": "https://news.yahoo.co.jp/rss/topics/it.xml",
}


def generate_doc_id(url):
    """URL からドキュメント ID を生成（ハッシュ化）"""
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def fetch_and_save_news(db):
    """各カテゴリのニュースを取得して Firestore に保存"""
    total_saved = 0

    for category, feed_url in RSS_FEEDS.items():
        print(f"📰 カテゴリ「{category}」を取得中...")

        # RSS フィードをパース
        feed = feedparser.parse(feed_url)

        if not feed.entries:
            print(f"⚠️  カテゴリ「{category}」: エントリが見つかりませんでした")
            continue

        # 各ニュース記事を処理
        for entry in feed.entries:
            # ドキュメント ID を生成
            doc_id = generate_doc_id(entry.link)

            # ニュースデータを構築
            news_data = {
                "category": category,
                "title": entry.title,
                "link": entry.link,
                "summary": entry.get("summary", ""),
                "pub_date": entry.get("published", ""),
                "created_at": firestore.SERVER_TIMESTAMP,
                "status": "unread",  # unread / selected / archived
            }

            # Firestore に保存（merge: true で重複排除）
            db.collection("news").document(doc_id).set(news_data, merge=True)
            total_saved += 1

        print(f"✅ カテゴリ「{category}」: {len(feed.entries)}件 保存完了")

    print(f"\n🎉 合計 {total_saved} 件のニュースを保存しました")


def main():
    """メイン処理"""
    print("=" * 50)
    print("NewsCast - ニュース収集スクリプト")
    print("=" * 50)
    print()

    # Firebase 初期化
    db = initialize_firebase()
    print("✅ Firebase 初期化完了\n")

    # ニュース取得・保存
    fetch_and_save_news(db)

    print("\n" + "=" * 50)
    print("処理完了")
    print("=" * 50)


if __name__ == "__main__":
    main()
