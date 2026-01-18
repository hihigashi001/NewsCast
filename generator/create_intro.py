#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
イントロ音声生成スクリプト
SteveとNancyの挨拶音声を生成し、BGMと合成してintro_fixed.mp3を作成します。

使用方法:
    python create_intro.py

必要なパッケージ:
    pip install gTTS pydub python-dotenv

必要なファイル:
    generator/assets/bgm/bgm_main.mp3
"""

import os
import sys
import tempfile
from pathlib import Path

# .env.local を読み込む
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env.local"
load_dotenv(env_path)

# パス設定
ASSETS_DIR = Path(__file__).parent / "assets"
BGM_DIR = ASSETS_DIR / "bgm"
BGM_PATH = BGM_DIR / "bgm_main.mp3"
OUTPUT_PATH = ASSETS_DIR / "intro_fixed.mp3"


# イントロ台本（Steve と Nancy の挨拶）
INTRO_SCRIPT = [
    {
        "speaker": "Steve",
        "text": "Hello everyone, and welcome to NewsCast! I'm Steve.",
    },
    {
        "speaker": "Nancy",
        "text": "And I'm Nancy! It's great to have you with us today.",
    },
    {
        "speaker": "Steve",
        "text": "This podcast is for English learners. We'll introduce three news stories from yesterday in an easy-to-understand way.",
    },
    {
        "speaker": "Nancy",
        "text": "That's right! We'll explain difficult words and discuss what these stories mean for our daily lives.",
    },
    {
        "speaker": "Steve",
        "text": "So, let's get started with today's news!",
    },
    {
        "speaker": "Nancy",
        "text": "Here we go!",
    },
]


def generate_speech_with_gtts(script: list, output_path: str):
    """
    gTTS を使用して音声を生成

    Args:
        script: 発話リスト
        output_path: 出力ファイルパス
    """
    from gtts import gTTS
    from pydub import AudioSegment

    print("🎙️ gTTS で音声を生成中...")

    # 各発話を音声に変換
    audio_segments = []

    with tempfile.TemporaryDirectory() as temp_dir:
        for i, item in enumerate(script):
            speaker = item["speaker"]
            text = item["text"]
            temp_file = Path(temp_dir) / f"segment_{i}.mp3"

            # gTTS で音声生成
            tts = gTTS(text=text, lang="en", slow=False)
            tts.save(str(temp_file))

            # AudioSegment で読み込み
            segment = AudioSegment.from_mp3(str(temp_file))

            # 話者によって少し調整（Steve は低め、Nancy は高め）
            if speaker == "Steve":
                # 若干低い声に
                segment = segment._spawn(
                    segment.raw_data,
                    overrides={"frame_rate": int(segment.frame_rate * 0.95)},
                ).set_frame_rate(segment.frame_rate)
            else:
                # 若干高い声に
                segment = segment._spawn(
                    segment.raw_data,
                    overrides={"frame_rate": int(segment.frame_rate * 1.05)},
                ).set_frame_rate(segment.frame_rate)

            audio_segments.append(segment)

            # 発話間に短い無音を追加
            silence = AudioSegment.silent(duration=300)  # 300ms
            audio_segments.append(silence)

            print(f"   {speaker}: OK")

        # 全セグメントを結合
        combined = audio_segments[0]
        for segment in audio_segments[1:]:
            combined += segment

        # MP3 として保存
        combined.export(output_path, format="mp3")

    print("✅ 音声生成完了")


def generate_speech_with_edge_tts(script: list, output_path: str):
    """
    Edge TTS を使用して音声を生成（より自然な声）

    Args:
        script: 発話リスト
        output_path: 出力ファイルパス
    """
    import asyncio
    import edge_tts
    from pydub import AudioSegment

    print("🎙️ Edge TTS で音声を生成中...")

    # 話者ごとの声
    voices = {
        "Steve": "en-US-GuyNeural",  # 男性、落ち着いた声
        "Nancy": "en-US-JennyNeural",  # 女性、明るい声
    }

    async def generate_segment(text: str, voice: str, output_file: str):
        communicate = edge_tts.Communicate(text, voice, rate="-10%")
        await communicate.save(output_file)

    audio_segments = []

    with tempfile.TemporaryDirectory() as temp_dir:
        for i, item in enumerate(script):
            speaker = item["speaker"]
            text = item["text"]
            voice = voices.get(speaker, voices["Steve"])
            temp_file = Path(temp_dir) / f"segment_{i}.mp3"

            # Edge TTS で音声生成
            asyncio.run(generate_segment(text, voice, str(temp_file)))

            # AudioSegment で読み込み
            segment = AudioSegment.from_mp3(str(temp_file))
            audio_segments.append(segment)

            # 発話間に短い無音を追加
            silence = AudioSegment.silent(duration=400)  # 400ms
            audio_segments.append(silence)

            print(f"   {speaker}: OK")

        # 全セグメントを結合
        combined = audio_segments[0]
        for segment in audio_segments[1:]:
            combined += segment

        # MP3 として保存
        combined.export(output_path, format="mp3")

    print("✅ 音声生成完了")


def generate_speech_with_gemini_tts(script: list, output_path: str):
    """
    Gemini 2.5 Flash TTS を使用して音声を生成（高品質・メイン動画と同じ声）

    Args:
        script: 発話リスト
        output_path: 出力ファイルパス
    """
    import os
    import io
    from pydub import AudioSegment

    print("🎙️ Gemini TTS で音声を生成中...")

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 環境変数が設定されていません")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    # 話者ごとの声（audio_generator.py と同じ設定）
    voices = {
        "Steve": "Orus",  # 男性、落ち着いた声
        "Nancy": "Kore",  # 女性、明るい声
    }

    audio_segments = []

    for i, item in enumerate(script):
        speaker = item["speaker"]
        text = item["text"]
        voice_name = voices.get(speaker, voices["Steve"])

        # Gemini TTS で音声生成
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name,
                        )
                    )
                ),
            ),
        )

        # 音声データを取得
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    segment = AudioSegment.from_file(
                        io.BytesIO(part.inline_data.data), format="wav"
                    )
                    audio_segments.append(segment)

                    # 発話間に短い無音を追加
                    silence = AudioSegment.silent(duration=400)
                    audio_segments.append(silence)

        print(f"   {speaker}: OK")

    # 全セグメントを結合
    if not audio_segments:
        raise ValueError("音声生成に失敗しました")

    combined = audio_segments[0]
    for segment in audio_segments[1:]:
        combined += segment

    # MP3 として保存
    combined.export(output_path, format="mp3")

    print("✅ 音声生成完了")


def mix_with_bgm(
    speech_path: str, bgm_path: str, output_path: str, bgm_volume: float = 0.15
):
    """
    音声とBGMを合成

    Args:
        speech_path: 音声ファイルのパス
        bgm_path: BGMファイルのパス
        output_path: 出力ファイルのパス
        bgm_volume: BGMの音量 (0.0-1.0)
    """
    import subprocess

    print(f"🎚️ BGMと合成中... (BGM音量: {int(bgm_volume * 100)}%)")

    # BGMをループして音声の長さに合わせ、音量を調整して合成
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            speech_path,
            "-stream_loop",
            "-1",
            "-i",
            bgm_path,
            "-filter_complex",
            f"[1:a]volume={bgm_volume}[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2",
            "-c:a",
            "libmp3lame",
            "-q:a",
            "2",
            output_path,
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg エラー: {result.stderr}")

    print(f"✅ 合成完了: {output_path}")


def main():
    """メイン処理"""
    print("=" * 60)
    print("NewsCast イントロ音声生成スクリプト")
    print("=" * 60)
    print()

    # ディレクトリを作成
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    BGM_DIR.mkdir(parents=True, exist_ok=True)

    # BGMファイルの確認
    if not BGM_PATH.exists():
        print(f"❌ BGMファイルが見つかりません: {BGM_PATH}")
        print(f"   {BGM_DIR} に bgm_main.mp3 を配置してください")
        sys.exit(1)

    print(f"📂 BGMファイル: {BGM_PATH}")
    print(f"📂 出力先: {OUTPUT_PATH}")
    print()

    # 台本を表示
    print("📝 台本:")
    for item in INTRO_SCRIPT:
        print(f"   {item['speaker']}: {item['text']}")
    print()

    # 一時ファイル用ディレクトリ
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_speech = Path(temp_dir) / "speech.mp3"

        # 音声生成（Gemini TTS → Edge TTS → gTTS のフォールバック）
        try:
            generate_speech_with_gemini_tts(INTRO_SCRIPT, str(temp_speech))
        except Exception as e:
            print(f"⚠️ Gemini TTS エラー: {e}")
            print("   Edge TTS にフォールバック...")

            try:
                generate_speech_with_edge_tts(INTRO_SCRIPT, str(temp_speech))
            except Exception as e2:
                print(f"⚠️ Edge TTS エラー: {e2}")
                print("   gTTS にフォールバック...")

                try:
                    generate_speech_with_gtts(INTRO_SCRIPT, str(temp_speech))
                except Exception as e3:
                    print(f"❌ gTTS エラー: {e3}")
                    print()
                    print(
                        "音声生成に失敗しました。以下のパッケージをインストールしてください:"
                    )
                    print("  pip install google-genai pydub")
                    print("  または")
                    print("  pip install edge-tts pydub")
                    sys.exit(1)

        # BGM と合成
        mix_with_bgm(
            speech_path=str(temp_speech),
            bgm_path=str(BGM_PATH),
            output_path=str(OUTPUT_PATH),
            bgm_volume=0.15,
        )

    print()
    print("=" * 60)
    print("🎉 イントロ音声の生成が完了しました！")
    print(f"   出力ファイル: {OUTPUT_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()
