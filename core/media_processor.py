from __future__ import annotations
import os
import numpy as np
from PIL import Image
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
# moviepy は起動時セグフォルト回避のため関数内でlazy import


class MediaProcessor:
    """Load images/videos and normalize to Instagram Reel format (1080x1920, 30fps)."""

    def load(self, path: str, duration: float = None):
        ext = os.path.splitext(path)[1].lower()
        if ext in ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'):
            return self._image_to_video(path, duration or config.DEFAULT_IMAGE_DURATION)
        else:
            return self._normalize_video(path, duration)

    def _image_to_video(self, path: str, duration: float):
        img = Image.open(path).convert('RGB')
        img = self._cover_crop(img)
        img_large = img.resize(
            (int(img.width * 1.12), int(img.height * 1.12)), Image.LANCZOS
        )
        base_arr = np.array(img_large)
        bw, bh = img_large.size

        def make_frame(t):
            progress = t / duration
            zoom = 1.0 + 0.10 * progress  # zoom in 10% over clip
            vw = int(config.TARGET_WIDTH / zoom)
            vh = int(config.TARGET_HEIGHT / zoom)
            # Keep it inside the oversized image
            vw = min(vw, bw)
            vh = min(vh, bh)
            x = (bw - vw) // 2
            y = (bh - vh) // 2
            cropped = base_arr[y:y + vh, x:x + vw]
            frame = np.array(Image.fromarray(cropped).resize(
                (config.TARGET_WIDTH, config.TARGET_HEIGHT), Image.LANCZOS
            ))
            return frame

        from moviepy.editor import VideoClip
        return VideoClip(make_frame, duration=duration).set_fps(config.FPS)

    def _normalize_video(self, path: str, duration: float = None):
        from moviepy.editor import VideoFileClip
        clip = VideoFileClip(path)
        if duration:
            clip = clip.subclip(0, min(duration, clip.duration))

        # Cover crop to 9:16
        clip_ratio = clip.w / clip.h
        target_ratio = config.TARGET_WIDTH / config.TARGET_HEIGHT

        if clip_ratio > target_ratio:
            new_h = config.TARGET_HEIGHT
            new_w = int(clip.w * new_h / clip.h)
            clip = clip.resize((new_w, new_h))
            x = (new_w - config.TARGET_WIDTH) // 2
            clip = clip.crop(x1=x, x2=x + config.TARGET_WIDTH)
        else:
            new_w = config.TARGET_WIDTH
            new_h = int(clip.h * new_w / clip.w)
            clip = clip.resize((new_w, new_h))
            y = (new_h - config.TARGET_HEIGHT) // 2
            clip = clip.crop(y1=y, y2=y + config.TARGET_HEIGHT)

        return clip.set_fps(config.FPS)

    def _cover_crop(self, img: Image.Image) -> Image.Image:
        """Resize+center-crop image to exactly TARGET_WIDTH x TARGET_HEIGHT."""
        img_ratio = img.width / img.height
        target_ratio = config.TARGET_WIDTH / config.TARGET_HEIGHT

        if img_ratio > target_ratio:
            new_h = config.TARGET_HEIGHT
            new_w = int(img.width * new_h / img.height)
        else:
            new_w = config.TARGET_WIDTH
            new_h = int(img.height * new_w / img.width)

        img = img.resize((new_w, new_h), Image.LANCZOS)
        x = (new_w - config.TARGET_WIDTH) // 2
        y = (new_h - config.TARGET_HEIGHT) // 2
        return img.crop((x, y, x + config.TARGET_WIDTH, y + config.TARGET_HEIGHT))
