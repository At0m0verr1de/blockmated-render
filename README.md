# Blockmated render kit

Renders [@blockmated](https://instagram.com/blockmated) reels (Blender 3.6 EEVEE + ffmpeg) on a second
Mac and uploads the finished videos as GitHub Releases. Characters are built procedurally and the
music is synthesized, so there are no third-party assets here. No credentials are stored in this repo.

## One-time setup (office Mac)

```bash
brew install ffmpeg gh
gh auth login                                   # GitHub account that owns this repo
git clone https://github.com/At0m0verr1de/blockmated-render.git
```
Then install **Blender 3.6 LTS** (newer versions changed EEVEE and won't match):
```bash
cd blockmated-render && ./install_blender.sh   # downloads 3.6.23 from Blender's mirrors, verifies the checksum
```
If no mirror is reachable, copy `/Applications/Blender.app` (3.6) from the main Mac by AirDrop or USB.
Set `BLENDER=/path/to/Blender` if it lives somewhere other than /Applications.

## Render

```bash
cd blockmated-render
./render.sh            # newest job
./render.sh <id>       # a specific job
./render.sh --list     # jobs and whether they're rendered
```
It pulls new jobs, renders every shot, adds captions, music and narration, and uploads
`<id>.mp4` plus Instagram/TikTok/YouTube exports and the cover to a Release named `<id>-render-<date>`.
Stopping and re-running continues from the last finished shot.

## How jobs arrive

On the main Mac, `blockmated/tools/remote_render.sh send content/<id>.json` narrates the story,
copies the current render code into this repo, adds `jobs/<id>/` (timing.json + narration.wav) and
pushes. `remote_render.sh fetch <id>` downloads the finished render back into blockmated.

Code in `blender/`, `brand/` and `pipeline/` is synced from the main project; edit it there, not here.
