from __future__ import annotations
import numpy as np
from PIL import Image, ImageFilter
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
# moviepy は起動時セグフォルト回避のため関数内でlazy import


class TransitionEngine:
    """Apply transitions between two VideoClip objects."""

    def apply(self, clip_a, clip_b,
              transition: str = "crossdissolve"):
        if transition == "auto":
            transition = self._auto_select(clip_a, clip_b)
        d = config.TRANSITION_DURATION
        if transition == "crossdissolve":
            return self._crossdissolve(clip_a, clip_b, d)
        elif transition == "fade":
            return self._fade(clip_a, clip_b, d)
        elif transition == "wipe_left":
            return self._wipe(clip_a, clip_b, d, direction="left")
        elif transition == "wipe_up":
            return self._wipe(clip_a, clip_b, d, direction="up")
        elif transition == "zoom_blur":
            return self._zoom_blur(clip_a, clip_b, d)
        elif transition == "glitch":
            return self._glitch(clip_a, clip_b, d)
        else:
            return self._crossdissolve(clip_a, clip_b, d)

    def _auto_select(self, clip_a, clip_b) -> str:
        """Pick transition based on clip energy (brightness variance)."""
        try:
            frame_a = clip_a.get_frame(min(0.5, clip_a.duration - 0.1))
            frame_b = clip_b.get_frame(0.0)
            energy_a = float(np.std(frame_a))
            energy_b = float(np.std(frame_b))
            avg_energy = (energy_a + energy_b) / 2

            if avg_energy > 70:
                return "zoom_blur"
            elif avg_energy > 45:
                return "wipe_left"
            else:
                return "crossdissolve"
        except Exception:
            return "crossdissolve"

    # ── Cross Dissolve ─────────────────────────────────────────────
    def _crossdissolve(self, clip_a, clip_b, d):
        from moviepy.editor import CompositeVideoClip
        clip_a_out = clip_a.crossfadeout(d)
        clip_b_in = clip_b.crossfadein(d).set_start(clip_a.duration - d)
        result = CompositeVideoClip([clip_a_out, clip_b_in])
        result.duration = clip_a.duration + clip_b.duration - d
        return result

    # ── Fade (black) ───────────────────────────────────────────────
    def _fade(self, clip_a, clip_b, d):
        from moviepy.editor import CompositeVideoClip
        clip_a_out = clip_a.fadeout(d / 2)
        clip_b_in = clip_b.fadein(d / 2).set_start(clip_a.duration - d / 2)
        result = CompositeVideoClip([clip_a_out, clip_b_in])
        result.duration = clip_a.duration + clip_b.duration - d / 2
        return result

    # ── Wipe ───────────────────────────────────────────────────────
    def _wipe(self, clip_a, clip_b, d, direction="left"):
        w, h = config.TARGET_WIDTH, config.TARGET_HEIGHT
        total_dur = clip_a.duration + clip_b.duration - d
        start_b = clip_a.duration - d

        def make_frame(t):
            if t < start_b:
                return clip_a.get_frame(t)
            if t >= clip_a.duration:
                return clip_b.get_frame(t - start_b)

            local_t = t - start_b
            progress = local_t / d
            fa = clip_a.get_frame(t)
            fb = clip_b.get_frame(local_t)

            if direction == "left":
                split = int(w * progress)
                frame = np.copy(fa)
                frame[:, :split] = fb[:, :split]
            else:  # up
                split = int(h * progress)
                frame = np.copy(fa)
                frame[:split, :] = fb[:split, :]
            return frame

        from moviepy.editor import VideoClip
        result = VideoClip(make_frame, duration=total_dur)
        return result.set_fps(config.FPS)

    # ── Zoom Blur ──────────────────────────────────────────────────
    def _zoom_blur(self, clip_a, clip_b, d):
        w, h = config.TARGET_WIDTH, config.TARGET_HEIGHT
        total_dur = clip_a.duration + clip_b.duration - d
        start_b = clip_a.duration - d

        def make_frame(t):
            if t < start_b:
                return clip_a.get_frame(t)
            if t >= clip_a.duration:
                return clip_b.get_frame(t - start_b)

            local_t = t - start_b
            progress = local_t / d  # 0→1

            fa = clip_a.get_frame(t)
            fb = clip_b.get_frame(local_t)

            # Zoom out clip_a with blur
            zoom_scale = 1 + progress * 0.15
            pil_a = Image.fromarray(fa.astype(np.uint8))
            new_w = int(w * zoom_scale)
            new_h = int(h * zoom_scale)
            pil_a = pil_a.resize((new_w, new_h), Image.LANCZOS)
            x = (new_w - w) // 2
            y = (new_h - h) // 2
            pil_a = pil_a.crop((x, y, x + w, y + h))
            blur_radius = progress * 6
            if blur_radius > 0.5:
                pil_a = pil_a.filter(ImageFilter.GaussianBlur(blur_radius))

            # Blend
            alpha = progress
            fa_arr = np.array(pil_a, dtype=np.float32)
            fb_arr = fb.astype(np.float32)
            blended = ((1 - alpha) * fa_arr + alpha * fb_arr).astype(np.uint8)
            return blended

        from moviepy.editor import VideoClip
        result = VideoClip(make_frame, duration=total_dur)
        return result.set_fps(config.FPS)

    # ── Glitch ─────────────────────────────────────────────────────
    def _glitch(self, clip_a, clip_b, d):
        w, h = config.TARGET_WIDTH, config.TARGET_HEIGHT
        total_dur = clip_a.duration + clip_b.duration - d
        start_b = clip_a.duration - d
        rng = np.random.default_rng(42)

        def make_frame(t):
            if t < start_b:
                return clip_a.get_frame(t)
            if t >= clip_a.duration:
                return clip_b.get_frame(t - start_b)

            local_t = t - start_b
            progress = local_t / d
            fa = clip_a.get_frame(t).astype(np.uint8)
            fb = clip_b.get_frame(local_t).astype(np.uint8)

            frame = fa.copy()
            # Random horizontal slices from clip_b
            n_slices = int(6 + progress * 10)
            for _ in range(n_slices):
                row = rng.integers(0, h - 20)
                height = rng.integers(5, 30)
                if rng.random() < progress:
                    frame[row:row + height, :] = fb[row:row + height, :]

            # RGB channel shift
            shift = int(progress * 12)
            if shift > 0:
                result = frame.copy()
                result[:, shift:, 0] = frame[:, :-shift, 0]  # R shift right
                result[:, :-shift, 2] = frame[:, shift:, 2]  # B shift left
                frame = result

            # Blend at the end
            if progress > 0.7:
                alpha = (progress - 0.7) / 0.3
                frame = ((1 - alpha) * frame + alpha * fb).astype(np.uint8)

            return frame

        from moviepy.editor import VideoClip
        result = VideoClip(make_frame, duration=total_dur)
        return result.set_fps(config.FPS)
