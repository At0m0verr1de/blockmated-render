"""Package a finished reel for every platform.

Usage: python3 pipeline/export.py out/<id>/timing.json
Writes out/<id>/export/: instagram.mp4, tiktok.mp4, cover.jpg, captions.txt
Checks that burned-in captions stay out of TikTok/Reels UI zones.
"""
import json
import re
import shutil
import sys
from pathlib import Path

H, W = 1920, 1080
BOTTOM_UI = 0.24 * H   # TikTok/Reels caption + buttons area at the bottom
TOP_UI = 0.07 * H      # "Following | For You" tabs at the top

timing = Path(sys.argv[1])
spec = json.loads(timing.read_text())
d = timing.parent
video = d / f"{spec['id']}.mp4"
if not video.exists():
    sys.exit(f"no video at {video}; run pipeline/assemble.py first")

# safe-zone check against the ASS styles we burned in
ass = (d / "captions.ass").read_text()
for name, align, margin_v in re.findall(r"^Style: (\w+),.*,(\d+),\d+,\d+,(\d+),\d+$", ass, re.M):
    mv = int(margin_v)
    if align in ("1", "2", "3") and mv < BOTTOM_UI:
        sys.exit(f"style {name}: bottom margin {mv}px is inside the bottom UI zone ({BOTTOM_UI:.0f}px)")
    if align in ("7", "8", "9") and mv < TOP_UI:
        sys.exit(f"style {name}: top margin {mv}px is inside the top UI zone ({TOP_UI:.0f}px)")

out = d / "export"
out.mkdir(exist_ok=True)
shutil.copy2(video, out / "instagram.mp4")
shutil.copy2(video, out / "tiktok.mp4")  # same clean file; no watermark from either app
shutil.copy2(video, out / "youtube.mp4")  # vertical and under 3 min, so YouTube treats it as a Short
shutil.copy2(d / "cover.jpg", out / "cover.jpg")

cover_at = spec["shots"][1]["start"] + 0.8
tiktok = spec.get("tiktok_caption", spec["caption"])
yt = spec.get("youtube", {})
(out / "captions.txt").write_text(f"""{spec['title']}  ({spec['duration']:.0f}s)

INSTAGRAM
{spec['caption']}

TIKTOK
{tiktok}

YOUTUBE SHORTS
Title: {yt.get('title', spec['title'])}
Description:
{yt.get('description', spec['caption'])}
Tags: {', '.join(yt.get('tags', []))}

POSTING CHECKLIST
- Instagram: posted by pipeline/publish.py after approval (AI label: set in the app's advanced settings if not applied)
- TikTok: upload tiktok.mp4, paste the TikTok caption, set the cover to {cover_at:.1f}s,
  turn ON "AI-generated content" (More options), leave "Allow Duet/Stitch" on
- YouTube: upload youtube.mp4 in the app or Studio, paste title/description/tags, pick the
  thumbnail frame at {cover_at:.1f}s, answer "Made for kids" for the channel (your decision),
  and tick "Altered or synthetic content" only if it applies (it covers realistic-looking AI content)
""")
print(f"exported to {out}")
