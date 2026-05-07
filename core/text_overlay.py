import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoClip
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in config.FONT_PATHS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _text_with_shadow(draw: ImageDraw.ImageDraw, xy, text: str,
                      font, fill, shadow_offset=3):
    x, y = xy
    draw.text((x + shadow_offset, y + shadow_offset), text,
              font=font, fill=(0, 0, 0, 180))
    draw.text((x, y), text, font=font, fill=fill)


def _wrap_text(text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines = []
    current = ""
    dummy_img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    for word in words:
        test = (current + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


class TextOverlay:

    def add_title(self, clip: VideoClip, title: str,
                  style: str = "modern") -> VideoClip:
        """Overlay animated title on the first 2.5 seconds of the clip."""
        if not title.strip():
            return clip

        font = _load_font(config.TITLE_FONT_SIZE)
        w, h = config.TARGET_WIDTH, config.TARGET_HEIGHT
        fade_in_end = 0.6
        hold_end = 2.5
        anim_dur = min(hold_end, clip.duration)

        def make_frame(t):
            frame = clip.get_frame(t).copy()

            if t > anim_dur:
                return frame

            # Opacity
            if t < fade_in_end:
                alpha = t / fade_in_end
            elif t < hold_end - 0.4:
                alpha = 1.0
            else:
                alpha = max(0.0, (anim_dur - t) / 0.4)

            if alpha <= 0:
                return frame

            # Build text overlay
            overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)

            lines = _wrap_text(title, font, w - 80)

            # Measure total text block height
            line_h = config.TITLE_FONT_SIZE + 12
            total_h = len(lines) * line_h

            # Position: upper 1/3 of frame
            y_start = h // 5 - total_h // 2

            # Semi-transparent background bar
            pad = 20
            bg_x0 = 30
            bg_x1 = w - 30
            bg_y0 = y_start - pad
            bg_y1 = y_start + total_h + pad
            draw.rectangle([bg_x0, bg_y0, bg_x1, bg_y1],
                           fill=(0, 0, 0, int(150 * alpha)))

            # Draw lines
            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                text_w = bbox[2] - bbox[0]
                x = (w - text_w) // 2
                y = y_start + i * line_h

                # Slide-up animation
                if t < fade_in_end:
                    slide = int((1 - alpha) * 30)
                    y += slide

                _text_with_shadow(draw, (x, y), line, font,
                                  fill=(255, 255, 255, int(255 * alpha)))

            # Composite
            base = Image.fromarray(frame).convert("RGBA")
            base = Image.alpha_composite(base, overlay)
            return np.array(base.convert("RGB"))

        result = VideoClip(make_frame, duration=clip.duration)
        result = result.set_fps(config.FPS)
        if hasattr(clip, 'audio') and clip.audio:
            result = result.set_audio(clip.audio)
        return result

    def add_message(self, clip: VideoClip, text: str,
                    position: str = "bottom",
                    animation: str = "fade_in") -> VideoClip:
        """Overlay a message text on the clip."""
        if not text.strip():
            return clip

        font = _load_font(config.MESSAGE_FONT_SIZE)
        w, h = config.TARGET_WIDTH, config.TARGET_HEIGHT
        fade_dur = 0.5

        def make_frame(t):
            frame = clip.get_frame(t).copy()

            # Opacity (fade in / hold / fade out)
            if t < fade_dur:
                alpha = t / fade_dur
            elif t < clip.duration - fade_dur:
                alpha = 1.0
            else:
                alpha = max(0.0, (clip.duration - t) / fade_dur)

            if alpha <= 0:
                return frame

            overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)

            lines = _wrap_text(text, font, w - 100)
            line_h = config.MESSAGE_FONT_SIZE + 14
            total_h = len(lines) * line_h

            if position == "top":
                y_start = 120
            elif position == "center":
                y_start = (h - total_h) // 2
            else:  # bottom
                y_start = h - total_h - 120

            # Animation offset
            if animation == "slide_up" and t < fade_dur:
                y_start += int((1 - alpha) * 40)

            pad = 18
            bg_x0 = 40
            bg_x1 = w - 40
            draw.rounded_rectangle(
                [bg_x0, y_start - pad, bg_x1, y_start + total_h + pad],
                radius=16,
                fill=(0, 0, 0, int(160 * alpha))
            )

            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                text_w = bbox[2] - bbox[0]
                x = (w - text_w) // 2
                y = y_start + i * line_h
                _text_with_shadow(draw, (x, y), line, font,
                                  fill=(255, 255, 255, int(255 * alpha)))

            base = Image.fromarray(frame).convert("RGBA")
            base = Image.alpha_composite(base, overlay)
            return np.array(base.convert("RGB"))

        result = VideoClip(make_frame, duration=clip.duration)
        result = result.set_fps(config.FPS)
        if hasattr(clip, 'audio') and clip.audio:
            result = result.set_audio(clip.audio)
        return result
