#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
スクリプト生成モジュール
Gemini API を使用して英語学習者向けの対話スクリプトを生成します。
"""

import os
import json
from typing import List, Dict, Any

from google import genai
from google.genai import types


class ScriptGenerator:
    """英語学習者向け対話スクリプトを生成するクラス"""

    def __init__(self):
        """Gemini API を初期化"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY 環境変数が設定されていません")

        self.client = genai.Client(api_key=api_key)
        # Gemini 2.5 Pro を使用
        self.model = "gemini-2.5-pro"

    def generate_script(self, news_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        ニュース記事からポッドキャストスクリプトを生成

        Args:
            news_items: ニュース記事のリスト（3件）
                - title: 日本語タイトル
                - link: 記事URL
                - category: カテゴリ
                - summary: 記事の要約

        Returns:
            生成されたスクリプト（JSON形式）
        """
        if len(news_items) != 3:
            raise ValueError("ニュース記事は3件必要です")

        prompt = self._build_prompt(news_items)

        # Gemini API を呼び出し（Google Search Grounding 付き）
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=8192,
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )

        # レスポンスからJSONを抽出
        text = response.text
        text = (
            text.replace("```json\n", "")
            .replace("```\n", "")
            .replace("```", "")
            .strip()
        )

        return json.loads(text)

    def _build_prompt(self, news_items: List[Dict[str, Any]]) -> str:
        """Gemini 用のプロンプトを構築"""

        news_section = "\n".join(
            [
                f"{i + 1}. **{item['title']}**\n"
                f"   - カテゴリ: {item['category']}\n"
                f"   - 記事URL: {item['link']}\n"
                f"   - 概要: {item.get('summary', 'なし')}"
                for i, item in enumerate(news_items)
            ]
        )

        return f"""
あなたは英語学習者（B1レベル）向けのポッドキャスト台本ライターです。
以下の3つの日本のニュースを使って、4〜5分（500〜650語）の対話型ポッドキャスト台本を英語で作成してください。

## ニューストピック
{news_section}

## 話者設定
- **Steve（男性）**: 解説役。冷静で知識豊富。ゆっくり明確に話す。
- **Nancy（女性）**: 聞き手役。明るく好奇心旺盛。視聴者の疑問を代弁する。

## 各ニュースの対話フロー構造（必須）

各ニュースについて、以下の4つのセクションを必ず含めてください：

### 1. Introduction (2ターン)
- ニュースタイトルをB1レベルの平易な英語に翻訳して紹介

### 2. Vocabulary Hook (2ターン)
- 重要な単語を1つ抽出
- Nancy が「What does [word] mean?」と質問
- Steve が簡潔に説明

### 3. Deep Dive (3〜4ターン)
- Google検索で得た背景情報を使って詳細を解説
- なぜこのニュースが重要なのかを説明

### 4. Discussion (2ターン)
- このニュースが日本や日常生活にどう影響するかを議論
- 二人の意見を交わす

## 制約条件
- B1レベルの英語を使用（高校生向けの語彙）
- 各発話: 最大30語、1〜2文
- 総語数: 500〜650語
- 自然な会話の流れ

## エモーション制御
各発話に以下のいずれかの emotion タグを付けてください：
- neutral: 通常の説明
- curious: 興味・質問
- surprised: 驚き
- empathetic: 共感

## 出力形式（JSON）

```json
{{
  "metadata": {{
    "duration_est": <分数>,
    "total_words": <総語数>,
    "topics": ["トピック1", "トピック2", "トピック3"]
  }},
  "intro": [
    {{"speaker": "Steve", "text": "...", "emotion": "neutral"}},
    {{"speaker": "Nancy", "text": "...", "emotion": "neutral"}}
  ],
  "news": [
    {{
      "category": "{news_items[0]["category"]}",
      "original_title": "{news_items[0]["title"]}",
      "sections": {{
        "introduction": [
          {{"speaker": "Steve", "text": "...", "emotion": "neutral"}},
          {{"speaker": "Nancy", "text": "...", "emotion": "curious"}}
        ],
        "vocabulary_hook": [
          {{"speaker": "Nancy", "text": "What does [word] mean?", "emotion": "curious"}},
          {{"speaker": "Steve", "text": "...", "emotion": "neutral"}}
        ],
        "deep_dive": [
          {{"speaker": "Steve", "text": "...", "emotion": "neutral"}},
          {{"speaker": "Nancy", "text": "...", "emotion": "surprised"}},
          ...
        ],
        "discussion": [
          {{"speaker": "Nancy", "text": "...", "emotion": "curious"}},
          {{"speaker": "Steve", "text": "...", "emotion": "empathetic"}}
        ]
      }}
    }},
    // news[1], news[2] も同様の構造
  ],
  "outro": [
    {{"speaker": "Steve", "text": "...", "emotion": "neutral"}},
    {{"speaker": "Nancy", "text": "...", "emotion": "neutral"}}
  ]
}}
```

JSONのみを出力してください。追加のテキストは不要です。
"""


if __name__ == "__main__":
    # テスト用
    generator = ScriptGenerator()
    test_news = [
        {
            "title": "テストニュース1",
            "link": "https://example.com/1",
            "category": "主要",
            "summary": "テスト概要1",
        },
        {
            "title": "テストニュース2",
            "link": "https://example.com/2",
            "category": "国際",
            "summary": "テスト概要2",
        },
        {
            "title": "テストニュース3",
            "link": "https://example.com/3",
            "category": "経済",
            "summary": "テスト概要3",
        },
    ]
    script = generator.generate_script(test_news)
    print(json.dumps(script, indent=2, ensure_ascii=False))
