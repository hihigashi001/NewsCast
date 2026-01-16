# NewsCast Auto-Generator

Yahoo! ニュース RSS から日本の主要ニュースを自動収集し、英語学習者（B1レベル）向けの4〜5分の対話型ポッドキャスト台本（JSON形式）を生成する Web アプリケーション。

## 機能

- **自動ニュース収集**: Yahoo! ニュース RSS から7カテゴリのニュースを1時間ごとに自動収集
- **管理画面**: Firestore に保存されたニュースを一覧表示・選択
- **AI 台本生成**: Gemini API で Steve & Nancy による対話型英語台本を自動生成
- **認証**: Google 認証で管理画面を保護

## 技術スタック

- **フロントエンド**: Next.js (App Router), TypeScript, Tailwind CSS
- **バックエンド**: Firestore, Firebase Auth
- **AI**: Gemini 1.5 Flash (Google Search Grounding)
- **自動化**: GitHub Actions (Cron)
- **デプロイ**: Vercel

## セットアップ

### 必要な準備

1. Firebase プロジェクトの作成
2. Firestore の有効化
3. サービスアカウントキーの取得
4. Gemini API キーの取得

### インストール

```bash
# Python 依存関係のインストール
pip install -r requirements.txt

# Node.js 依存関係のインストール
npm install
```

### 環境変数の設定

`.env.local` ファイルを作成:

```env
# Firebase
NEXT_PUBLIC_FIREBASE_API_KEY=your_api_key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your_auth_domain
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your_project_id
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=your_storage_bucket
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
NEXT_PUBLIC_FIREBASE_APP_ID=your_app_id

# Gemini API
GEMINI_API_KEY=your_gemini_api_key
```

### ローカル実行

```bash
# 開発サーバーの起動
npm run dev

# ニュース収集スクリプトの実行
python collector/collector.py
```

## プロジェクト構造

```
NewsCast/
├── collector/              # Python ニュース収集スクリプト
│   └── collector.py
├── src/
│   ├── app/               # Next.js App Router
│   │   ├── page.tsx       # メイン画面
│   │   ├── login/         # ログイン画面
│   │   └── api/           # API Routes
│   ├── components/        # React コンポーネント
│   └── lib/              # ユーティリティ
├── .github/
│   └── workflows/         # GitHub Actions
└── requirements.txt       # Python 依存関係
```

## デプロイ

Vercel にデプロイ:

```bash
vercel
```

## ライセンス

MIT
