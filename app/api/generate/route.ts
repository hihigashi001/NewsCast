import { GoogleGenerativeAI } from "@google/generative-ai";
import { NextRequest, NextResponse } from "next/server";

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY || "");

export async function POST(request: NextRequest) {
  try {
    const { news } = await request.json();

    if (!news || news.length !== 3) {
      return NextResponse.json(
        { error: "ニュースは3つ選択してください" },
        { status: 400 }
      );
    }

    // Gemini 2.5 Pro モデルを使用（より高品質なスクリプト生成）
    const model = genAI.getGenerativeModel({
      model: "gemini-2.5-pro-preview-06-05",
    });

    // 改善されたプロンプトの構築
    const prompt = `
あなたは英語学習者（B1レベル）向けのポッドキャスト台本ライターです。
以下の3つの日本のニュースを使って、4〜5分（500〜650語）の対話型ポッドキャスト台本を英語で作成してください。

## ニューストピック
1. **${news[0].title}**
   - カテゴリ: ${news[0].category}
   - 概要: ${news[0].summary || "なし"}

2. **${news[1].title}**
   - カテゴリ: ${news[1].category}
   - 概要: ${news[1].summary || "なし"}

3. **${news[2].title}**
   - カテゴリ: ${news[2].category}
   - 概要: ${news[2].summary || "なし"}

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
- 背景情報を使って詳細を解説
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

{
  "metadata": {
    "duration_est": <分数>,
    "total_words": <総語数>,
    "topics": ["トピック1", "トピック2", "トピック3"]
  },
  "intro": [
    {"speaker": "Steve", "text": "...", "emotion": "neutral"},
    {"speaker": "Nancy", "text": "...", "emotion": "neutral"}
  ],
  "news": [
    {
      "category": "${news[0].category}",
      "original_title": "${news[0].title}",
      "sections": {
        "introduction": [
          {"speaker": "Steve", "text": "...", "emotion": "neutral"},
          {"speaker": "Nancy", "text": "...", "emotion": "curious"}
        ],
        "vocabulary_hook": [
          {"speaker": "Nancy", "text": "What does [word] mean?", "emotion": "curious"},
          {"speaker": "Steve", "text": "...", "emotion": "neutral"}
        ],
        "deep_dive": [
          {"speaker": "Steve", "text": "...", "emotion": "neutral"},
          {"speaker": "Nancy", "text": "...", "emotion": "surprised"}
        ],
        "discussion": [
          {"speaker": "Nancy", "text": "...", "emotion": "curious"},
          {"speaker": "Steve", "text": "...", "emotion": "empathetic"}
        ]
      }
    }
  ],
  "outro": [
    {"speaker": "Steve", "text": "...", "emotion": "neutral"},
    {"speaker": "Nancy", "text": "...", "emotion": "neutral"}
  ]
}

JSONのみを出力してください。追加のテキストは不要です。
`;

    // Gemini API を呼び出し
    const result = await model.generateContent(prompt);
    const response = await result.response;
    let text = response.text();

    // JSON部分を抽出（マークダウンのコードブロックを除去）
    text = text
      .replace(/```json\n?/g, "")
      .replace(/```\n?/g, "")
      .trim();

    // JSONをパース
    const script = JSON.parse(text);

    return NextResponse.json({ script });
  } catch (error) {
    console.error("台本生成エラー:", error);
    console.error("エラーの詳細:", {
      message: error instanceof Error ? error.message : String(error),
      stack: error instanceof Error ? error.stack : undefined,
    });
    return NextResponse.json(
      {
        error: "台本生成に失敗しました",
        details: error instanceof Error ? error.message : String(error),
        type: error instanceof Error ? error.constructor.name : typeof error,
      },
      { status: 500 }
    );
  }
}
