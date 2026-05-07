import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import VideoClip
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

from core.text_overlay import _load_font, _text_with_shadow


class EndingGenerator:
    """Create a profile-redirect CTA ending clip."""

    def create(self,
               username: str = "@your_account",
               cta_text: str = "フォローはこちら 👆",
               duration: float = None,
               bg_style: str = "gradient") -> VideoClip:

        dur = duration or config.DEFAULT_ENDING_DURATION
        w, h = config.TARGET_WIDTH, config.TARGET_HEIGHT

        # Pre-render background
        bg = self._make_background(w, h, bg_style)

        font_user = _load_font(config.ENDING_USERNAME_SIZE)
        font_cta = _load_font(config.ENDING_CTA_SIZE)
        font_small = _load_font(36)

        def make_frame(t):
            progress = t / dur
            fade_in = min(1.0, t / 0.5)
            fade_out = 1.0 if t < dur - 0.5 else (dur - t) / 0.5

            alpha = min(fade_in, fade_out)

            overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)

            center_x = w // 2
            center_y = h // 2

            # Bouncy scale animation for icon
            if t < 0.8:
                scale = 0.6 + 0.4 * min(1.0, t / 0.4)
                bounce = abs(np.sin(t * np.pi * 2.5)) * (1 - t / 0.8) * 0.08
                icon_scale = scale + bounce
            else:
                icon_scale = 1.0

            # Draw circular icon placeholder
            icon_r = int(120 * icon_scale)
            icon_x0 = center_x - icon_r
            icon_y0 = center_y - 340 - icon_r
            icon_x1 = center_x + icon_r
            icon_y1 = center_y - 340 + icon_r

            # Gradient ring
            for ring in range(8, 0, -1):
                ring_alpha = int(alpha * 255 * (ring / 8) * 0.4)
                draw.ellipse(
                    [icon_x0 - ring * 4, icon_y0 - ring * 4,
                     icon_x1 + ring * 4, icon_y1 + ring * 4],
                    fill=(255, 80, 120, ring_alpha)
                )
            draw.ellipse([icon_x0, icon_y0, icon_x1, icon_y1],
                         fill=(255, 255, 255, int(alpha * 230)))

            # Camera icon inside circle
            cam_size = int(icon_r * 0.55)
            cx, cy = center_x, center_y - 340
            draw.rounded_rectangle(
                [cx - cam_size, cy - int(cam_size * 0.7),
                 cx + cam_size, cy + int(cam_size * 0.7)],
                radius=int(cam_size * 0.25),
                outline=(255, 80, 120, int(alpha * 255)),
                width=6
            )
            lens_r = int(cam_size * 0.35)
            draw.ellipse([cx - lens_r, cy - lens_r, cx + lens_r, cy + lens_r],
                         outline=(255, 80, 120, int(alpha * 255)), width=5)

            # Slide-in animation for text
            slide = int((1 - min(1.0, t / 0.6)) * 50)

            # Username
            bbox = draw.textbbox((0, 0), username, font=font_user)
            uw = bbox[2] - bbox[0]
            uy = center_y - 160 + slide
            _text_with_shadow(draw, (center_x - uw // 2, uy), username,
                               font_user, fill=(255, 255, 255, int(alpha * 255)))

            # Divider line
            if alpha > 0.3:
                line_alpha = int(alpha * 180)
                lx0 = center_x - 200
                lx1 = center_x + 200
                ly = center_y - 50
                draw.line([(lx0, ly), (lx1, ly)],
                          fill=(255, 80, 120, line_alpha), width=3)

            # CTA text
            bbox2 = draw.textbbox((0, 0), cta_text, font=font_cta)
            cw = bbox2[2] - bbox2[0]
            cy_cta = center_y + slide
            _text_with_shadow(draw, (center_x - cw // 2, cy_cta), cta_text,
                               font_cta, fill=(255, 255, 255, int(alpha * 255)))

            # "プロフィールをチェック" sub-text
            sub = "▲ プロフィールをチェック ▲"
            bbox3 = draw.textbbox((0, 0), sub, font=font_small)
            sw = bbox3[2] - bbox3[0]
            sy = center_y + 140 + slide
            _text_with_shadow(draw, (center_x - sw // 2, sy), sub,
                               font_small,
                               fill=(255, 200, 200, int(alpha * 200)))

            # Pulsing arrow up animation
            pulse = 0.5 + 0.5 * np.sin(t * np.pi * 2)
            arrow_y = center_y + 260 - int(pulse * 20)
            arrow_alpha = int(alpha * (0.6 + 0.4 * pulse) * 255)
            arrow_font = _load_font(80)
            draw.text((center_x - 30, arrow_y), "↑",
                      font=arrow_font, fill=(255, 80, 120, arrow_alpha))

            # Composite
            base = bg.copy().convert("RGBA")
            base = Image.alpha_composite(base, overlay)
            return np.array(base.convert("RGB"))

        clip = VideoClip(make_frame, duration=dur)
        return clip.set_fps(config.FPS)

    def _make_background(self, w: int, h: int, style: str) -> Image.Image:
        bg = Image.new("RGB", (w, h), (15, 10, 25))
        draw = ImageDraw.Draw(bg)

        if style == "gradient":
            # Dark gradient with subtle purple/pink tones
            for y in range(h):
                ratio = y / h
                r = int(15 + ratio * 25)
                g = int(10 + ratio * 5)
                b = int(25 + ratio * 20)
                draw.line([(0, y), (w, y)], fill=(r, g, b))

            # Soft glow circles
            glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow)
            gd.ellipse([w // 2 - 300, h // 2 - 500,
                        w // 2 + 300, h // 2 + 100],
                       fill=(180, 30, 80, 40))
            glow = glow.filter(ImageFilter.GaussianBlur(120))
            bg = Image.alpha_composite(bg.convert("RGBA"), glow).convert("RGB")

        return bg
