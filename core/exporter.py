import os
from datetime import datetime
from moviepy.editor import VideoClip, concatenate_videoclips, CompositeVideoClip
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class Exporter:

    def compose_with_transitions(self,
                                  clips: list,
                                  transition_engine,
                                  transition: str = "auto") -> VideoClip:
        """Join all clips with transitions between them."""
        if len(clips) == 0:
            raise ValueError("クリップが0件です")
        if len(clips) == 1:
            return clips[0]

        result = clips[0]
        for next_clip in clips[1:]:
            result = transition_engine.apply(result, next_clip, transition)

        return result

    def export(self, clip: VideoClip,
               filename: str = None,
               progress_callback=None) -> str:
        """Export the final clip to MP4."""
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)

        if not filename:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"reel_{ts}.mp4"

        output_path = os.path.join(config.OUTPUT_DIR, filename)

        def logger_callback(progress_dict):
            if progress_callback and 't' in progress_dict:
                try:
                    pct = progress_dict['t'] / clip.duration
                    progress_callback(min(pct, 1.0))
                except Exception:
                    pass

        clip.write_videofile(
            output_path,
            fps=config.FPS,
            codec="libx264",
            audio_codec="aac",
            bitrate=config.VIDEO_BITRATE,
            audio_bitrate=config.AUDIO_BITRATE,
            preset="medium",
            logger=None,
        )

        return output_path
