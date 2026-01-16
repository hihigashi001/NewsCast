#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
音声編集モジュール
FFmpeg を使用して音声ファイルを結合・ミキシングします。
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List


class AudioMixer:
    """FFmpeg を使用して音声をミキシングするクラス"""

    def __init__(self, assets_dir: Optional[str] = None):
        """
        AudioMixer を初期化

        Args:
            assets_dir: アセットファイルが格納されているディレクトリ
        """
        if assets_dir is None:
            # デフォルトは generator/assets ディレクトリ
            self.assets_dir = Path(__file__).parent / "assets"
        else:
            self.assets_dir = Path(assets_dir)

        self.intro_path = self.assets_dir / "intro_fixed.mp3"

        # FFmpeg のパスを確認
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """FFmpeg がインストールされているか確認"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError("FFmpeg の実行に失敗しました")
        except FileNotFoundError:
            raise RuntimeError(
                "FFmpeg がインストールされていません。インストールしてください。"
            )

    def mix_audio(
        self,
        main_audio_path: str,
        output_path: str,
        include_intro: bool = True,
    ) -> str:
        """
        イントロと本編音声を結合

        Args:
            main_audio_path: 本編音声ファイルのパス
            output_path: 出力ファイルのパス
            include_intro: イントロを含めるかどうか

        Returns:
            出力ファイルのパス
        """
        if include_intro and self.intro_path.exists():
            # イントロと本編を結合
            return self._concat_audio_files(
                [str(self.intro_path), main_audio_path],
                output_path,
            )
        else:
            # イントロなしの場合はそのままコピー
            subprocess.run(
                ["ffmpeg", "-y", "-i", main_audio_path, "-c", "copy", output_path],
                capture_output=True,
            )
            return output_path

    def _concat_audio_files(self, audio_files: List[str], output_path: str) -> str:
        """
        複数の音声ファイルを結合

        Args:
            audio_files: 結合する音声ファイルのリスト
            output_path: 出力ファイルのパス

        Returns:
            出力ファイルのパス
        """
        # 一時ファイルリストを作成
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            for audio_file in audio_files:
                # パスをエスケープ
                escaped_path = audio_file.replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")
            concat_list_path = f.name

        try:
            # FFmpeg で結合
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    concat_list_path,
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

            return output_path
        finally:
            # 一時ファイルを削除
            os.unlink(concat_list_path)

    def convert_to_mp3(self, input_path: str, output_path: str) -> str:
        """
        音声ファイルを MP3 に変換

        Args:
            input_path: 入力ファイルのパス
            output_path: 出力ファイルのパス

        Returns:
            出力ファイルのパス
        """
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                input_path,
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

        return output_path

    def add_background_music(
        self,
        speech_path: str,
        bgm_path: str,
        output_path: str,
        bgm_volume: float = 0.1,
    ) -> str:
        """
        スピーチにBGMを追加

        Args:
            speech_path: スピーチ音声のパス
            bgm_path: BGM ファイルのパス
            output_path: 出力ファイルのパス
            bgm_volume: BGM の音量（0.0〜1.0）

        Returns:
            出力ファイルのパス
        """
        # BGM を speech の長さにループし、音量を調整して合成
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
                f"[1:a]volume={bgm_volume}[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=3",
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

        return output_path

    def normalize_audio(self, input_path: str, output_path: str) -> str:
        """
        音声を正規化（音量を均一化）

        Args:
            input_path: 入力ファイルのパス
            output_path: 出力ファイルのパス

        Returns:
            出力ファイルのパス
        """
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                input_path,
                "-filter:a",
                "loudnorm",
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

        return output_path

    def get_audio_duration(self, audio_path: str) -> float:
        """
        音声ファイルの長さを取得

        Args:
            audio_path: 音声ファイルのパス

        Returns:
            長さ（秒）
        """
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"FFprobe エラー: {result.stderr}")

        return float(result.stdout.strip())


if __name__ == "__main__":
    print("AudioMixer モジュールのテスト")

    try:
        mixer = AudioMixer()
        print("✅ AudioMixer の初期化に成功しました")
        print(f"   Assets ディレクトリ: {mixer.assets_dir}")
        print(f"   イントロファイル: {mixer.intro_path}")
        print(f"   イントロ存在: {mixer.intro_path.exists()}")
    except Exception as e:
        print(f"⚠️ AudioMixer の初期化に失敗: {e}")
