"""Join rendered shots, burn captions + title, mix narration with music and SFX.

Usage: python3 pipeline/assemble.py out/<id>/timing.json
Writes out/<id>/<id>.mp4 and out/<id>/cover.jpg
Music and SFX are synthesized here, so there is nothing to license.
"""
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from music import generate as generate_music  # noqa: E402

SR = 24000
FONT = "Arial Rounded MT Bold"
FONT_FILE = "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf"

timing = Path(sys.argv[1])
spec = json.loads(timing.read_text())
d = timing.parent
shots_dir = d / "shots"
dur = spec["duration"]


def run(*cmd, cwd=None):
    subprocess.run(cmd, check=True, cwd=cwd)


# ------------------------------------------------------------ captions (ASS)

def ts(t):
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def esc(s):
    return s.replace("{", "(").replace("}", ")")


STOP = set("a an the and or but so to of in on at for with my me i i'm you he she it its it's we they his her our your is was were be been are this that there then just not no as by from up out".split())


def captions():
    """craftee-style captions: 1-2 words at a time, centred, the key word in CAPS and colour, popping in."""
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{FONT},104,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,1,0,0,0,100,100,0,0,1,8,3,5,60,60,0,1
Style: Title,{FONT},104,&H00FFFFFF,&H00FFFFFF,&H00101010,&H80000000,1,0,0,0,100,100,0,0,1,8,4,8,60,60,250,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = [f"Dialogue: 1,{ts(0.15)},{ts(2.8)},Title,,0,0,0,,{{\\fad(200,300)}}{esc(spec['title'])}"]
    if spec.get("title_card") is False:   # craftee-style reels open straight on the first caption
        ev = []
    upper = spec.get("caption_style") == "upper"   # 2-4 words on two lines, upper-middle, green keyword
    per = 4 if upper else 2
    words = [w for s in spec["shots"] for w in s["words"]]
    groups, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) == per or w["text"][-1] in ".,?!:;":
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    y = 560 if upper else 840
    pop = "{\\pos(540,%d)\\fscx70\\fscy70\\t(0,90,\\fscx110\\fscy110)\\t(90,170,\\fscx100\\fscy100)}" % y
    key_tag, base_tag = ("{\\c&H4DD65C&\\fs96}", "{\\c&HFFFFFF&\\fs84}") if upper else ("{\\c&H3CC9FF&\\fs120}", "{\\c&HFFFFFF&\\fs104}")
    for gi, g in enumerate(groups):
        end = groups[gi + 1][0]["start"] if gi + 1 < len(groups) else g[-1]["end"] + 0.5
        end = min(end, g[-1]["end"] + 0.5)
        key = max(range(len(g)), key=lambda k: (g[k]["text"].strip(".,?!:;\"'").lower() not in STOP,
                                                len(g[k]["text"])))
        parts = []
        for k, w in enumerate(g):
            t = esc(w["text"])
            parts.append(key_tag + t.upper() + base_tag if k == key else t)
        if upper and len(parts) > 2:                      # two lines: first half / second half
            mid = len(parts) // 2
            text_ = " ".join(parts[:mid]) + "\\N" + " ".join(parts[mid:])
        else:
            text_ = " ".join(parts)
        lead = base_tag if upper else ""
        ev.append(f"Dialogue: 0,{ts(g[0]['start'])},{ts(end)},Cap,,0,0,0,,{pop}{lead}{text_}")
    (d / "captions.ass").write_text(head + "\n".join(ev) + "\n")


# ------------------------------------------------------------ music + sfx

def env(n, attack, decay):
    t = np.arange(n) / SR
    return np.minimum(1, t / attack) * np.exp(-t / decay)


def tone(freq, length, attack=0.005, decay=0.6, harmonics=(1, 0.3, 0.12)):
    n = int(length * SR)
    t = np.arange(n) / SR
    w = sum(a * np.sin(2 * np.pi * freq * (k + 1) * t) for k, a in enumerate(harmonics))
    return w * env(n, attack, decay)


def music(total):
    """Soft music-box loop in A minor with a low pad: curious, a little spooky."""
    out = np.zeros(int(total * SR) + SR)
    beat = 60 / 84
    a4 = 440.0
    hz = lambda semi: a4 * 2 ** (semi / 12)
    # chord roots (semitones from A4): Am, F, C, E
    prog = [(-12, [0, 3, 7, 12, 15, 12, 7, 3]), (-16, [-4, 0, 3, 8, 12, 8, 3, 0]),
            (-9, [3, 7, 10, 15, 19, 15, 10, 7]), (-17, [-5, -1, 2, 7, 11, 7, 2, -1])]
    t = 0.0
    while t < total:
        for root, arp in prog:
            pad = tone(hz(root), beat * 8, attack=0.6, decay=3.0, harmonics=(1, 0.5, 0.25))
            i = int(t * SR)
            out[i:i + len(pad)] += 0.10 * pad[: max(0, len(out) - i)]
            for k, semi in enumerate(arp):
                note = tone(hz(semi + 12), 1.2, decay=0.45, harmonics=(1, 0.18, 0.05))
                j = int((t + k * beat) * SR)
                out[j:j + len(note)] += 0.13 * note[: max(0, len(out) - j)]
            t += beat * 8
    return out[: int(total * SR)]


