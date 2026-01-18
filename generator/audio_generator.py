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
from typing import Dict, Any, List

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
        },
        "Nancy": {
            "voice": "en-US-JennyNeural",  # 女性の声
            "rate": "-5%",
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
        """全ての発話から音声を生成"""
        audio_segments = []

        with tempfile.TemporaryDirectory() as temp_dir:
            for i, dialogue in enumerate(dialogues):
                speaker = dialogue.get("speaker", "Steve")
                text = dialogue.get("text", "")

                if not text.strip():
                    continue

                voice_config = self.VOICE_CONFIG.get(
                    speaker, self.VOICE_CONFIG["Steve"]
                )
                temp_file = Path(temp_dir) / f"segment_{i}.mp3"

                # Edge TTS で音声生成
                communicate = edge_tts.Communicate(
                    text,
                    voice_config["voice"],
                    rate=voice_config["rate"],
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
    高品質音声生成クラス
    Google Cloud Text-to-Speech API を使用（WaveNet / Neural2 voices）
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

    # 話者ごとの声の設定（高品質 Neural2 voices）
    VOICE_CONFIG = {
        "Steve": {
            "name": "en-US-Neural2-J",  # 男性、落ち着いた声
            "ssml_gender": "MALE",
            "speaking_rate": 0.92,
        },
        "Nancy": {
            "name": "en-US-Neural2-F",  # 女性、明るい声
            "ssml_gender": "FEMALE",
            "speaking_rate": 0.95,
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
        try:
            from pydub import AudioSegment
        except ImportError:
            raise ImportError("pydub パッケージをインストールしてください")

        audio_segments = []
        dialogues = self._extract_all_dialogues(script)

        for dialogue in dialogues:
            speaker = dialogue.get("speaker", "Steve")
            text = dialogue.get("text", "")

            if not text.strip():
                continue

            voice_config = self.VOICE_CONFIG.get(speaker, self.VOICE_CONFIG["Steve"])

            # SSML を構築（自然な読み上げのため）
            ssml = f'<speak><prosody rate="{voice_config["speaking_rate"]}">{text}</prosody></speak>'

            synthesis_input = self.tts.SynthesisInput(ssml=ssml)

            voice = self.tts.VoiceSelectionParams(
                language_code="en-US",
                name=voice_config["name"],
            )

            audio_config = self.tts.AudioConfig(
                audio_encoding=self.tts.AudioEncoding.MP3,
                speaking_rate=1.0,  # SSMLで制御するので1.0
                pitch=0.0,
            )

            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )

            # バイトデータをAudioSegmentに変換
            import io

            segment = AudioSegment.from_mp3(io.BytesIO(response.audio_content))
            audio_segments.append(segment)

            # 発話間に無音を追加（400ms）
            silence = AudioSegment.silent(duration=400)
            audio_segments.append(silence)

        # 全セグメントを結合
        if not audio_segments:
            return b""

        combined = audio_segments[0]
        for segment in audio_segments[1:]:
            combined += segment

        # MP3として出力
        import tempfile

        output_buffer = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        output_path = output_buffer.name
        output_buffer.close()

        combined.export(output_path, format="mp3")

        import os

        with open(output_path, "rb") as f:
            audio_data = f.read()
        os.unlink(output_path)

        return audio_data

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


class GeminiAudioGenerator:
    """
    Gemini 2.5 Flash TTS を使用した高品質音声生成クラス
    感情制御とマルチスピーカー対応
    """

    MODEL = "gemini-2.5-flash-preview-tts"

    # 話者ごとの声の設定
    VOICE_CONFIG = {
        "Steve": {
            "voice_name": "Orus",  # 男性、落ち着いた声
            "style": "calm, clear, and explanatory like a news anchor",
        },
        "Nancy": {
            "voice_name": "Kore",  # 女性、明るい声
            "style": "friendly, warm, and curious like a co-host",
        },
    }

    # Emotion に応じたスタイル指示
    EMOTION_STYLE = {
        "neutral": "speak in a normal, professional tone",
        "curious": "speak with curiosity and genuine interest, slightly upbeat",
        "surprised": "speak with surprise and excitement, with emphasis",
        "empathetic": "speak with empathy and warmth, in a caring tone",
    }

    def __init__(self):
        """Gemini TTS を初期化"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY 環境変数が設定されていません")

        from google import genai

        self.client = genai.Client(api_key=api_key)

    def generate_audio(self, script: Dict[str, Any]) -> bytes:
        """
        スクリプトから音声を生成（Gemini TTS）

        Args:
            script: スクリプトデータ

        Returns:
            生成された音声データ（WAV形式）
        """
        import time
        from google.genai import types
        from google.genai.errors import ClientError, ServerError

        dialogues = self._extract_all_dialogues(script)

        if not dialogues:
            return b""

        audio_segments = []

        # レート制限対策: 1分あたり10リクエストなので、リクエスト間に待機
        request_interval = 7.0  # 7秒間隔で1分あたり約8-9リクエスト（安全マージン）
        max_retries = 5
        base_wait = 3.0  # 基本待機時間（秒）

        for i, dialogue in enumerate(dialogues):
            speaker = dialogue.get("speaker", "Steve")
            text = dialogue.get("text", "")
            # emotion は将来の感情制御機能で使用予定
            # emotion = dialogue.get("emotion", "neutral")
            # emotion_style = self.EMOTION_STYLE.get(emotion, self.EMOTION_STYLE["neutral"])

            if not text.strip():
                continue

            voice_config = self.VOICE_CONFIG.get(speaker, self.VOICE_CONFIG["Steve"])

            # リトライロジック付き音声生成
            for retry in range(max_retries):
                try:
                    # レート制限対策: リクエスト間に待機（最初のリクエスト以外）
                    if i > 0 and retry == 0:
                        time.sleep(request_interval)

                    response = self.client.models.generate_content(
                        model=self.MODEL,
                        contents=text,
                        config=types.GenerateContentConfig(
                            response_modalities=["AUDIO"],
                            speech_config=types.SpeechConfig(
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                        voice_name=voice_config["voice_name"],
                                    )
                                )
                            ),
                        ),
                    )

                    # 音声データを取得（MIMEタイプも保存）
                    if response.candidates and response.candidates[0].content.parts:
                        for part in response.candidates[0].content.parts:
                            if part.inline_data and part.inline_data.data:
                                mime_type = getattr(
                                    part.inline_data, "mime_type", "audio/wav"
                                )
                                audio_segments.append(
                                    {
                                        "data": part.inline_data.data,
                                        "mime_type": mime_type,
                                    }
                                )

                    break  # 成功したらループを抜ける

                except ClientError as e:
                    error_code = getattr(e, "code", None) or getattr(
                        e, "status_code", None
                    )
                    if error_code == 429:
                        # レート制限エラー: 指数バックオフでリトライ
                        wait_time = base_wait * (2**retry)
                        print(
                            f"   ⏳ レート制限 - {wait_time:.1f}秒待機後リトライ ({retry + 1}/{max_retries})"
                        )
                        time.sleep(wait_time)
                        if retry == max_retries - 1:
                            raise  # 最後のリトライも失敗したら例外を再送出
                    else:
                        raise  # 429以外のクライアントエラーはそのまま送出
                except ServerError as e:
                    # 500/503などのサーバーエラー: 指数バックオフでリトライ
                    error_code = getattr(e, "code", None) or getattr(
                        e, "status_code", 500
                    )
                    wait_time = base_wait * (2**retry)
                    print(
                        f"   ⏳ サーバーエラー({error_code}) - {wait_time:.1f}秒待機後リトライ ({retry + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                    if retry == max_retries - 1:
                        raise  # 最後のリトライも失敗したら例外を再送出

        if not audio_segments:
            return b""

        # pydub で結合（無音を追加）
        try:
            from pydub import AudioSegment
            import io

            # MIMEタイプからフォーマットを判定
            def get_format_from_mime(mime_type: str) -> str:
                mime_to_format = {
                    "audio/wav": "wav",
                    "audio/x-wav": "wav",
                    "audio/mpeg": "mp3",
                    "audio/mp3": "mp3",
                    "audio/ogg": "ogg",
                    "audio/flac": "flac",
                    "audio/L16": "raw",
                    "audio/pcm": "raw",
                }
                return mime_to_format.get(mime_type, "wav")

            combined = None
            for audio_info in audio_segments:
                audio_data = audio_info["data"]
                mime_type = audio_info["mime_type"]

                # 空データはスキップ
                if not audio_data or len(audio_data) < 10:
                    print("   ⚠️ 空の音声データをスキップ")
                    continue

                audio_format = get_format_from_mime(mime_type)

                try:
                    # PCM/raw形式の場合は特別な処理が必要
                    if audio_format == "raw" or mime_type.startswith("audio/L16"):
                        # Gemini TTSはL16 (16-bit PCM) を返す
                        segment = AudioSegment(
                            data=audio_data,
                            sample_width=2,  # 16-bit = 2 bytes
                            frame_rate=24000,  # Gemini TTSのデフォルトサンプルレート
                            channels=1,  # モノラル
                        )
                    else:
                        segment = AudioSegment.from_file(
                            io.BytesIO(audio_data), format=audio_format
                        )

                    if combined is None:
                        combined = segment
                    else:
                        silence = AudioSegment.silent(duration=400)
                        combined += silence + segment
                except Exception as e:
                    print(f"   ⚠️ 音声デコードエラー: {e}")
                    continue

            if combined is None:
                return b""

            output_buffer = io.BytesIO()
            combined.export(output_buffer, format="wav")
            return output_buffer.getvalue()

        except ImportError:
            return audio_segments[0]["data"] if audio_segments else b""

    def _extract_all_dialogues(self, script: Dict[str, Any]) -> List[Dict[str, str]]:
        """スクリプトから全ての発話を抽出（イントロは除外）"""
        dialogues = []

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


def get_audio_generator(engine: str = "gemini"):
    """
    音声生成器を取得

    Args:
        engine: 使用するTTSエンジン
            - "gemini": Gemini 2.5 Flash TTS（デフォルト、高品質、感情対応）
            - "google_cloud": Google Cloud TTS（高品質）
            - "edge": Edge TTS（無料）

    Returns:
        音声生成器のインスタンス
    """
    if engine == "gemini":
        return GeminiAudioGenerator()
    elif engine == "google_cloud":
        return FallbackAudioGenerator()
    else:
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
