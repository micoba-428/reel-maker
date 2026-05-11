"""
30-day batch reel producer.

Template pattern:
  Normal day  : pool1 → pool2 → pool3 → pool1  (4 clips)
  Every 5th   : pool1 → pool2 → pool3 → pool4 or pool5 (alternating)

Within each pool, files whose name starts with "0" are sorted first (priority).
"""

import os
import zipfile
from typing import List, Optional, Callable, Dict, Any

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from core.media_processor import MediaProcessor
# Ensure pool dirs exist
for _n in range(1, 6):
    os.makedirs(os.path.join(config.POOL_BASE, f"pool_{_n}"), exist_ok=True)
from core.text_overlay import TextOverlay
from core.transition_engine import TransitionEngine
from core.ending_generator import EndingGenerator
from core.exporter import Exporter


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".mp4", ".mov"}

# Default clip durations per position (seconds)
DEFAULT_DURATIONS = [12.0, 15.0, 12.0, 12.0]  # positions 1-4
DEFAULT_ENDING_DURATION = 4.0


def load_pool(folder: str) -> List[str]:
    """
    Return sorted media paths from folder.
    Files starting with '0' come first (priority), then alphabetical.
    """
    if not os.path.isdir(folder):
        return []
    files = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if os.path.splitext(f)[1].lower() in IMAGE_EXTS
    ]
    # 0-prefix files first, then the rest — both groups sorted alphabetically
    priority = sorted(f for f in files if os.path.basename(f).startswith("0"))
    normal   = sorted(f for f in files if not os.path.basename(f).startswith("0"))
    return priority + normal


def _pick(pool: List[str], index: int) -> Optional[str]:
    """Cycle through pool by index. Returns None if pool is empty."""
    if not pool:
        return None
    return pool[index % len(pool)]


class BatchProducer:
    """Generate N reels from 5 photo pools using a fixed template."""

    def __init__(self):
        self._processor = MediaProcessor()
        self._text = TextOverlay()
        self._transitions = TransitionEngine()
        self._ending_gen = EndingGenerator()
        self._exporter = Exporter()

    # ── Public API ────────────────────────────────────────────────

    def make_plan(
        self,
        pools: Dict[int, List[str]],
        num_days: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Build day-by-day clip plan.

        pools: {1: [...paths], 2: [...paths], 3: [...paths],
                4: [...paths], 5: [...paths]}

        Each day entry: {"day": int, "clips": [path, path, path, path]}
        """
        for key in (1, 2, 3):
            if not pools.get(key):
                raise ValueError(f"プール {key} に写真がありません")

        plan = []
        special_toggle = 0  # alternates between pool4 and pool5 on special days

        for day in range(1, num_days + 1):
            is_special = (day % 5 == 0)

            # Main three positions always come from pools 1-3
            c1 = _pick(pools[1], day - 1)
            c2 = _pick(pools[2], day - 1)
            c3 = _pick(pools[3], day - 1)

            if is_special:
                # Use pool4 or pool5, alternating; fall back to pool1 if empty
                if special_toggle % 2 == 0:
                    c4 = _pick(pools.get(4, []), special_toggle // 2) or _pick(pools[1], day)
                else:
                    c4 = _pick(pools.get(5, []), special_toggle // 2) or _pick(pools[1], day)
                special_toggle += 1
            else:
                # Repeat pool1 at position 4, offset by 1 to avoid identical frame
                c4 = _pick(pools[1], day)  # day (not day-1) gives the next photo

            plan.append({"day": day, "clips": [c1, c2, c3, c4]})

        return plan

    def generate_reel(
        self,
        day_plan: Dict[str, Any],
        *,
        durations: Optional[List[float]] = None,
        ending_duration: float = DEFAULT_ENDING_DURATION,
        title_template: str = "Day {day}",
        username: str = "@your_account",
        cta_text: str = "フォローはこちら 👆",
        transition: str = "auto",
        output_dir: Optional[str] = None,
        filename: Optional[str] = None,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> str:
        """Render one reel and return its output path."""
        durs = durations or DEFAULT_DURATIONS
        out_dir = output_dir or config.OUTPUT_DIR
        os.makedirs(out_dir, exist_ok=True)

        day = day_plan["day"]
        clip_paths = day_plan["clips"]

        # ── Load media clips ──────────────────────────────────────
        clips = []
        for i, path in enumerate(clip_paths):
            dur = durs[i] if i < len(durs) else DEFAULT_DURATIONS[-1]
            clips.append(self._processor.load(path, dur))

        # ── Title on first clip ───────────────────────────────────
        title = title_template.replace("{day}", str(day))
        clips[0] = self._text.add_title(clips[0], title)

        # ── Compose with transitions ──────────────────────────────
        composed = self._exporter.compose_with_transitions(
            clips, self._transitions, transition
        )

        # ── Ending ────────────────────────────────────────────────
        ending = self._ending_gen.create(
            username=username,
            cta_text=cta_text,
            duration=ending_duration,
        )
        composed = self._exporter.compose_with_transitions(
            [composed, ending], self._transitions, "fade"
        )

        # ── Export ────────────────────────────────────────────────
        fname = filename or f"day_{day:02d}.mp4"
        self._exporter.export(
            composed,
            filename=fname,
            output_dir=out_dir,
            progress_callback=progress_callback,
        )
        return os.path.join(out_dir, fname)

    def generate_batch(
        self,
        plan: List[Dict[str, Any]],
        *,
        durations: Optional[List[float]] = None,
        ending_duration: float = DEFAULT_ENDING_DURATION,
        title_template: str = "Day {day}",
        username: str = "@your_account",
        cta_text: str = "フォローはこちら 👆",
        transition: str = "auto",
        output_dir: Optional[str] = None,
        per_reel_callback: Optional[Callable[[int, int, float], None]] = None,
    ) -> List[str]:
        """Render every reel in plan. Returns list of output paths."""
        out_dir = output_dir or config.OUTPUT_DIR
        total = len(plan)
        paths = []

        for day_plan in plan:
            day = day_plan["day"]

            def _cb(p, _day=day):
                if per_reel_callback:
                    per_reel_callback(_day, total, p)

            path = self.generate_reel(
                day_plan,
                durations=durations,
                ending_duration=ending_duration,
                title_template=title_template,
                username=username,
                cta_text=cta_text,
                transition=transition,
                output_dir=out_dir,
                progress_callback=_cb,
            )
            paths.append(path)

        return paths


def zip_outputs(paths: List[str], zip_path: str) -> str:
    """Pack all mp4 files into a ZIP and return its path."""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in paths:
            zf.write(p, os.path.basename(p))
    return zip_path