def sfx_clunk():
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * (140 - 200 * t) * t) * np.exp(-t / 0.07)
    click = np.random.default_rng(1).normal(0, 1, n) * np.exp(-t / 0.01)
    return 0.9 * body + 0.25 * click


def sfx_hum(length):
    n = int(length * SR)
    t = np.arange(n) / SR
    w = 0.6 * np.sin(2 * np.pi * 60 * t) + 0.3 * np.sin(2 * np.pi * 120 * t) + 0.1 * np.sin(2 * np.pi * 180 * t)
    fade = np.minimum(1, np.minimum(t / 0.3, (length - t) / 0.3))
    return w * (0.75 + 0.25 * np.sin(2 * np.pi * 5 * t)) * fade


def sfx_ding():
    return tone(1318.5, 1.2, decay=0.35, harmonics=(1, 0.4, 0.2)) + 0.6 * tone(1975.5, 1.2, decay=0.3)


def bed():
    out = 0.8 * generate_music(dur, mood=spec.get("music", "night_walk"), sr=SR, seed=len(spec["id"]))
    def put(sig, at, gain):
        i = int(at * SR)
        seg = sig[: max(0, len(out) - i)]
        out[i:i + len(seg)] += gain * seg
    for s in spec["shots"]:
        fx = s.get("machine") or {}
        length = s["end"] - s["start"]
        if "drop" in fx:
            put(sfx_clunk(), s["start"] + fx["drop"] * length, 0.8)
        if fx.get("glow_up") or fx.get("shake") or fx.get("pulse"):
            put(sfx_hum(length), s["start"], 0.12)
        if "return_on" in fx:
            put(sfx_ding(), s["start"] + fx["return_on"] * length, 0.35)
    # duck the music under the voice a little
    out = np.clip(out, -1, 1)
    with wave.open(str(d / "bed.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((out * 32767 * 0.8).astype(np.int16).tobytes())


# ------------------------------------------------------------ video

def video():
    shots = [shots_dir / f"{i:02d}.mp4" for i in range(len(spec["shots"]))]
    missing = [p.name for p in shots if not p.exists()]
    if missing:
        sys.exit(f"missing shots: {missing}")
    (d / "concat.txt").write_text("".join(f"file '{p.resolve()}'\n" for p in shots))
    out = d / f"{spec['id']}.mp4"
    # run inside the reel folder with relative names: ffmpeg filter paths can't contain spaces
    run("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", "concat.txt",
        "-i", "narration.wav", "-i", "bed.wav",
        "-filter_complex",
        "[0:v]eq=saturation=1.12:contrast=1.04,colorbalance=rs=0.04:bs=-0.04:rh=0.03:bh=-0.03,"
        "vignette=angle=PI/6,ass=captions.ass,format=yuv420p[v];"
        # voice and music are levelled separately (music ~13 dB under the voice), the music ducks
        # while the narrator talks, then the mix is normalised for Instagram (-14 LUFS)
        "[1:a]loudnorm=I=-16:TP=-2:LRA=11,asplit=2[v1][v2];[2:a]loudnorm=I=-26:TP=-8:LRA=11[m];"
        "[m][v2]sidechaincompress=threshold=0.03:ratio=3:attack=20:release=600[md];"
        "[v1][md]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]",
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "19", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k", "-t", f"{dur:.2f}", "-movflags", "+faststart", out.name, cwd=d)
    # cover: a frame from the "It takes memories" sign shot + title
    title = spec["title"].replace(":", "\\:").replace("'", "")
    run("ffmpeg", "-y", "-v", "error", "-ss", f"{spec['shots'][1]['start'] + 0.8:.2f}", "-i", str(out),
        "-frames:v", "1", "-vf",
        f"drawtext=fontfile='{FONT_FILE}':text='{title}':fontsize=110:fontcolor=white:borderw=9:"
        "bordercolor=0x101010:x=(w-text_w)/2:y=h*0.62", "-q:v", "2", str(d / "cover.jpg"))
    print(f"wrote {out} ({dur:.1f}s) and cover.jpg")


captions()
bed()
if "--audio-only" not in sys.argv:
    video()
