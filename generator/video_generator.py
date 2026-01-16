#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
動画生成モジュール
FFmpeg を使用して静止画と音声から動画を生成します。
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None
    ImageDraw = None
    ImageFont = None


class VideoGenerator:
    """静止画と音声から動画を生成するクラス"""

    # 動画設定
    VIDEO_WIDTH = 1920
    VIDEO_HEIGHT = 1080
    FPS = 30

    # イントロの長さ（秒）
    INTRO_DURATION = 35.0

    # 背景色（グラデーション用）
    BG_COLOR_START = (25, 25, 112)  # Midnight Blue
    BG_COLOR_END = (72, 61, 139)  # Dark Slate Blue

    def __init__(self, assets_dir: Optional[str] = None):
        """
        VideoGenerator を初期化

        Args:
            assets_dir: アセットファイルが格納されているディレクトリ
        """
        if assets_dir is None:
            self.assets_dir = Path(__file__).parent / "assets"
        else:
            self.assets_dir = Path(assets_dir)

        # 背景画像のパス
        self.background_image = self.assets_dir / "background.jpg"
        self.intro_bg_image = self.assets_dir / "images" / "hook.jpg"
        self.main_bg_image = self.assets_dir / "images" / "news_major.png"

        # FFmpeg のパスを確認
        self._check_ffmpeg()

        # PIL が利用可能か確認
        self.pil_available = Image is not None

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
            raise RuntimeError("FFmpeg がインストールされていません")

    def generate_video(
        self,
        audio_path: str,
        output_path: str,
        title: str = "NewsCast",
        topics: Optional[List[str]] = None,
        script: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        音声から動画を生成

        Args:
            audio_path: 音声ファイルのパス
            output_path: 出力動画ファイルのパス
            title: 動画タイトル
            topics: ニューストピックのリスト（サムネイルに表示）
            script: スクリプトデータ（字幕生成用）

        Returns:
            出力動画ファイルのパス
        """
        # 音声の長さを取得
        duration = self._get_audio_duration(audio_path)

        # イントロ用・メイン用の両方の背景があれば切り替え動画を生成
        if self.intro_bg_image.exists() and self.main_bg_image.exists():
            return self._generate_video_with_background_switch(
                audio_path=audio_path,
                output_path=output_path,
                duration=duration,
            )

        # 従来の単一背景での動画生成
        background_path = self._get_or_create_background(title, topics)

        # 動画を生成
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                background_path,
                "-i",
                audio_path,
                "-c:v",
                "libx264",
                "-tune",
                "stillimage",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-pix_fmt",
                "yuv420p",
                "-shortest",
                "-t",
                str(duration),
                output_path,
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg エラー: {result.stderr}")

        # 一時ファイルを削除
        if not self.background_image.exists() and os.path.exists(background_path):
            os.unlink(background_path)

        return output_path

    def _generate_video_with_background_switch(
        self,
        audio_path: str,
        output_path: str,
        duration: float,
    ) -> str:
        """
        イントロとメインで背景を切り替える動画を生成

        Args:
            audio_path: 音声ファイルのパス
            output_path: 出力動画ファイルのパス
            duration: 動画の長さ（秒）

        Returns:
            出力動画ファイルのパス
        """
        intro_duration = min(self.INTRO_DURATION, duration)

        # FFmpeg フィルタ複合処理:
        # 1. イントロ背景をリサイズ
        # 2. メイン背景をリサイズ
        # 3. イントロを最初の35秒間表示、その後メインに切り替え
        filter_complex = (
            f"[0:v]scale={self.VIDEO_WIDTH}:{self.VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={self.VIDEO_WIDTH}:{self.VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1[intro];"
            f"[1:v]scale={self.VIDEO_WIDTH}:{self.VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={self.VIDEO_WIDTH}:{self.VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1[main];"
            f"[main][intro]overlay=0:0:enable='lt(t,{intro_duration})'[v]"
        )

        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loop",
                "1",
                "-i",
                str(self.intro_bg_image),
                "-loop",
                "1",
                "-i",
                str(self.main_bg_image),
                "-i",
                audio_path,
                "-filter_complex",
                filter_complex,
                "-map",
                "[v]",
                "-map",
                "2:a",
                "-c:v",
                "libx264",
                "-tune",
                "stillimage",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-pix_fmt",
                "yuv420p",
                "-t",
                str(duration),
                output_path,
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg エラー: {result.stderr}")

        print(f"   背景切り替え: {intro_duration}秒でイントロ→メインに切り替え")
        return output_path

    def _get_or_create_background(
        self,
        title: str,
        topics: Optional[List[str]] = None,
    ) -> str:
        """背景画像を取得または生成"""
        # 既存の背景画像があればそれを使用
        if self.background_image.exists():
            return str(self.background_image)

        # PIL が利用可能な場合は動的に生成
        if self.pil_available:
            return self._create_background_image(title, topics)

        # それ以外は黒背景を使用（FFmpeg で生成）
        return self._create_solid_background()

    def _create_background_image(
        self,
        title: str,
        topics: Optional[List[str]] = None,
    ) -> str:
        """PIL を使用して背景画像を生成"""
        # グラデーション背景を作成
        img = Image.new("RGB", (self.VIDEO_WIDTH, self.VIDEO_HEIGHT))
        draw = ImageDraw.Draw(img)

        for y in range(self.VIDEO_HEIGHT):
            ratio = y / self.VIDEO_HEIGHT
            r = int(self.BG_COLOR_START[0] * (1 - ratio) + self.BG_COLOR_END[0] * ratio)
            g = int(self.BG_COLOR_START[1] * (1 - ratio) + self.BG_COLOR_END[1] * ratio)
            b = int(self.BG_COLOR_START[2] * (1 - ratio) + self.BG_COLOR_END[2] * ratio)
            draw.line([(0, y), (self.VIDEO_WIDTH, y)], fill=(r, g, b))

        # フォントを設定（システムフォントを使用）
        try:
            title_font = ImageFont.truetype("arial.ttf", 72)
            topic_font = ImageFont.truetype("arial.ttf", 36)
        except (OSError, IOError):
            title_font = ImageFont.load_default()
            topic_font = ImageFont.load_default()

        # タイトルを描画
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (self.VIDEO_WIDTH - title_width) // 2
        title_y = 200

        # タイトルの影
        draw.text(
            (title_x + 3, title_y + 3), title, fill=(0, 0, 0, 128), font=title_font
        )
        # タイトル本体
        draw.text((title_x, title_y), title, fill=(255, 255, 255), font=title_font)

        # トピックを描画
        if topics:
            y_offset = 400
            for i, topic in enumerate(topics[:3]):
                topic_text = f"📰 {topic}"
                topic_bbox = draw.textbbox((0, 0), topic_text, font=topic_font)
                topic_width = topic_bbox[2] - topic_bbox[0]
                topic_x = (self.VIDEO_WIDTH - topic_width) // 2

                draw.text(
                    (topic_x, y_offset),
                    topic_text,
                    fill=(200, 200, 255),
                    font=topic_font,
                )
                y_offset += 60

        # 日付を描画
        date_text = datetime.now().strftime("%Y年%m月%d日")
        date_bbox = draw.textbbox((0, 0), date_text, font=topic_font)
        date_width = date_bbox[2] - date_bbox[0]
        date_x = (self.VIDEO_WIDTH - date_width) // 2
        draw.text(
            (date_x, self.VIDEO_HEIGHT - 100),
            date_text,
            fill=(150, 150, 200),
            font=topic_font,
        )

        # 一時ファイルに保存
        temp_path = tempfile.mktemp(suffix=".png")
        img.save(temp_path, "PNG")

        return temp_path

    def _create_solid_background(self) -> str:
        """FFmpeg を使用して単色背景を生成"""
        temp_path = tempfile.mktemp(suffix=".png")

        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c=0x191970:s={self.VIDEO_WIDTH}x{self.VIDEO_HEIGHT}:d=1",
                "-vframes",
                "1",
                temp_path,
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg エラー: {result.stderr}")

        return temp_path

    def _get_audio_duration(self, audio_path: str) -> float:
        """音声ファイルの長さを取得"""
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

    def generate_thumbnail(
        self,
        output_path: str,
        title: str,
        topics: Optional[List[str]] = None,
    ) -> str:
        """
        YouTube 用のサムネイル画像を生成

        Args:
            output_path: 出力ファイルのパス
            title: 動画タイトル
            topics: ニューストピックのリスト

        Returns:
            出力ファイルのパス
        """
        if not self.pil_available:
            raise RuntimeError("PIL がインストールされていません")

        # サムネイルサイズ（YouTube推奨: 1280x720）
        width, height = 1280, 720

        # グラデーション背景を作成
        img = Image.new("RGB", (width, height))
        draw = ImageDraw.Draw(img)

        for y in range(height):
            ratio = y / height
            r = int(self.BG_COLOR_START[0] * (1 - ratio) + self.BG_COLOR_END[0] * ratio)
            g = int(self.BG_COLOR_START[1] * (1 - ratio) + self.BG_COLOR_END[1] * ratio)
            b = int(self.BG_COLOR_START[2] * (1 - ratio) + self.BG_COLOR_END[2] * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # フォントを設定
        try:
            title_font = ImageFont.truetype("arial.ttf", 64)
            topic_font = ImageFont.truetype("arial.ttf", 32)
        except (OSError, IOError):
            title_font = ImageFont.load_default()
            topic_font = ImageFont.load_default()

        # タイトルを描画
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_x = (width - title_width) // 2
        title_y = 100

        draw.text((title_x + 2, title_y + 2), title, fill=(0, 0, 0), font=title_font)
        draw.text((title_x, title_y), title, fill=(255, 255, 255), font=title_font)

        # トピックを描画
        if topics:
            y_offset = 250
            for topic in topics[:3]:
                topic_text = f"• {topic[:40]}..." if len(topic) > 40 else f"• {topic}"
                topic_bbox = draw.textbbox((0, 0), topic_text, font=topic_font)
                topic_width = topic_bbox[2] - topic_bbox[0]
                topic_x = (width - topic_width) // 2

                draw.text(
                    (topic_x, y_offset),
                    topic_text,
                    fill=(220, 220, 255),
                    font=topic_font,
                )
                y_offset += 50

        # 日付を描画
        date_text = datetime.now().strftime("%Y.%m.%d")
        draw.text(
            (width - 200, height - 60), date_text, fill=(150, 150, 200), font=topic_font
        )

        img.save(output_path, "JPEG", quality=95)

        return output_path


if __name__ == "__main__":
    print("VideoGenerator モジュールのテスト")

    try:
        generator = VideoGenerator()
        print("✅ VideoGenerator の初期化に成功しました")
        print(f"   PIL 利用可能: {generator.pil_available}")
        print(f"   背景画像: {generator.background_image}")
    except Exception as e:
        print(f"⚠️ VideoGenerator の初期化に失敗: {e}")
