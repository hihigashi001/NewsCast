#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
音声生成モジュール
Edge TTS を使用してマルチスピーカー音声を生成します。
"""

import os
import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    import edge_tts

    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

try:
    from pydub import AudioSegment

    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False


class AudioGenerator:
    """Edge TTS を使用してマルチスピーカー音声を生成するクラス"""

    # 話者ごとの声の設定
    VOICE_CONFIG = {
        "Steve": {
            "voice": "en-US-GuyNeural",  # 男性の声
            "rate": "-10%",
            "pitch": "+0Hz",
        },
        "Nancy": {
            "voice": "en-US-JennyNeural",  # 女性の声
            "rate": "-5%",
            "pitch": "+0Hz",
        },
    }

    # Emotion に応じた調整（rate と pitch を変化させてメリハリを付ける）
    EMOTION_CONFIG = {
        "neutral": {
            "rate_adjust": "+0%",
            "pitch_adjust": "+0Hz",
        },
        "curious": {
            "rate_adjust": "+5%",  # 少し速く
            "pitch_adjust": "+20Hz",  # 声を少し高く
        },
        "surprised": {
            "rate_adjust": "+10%",  # 驚いて速く
            "pitch_adjust": "+40Hz",  # 声を高く
        },
        "empathetic": {
            "rate_adjust": "-5%",  # ゆっくり
            "pitch_adjust": "-10Hz",  # 声を少し低く、落ち着いた感じ
        },
    }

    def __init__(self):
        """AudioGenerator を初期化"""
        if not EDGE_TTS_AVAILABLE:
            raise ImportError(
                "edge-tts パッケージをインストールしてください: pip install edge-tts"
            )
        if not PYDUB_AVAILABLE:
            raise ImportError(
                "pydub パッケージをインストールしてください: pip install pydub"
            )

    def generate_audio(self, script: Dict[str, Any]) -> bytes:
        """
        スクリプト全体から音声を生成

        Args:
            script: スクリプトデータ（ScriptGenerator の出力）

        Returns:
            生成された音声データ（MP3形式）
        """
        # 全ての発話を収集
        all_dialogues = self._extract_all_dialogues(script)

        # 各発話を音声に変換
        return asyncio.run(self._generate_all_audio(all_dialogues))

    async def _generate_all_audio(self, dialogues: List[Dict[str, str]]) -> bytes:
        """全ての発話から音声を生成（emotionに応じて声を調整）"""
        audio_segments = []

        with tempfile.TemporaryDirectory() as temp_dir:
            for i, dialogue in enumerate(dialogues):
                speaker = dialogue.get("speaker", "Steve")
                text = dialogue.get("text", "")
                emotion = dialogue.get("emotion", "neutral")

                if not text.strip():
                    continue

                voice_config = self.VOICE_CONFIG.get(
                    speaker, self.VOICE_CONFIG["Steve"]
                )
                emotion_config = self.EMOTION_CONFIG.get(
                    emotion, self.EMOTION_CONFIG["neutral"]
                )

                # ベースのrate/pitchとemotionの調整を組み合わせる
                base_rate = int(voice_config["rate"].replace("%", "").replace("+", ""))
                emotion_rate = int(
                    emotion_config["rate_adjust"].replace("%", "").replace("+", "")
                )
                final_rate = f"{base_rate + emotion_rate:+d}%"

                final_pitch = emotion_config["pitch_adjust"]

                temp_file = Path(temp_dir) / f"segment_{i}.mp3"

                # Edge TTS で音声生成（emotion対応）
                communicate = edge_tts.Communicate(
                    text,
                    voice_config["voice"],
                    rate=final_rate,
                    pitch=final_pitch,
                )
                await communicate.save(str(temp_file))

                # AudioSegment で読み込み
                segment = AudioSegment.from_mp3(str(temp_file))
                audio_segments.append(segment)

                # 発話間に短い無音を追加
                silence = AudioSegment.silent(duration=400)  # 400ms
                audio_segments.append(silence)

            # 全セグメントを結合
            if not audio_segments:
                return b""

            combined = audio_segments[0]
            for segment in audio_segments[1:]:
                combined += segment

            # バイトデータとして出力
            output_buffer = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            output_path = output_buffer.name
            output_buffer.close()

            combined.export(output_path, format="mp3")

            with open(output_path, "rb") as f:
                audio_data = f.read()

            os.unlink(output_path)
            return audio_data

    def _extract_all_dialogues(self, script: Dict[str, Any]) -> List[Dict[str, str]]:
        """スクリプトから全ての発話を抽出（イントロは除外）"""
        dialogues = []

        # イントロはスキップ（intro_fixed.mp3 を使用）
        # dialogues.extend(script.get("intro", []))

        # 各ニュース
        for news_item in script.get("news", []):
            sections = news_item.get("sections", {})
            for section_name in [
                "introduction",
                "vocabulary_hook",
                "deep_dive",
                "discussion",
            ]:
                dialogues.extend(sections.get(section_name, []))

        # アウトロ
        dialogues.extend(script.get("outro", []))

        return dialogues


class FallbackAudioGenerator:
    """
    フォールバック用の音声生成クラス
    Google Cloud Text-to-Speech API を使用
    """

    def __init__(self):
        """Google Cloud TTS を初期化"""
        try:
            from google.cloud import texttospeech

            self.client = texttospeech.TextToSpeechClient()
            self.tts = texttospeech
        except ImportError:
            raise ImportError(
                "google-cloud-texttospeech パッケージをインストールしてください"
            )

    # 話者ごとの声の設定
    VOICE_CONFIG = {
        "Steve": {
            "name": "en-US-Neural2-D",  # 男性
            "ssml_gender": "MALE",
        },
        "Nancy": {
            "name": "en-US-Neural2-F",  # 女性
            "ssml_gender": "FEMALE",
        },
    }

    def generate_audio(self, script: Dict[str, Any]) -> bytes:
        """
        スクリプトから音声を生成

        Args:
            script: スクリプトデータ

        Returns:
            生成された音声データ（MP3形式）
        """
        audio_segments = []
        dialogues = self._extract_all_dialogues(script)

        for dialogue in dialogues:
            speaker = dialogue.get("speaker", "Steve")
            text = dialogue.get("text", "")

            voice_config = self.VOICE_CONFIG.get(speaker, self.VOICE_CONFIG["Steve"])

            # SSML を構築
            ssml = f"<speak>{text}</speak>"

            synthesis_input = self.tts.SynthesisInput(ssml=ssml)

            voice = self.tts.VoiceSelectionParams(
                language_code="en-US",
                name=voice_config["name"],
            )

            audio_config = self.tts.AudioConfig(
                audio_encoding=self.tts.AudioEncoding.MP3,
                speaking_rate=0.9,
            )

            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )

            audio_segments.append(response.audio_content)

        # 全セグメントを結合
        return b"".join(audio_segments)

    def _extract_all_dialogues(self, script: Dict[str, Any]) -> List[Dict[str, str]]:
        """スクリプトから全ての発話を抽出（イントロは除外）"""
        dialogues = []

        # イントロはスキップ（intro_fixed.mp3 を使用）
        # dialogues.extend(script.get("intro", []))

        for news_item in script.get("news", []):
            sections = news_item.get("sections", {})
            for section_name in [
                "introduction",
                "vocabulary_hook",
                "deep_dive",
                "discussion",
            ]:
                dialogues.extend(sections.get(section_name, []))

        dialogues.extend(script.get("outro", []))

        return dialogues


def get_audio_generator(use_fallback: bool = False):
    """
    音声生成器を取得

    Args:
        use_fallback: True の場合は Google Cloud TTS を使用

    Returns:
        AudioGenerator または FallbackAudioGenerator のインスタンス
    """
    if use_fallback:
        return FallbackAudioGenerator()
    return AudioGenerator()


if __name__ == "__main__":
    print("AudioGenerator モジュールが正常にロードされました")

    # テスト用のスクリプト
    test_script = {
        "intro": [
            {
                "speaker": "Steve",
                "text": "Hello and welcome to NewsCast.",
                "emotion": "neutral",
            },
            {
                "speaker": "Nancy",
                "text": "Today we have exciting news for you!",
                "emotion": "curious",
            },
        ],
        "news": [],
        "outro": [
            {
                "speaker": "Steve",
                "text": "Thank you for listening.",
                "emotion": "neutral",
            },
        ],
    }

    try:
        generator = AudioGenerator()
        print("[OK] AudioGenerator の初期化に成功しました")
    except Exception as e:
        print(f"[Warning] AudioGenerator の初期化に失敗: {e}")
