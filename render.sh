#!/bin/bash
# Render a Blockmated reel on this Mac and upload it as a GitHub Release.
#
#   ./render.sh              render the newest job in jobs/
#   ./render.sh <id>         render a specific job
#   ./render.sh --list       show jobs and which ones already have a render
#
# First run checks/installs what it needs (Blender 3.6 LTS, ffmpeg, GitHub CLI, numpy).
set -euo pipefail
cd "$(dirname "$0")"

BLENDER="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
say() { printf "\033[1;35m▸ %s\033[0m\n" "$*"; }
die() { printf "\033[1;31m✗ %s\033[0m\n" "$*" >&2; exit 1; }

# ---------------------------------------------------------------- setup checks
[ -x "$BLENDER" ] || die "Blender not found at $BLENDER. Install Blender 3.6 LTS: https://www.blender.org/download/lts/3-6/ (or set BLENDER=/path/to/Blender)"
"$BLENDER" --version 2>/dev/null | head -1 | grep -q "Blender 3\.6" \
  || printf "\033[33m! %s is not Blender 3.6 LTS; output may differ from the main Mac.\033[0m\n" "$("$BLENDER" --version 2>/dev/null | head -1)"
command -v ffmpeg >/dev/null || die "ffmpeg missing: brew install ffmpeg"
command -v gh >/dev/null || die "GitHub CLI missing: brew install gh && gh auth login"
gh auth status >/dev/null 2>&1 || die "Not logged in to GitHub: run  gh auth login"
if [ ! -x .venv/bin/python ]; then
  say "First run: creating Python environment (numpy)"
  python3 -m venv .venv && .venv/bin/python -m pip install -q --upgrade pip numpy
fi

say "Pulling latest jobs and code"
git pull --ff-only -q

released() { gh release list --limit 200 --json tagName -q '.[].tagName' 2>/dev/null | grep -q "^$1-render-"; }

if [ "${1:-}" = "--list" ]; then
  for d in jobs/*/; do id=$(basename "$d"); released "$id" && s="rendered" || s="pending"; echo "$id  $s"; done
  exit 0
fi

ID="${1:-$(cat jobs/LATEST 2>/dev/null || true)}"
[ -n "$ID" ] && [ -f "jobs/$ID/timing.json" ] || die "No job '$ID'. Jobs: $(ls jobs | grep -v LATEST | tr '\n' ' ')"

OUT="out/$ID"
mkdir -p "$OUT"
cp "jobs/$ID/timing.json" "jobs/$ID/narration.wav" "$OUT/"
SHOTS=$(.venv/bin/python -c "import json;print(len(json.load(open('$OUT/timing.json'))['shots']))")
DUR=$(.venv/bin/python -c "import json;print(round(json.load(open('$OUT/timing.json'))['duration']))")
say "Rendering $ID: $SHOTS shots, ${DUR}s (finished shots are kept if you stop and re-run)"
START=$(date +%s)
"$BLENDER" -b -P blender/render_reel.py -- "$OUT/timing.json" > "$OUT/blender.log" 2>&1 &
BPID=$!
trap 'kill $BPID 2>/dev/null' INT TERM
# Blender buffers its output when piped, so show progress from the progress file it writes.
while kill -0 $BPID 2>/dev/null; do
  .venv/bin/python - "$OUT" "$START" <<'PY'
import json, sys, time
from pathlib import Path
out, start = Path(sys.argv[1]), float(sys.argv[2])
t = json.loads((out / "timing.json").read_text())["shots"]
frames = [max(12, round((s["end"] - s["start"]) * 24)) for s in t]
done = [i for i in range(len(t)) if (out / "shots" / f"{i:02d}.mp4").exists()]
cur = 0
p = out / "progress.json"
if p.exists():
    j = json.loads(p.read_text())
    if j["shot"] not in done:
        cur = j["frame"]
f_done = sum(frames[i] for i in done) + cur
pct = f_done / sum(frames)
el = time.time() - start
eta = f" · ~{int(el / pct * (1 - pct) / 60) + 1} min left" if 0.03 < pct < 1 else ""
print(f"\r  shots {len(done)}/{len(t)} · {pct:5.1%} · {int(el // 60)}m{int(el % 60):02d}s{eta}      ", end="", flush=True)
PY
  sleep 5
done
echo
wait $BPID || { tail -20 "$OUT/blender.log"; die "Blender failed (log: $OUT/blender.log)"; }
DONE=$(ls "$OUT/shots"/*.mp4 2>/dev/null | wc -l | tr -d ' ')
[ "$DONE" -eq "$SHOTS" ] || die "Only $DONE/$SHOTS shots rendered; re-run ./render.sh $ID to continue."

say "Assembling (captions, music, narration)"
.venv/bin/python pipeline/assemble.py "$OUT/timing.json"
.venv/bin/python pipeline/export.py "$OUT/timing.json"

TAG="$ID-render-$(date +%Y%m%d-%H%M)"
MINS=$(( ($(date +%s) - START) / 60 ))
say "Uploading to GitHub Release $TAG"
gh release create "$TAG" "$OUT/$ID.mp4" "$OUT"/export/* \
  --title "$ID ($(date '+%d %b %H:%M'))" \
  --notes "Rendered on $(scutil --get ComputerName 2>/dev/null || hostname) in ${MINS} min with $("$BLENDER" --version 2>/dev/null | head -1). ${SHOTS} shots, ${DUR}s." >/dev/null
printf "\033[1;32m✓ Done in %s min: %s\033[0m\n" "$MINS" "$(gh release view "$TAG" --json url -q .url)"
