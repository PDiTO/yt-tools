# yt-tools

A command-line tool to download and transcribe YouTube videos.

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- ffmpeg (for transcription)

## Installation

```bash
# Clone and enter directory
git clone https://github.com/pdito/yt-tools.git
cd yt-tools

# Sync dependencies with uv
uv sync

# Run the tool
uv run yt --help
```

## Commands

### Download

Download videos from YouTube channels or playlists with keyword filtering.

```bash
uv run yt download URL [keywords...] [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `-d, --download` | off | Download videos (default: list only) |
| `-n, --max N` | all | Maximum number of videos |
| `-o, --output DIR` | `./downloads` | Output directory |
| `-r, --resolution` | `1080` | Max resolution: `720`, `1080`, or `best` |
| `--shorts` | off | Include shorts (≤60s) |
| `--only-shorts` | off | Only download shorts |

Examples:
```bash
# List all full-length videos
uv run yt download https://www.youtube.com/@SomeChannel

# List videos with "crossing" in the title
uv run yt download https://www.youtube.com/@SomeChannel crossing

# Download matching videos at 720p
uv run yt download https://www.youtube.com/@SomeChannel crossing -d -r 720
```

### Transcribe

Download audio from YouTube and transcribe using Parakeet-MLX.

```bash
uv run yt transcribe SOURCE [options]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--outdir DIR` | `transcriptions` | Output directory |
| `--model REPO` | `mlx-community/parakeet-tdt-0.6b-v2` | Parakeet-MLX model |
| `--chunk-seconds N` | `120` | Chunk size for transcription |
| `--overlap-seconds N` | `15` | Overlap between chunks |

Examples:
```bash
# Transcribe a YouTube video
uv run yt transcribe https://www.youtube.com/watch?v=VIDEO_ID

# Transcribe a local WAV file
uv run yt transcribe recording.wav --outdir ./output
```

## Aliases

Both commands have short aliases:
- `download` → `dl`
- `transcribe` → `tr`

```bash
uv run yt dl URL -d
uv run yt tr https://youtube.com/watch?v=...
```
