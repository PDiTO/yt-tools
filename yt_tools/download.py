# download.py - Download YouTube videos with keyword filtering

import subprocess
from pathlib import Path


def filter_videos(videos: list[dict], filters: dict) -> list[dict]:
    """Apply filters to video list."""
    result = []

    for v in videos:
        try:
            duration = float(v["duration"]) if v["duration"] != "NA" else 0
        except (ValueError, TypeError):
            duration = 0

        min_dur = filters.get("min_duration", 0)
        if min_dur and duration <= min_dur:
            continue

        max_dur = filters.get("max_duration")
        if max_dur and duration > max_dur:
            continue

        title = v.get("title", "").lower()
        if filters.get("keywords"):
            if not all(kw.lower() in title for kw in filters["keywords"]):
                continue

        result.append(v)

    return result


def list_videos(url: str) -> list[dict]:
    """Fetch all videos from a channel/playlist."""
    args = ["yt-dlp", "--flat-playlist", "--print", "%(id)s\t%(duration)s\t%(title)s", url]
    result = subprocess.run(args, capture_output=True, text=True)

    videos = []
    for line in result.stdout.strip().split("\n"):
        if "\t" in line:
            parts = line.split("\t", 2)
            if len(parts) >= 3:
                videos.append({
                    "id": parts[0],
                    "duration": parts[1],
                    "title": parts[2],
                })
    return videos


def download_videos(videos: list[dict], output_dir: str, resolution: str = "1080") -> None:
    """Download videos by ID."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Prefer m4a audio (AAC) to avoid re-encoding when merging to mp4
    if resolution == "best":
        fmt = "bestvideo+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
    else:
        fmt = f"bestvideo[height<={resolution}]+bestaudio[ext=m4a]/bestvideo[height<={resolution}]+bestaudio/best[height<={resolution}]"

    for v in videos:
        video_url = f"https://www.youtube.com/watch?v={v['id']}"
        args = [
            "yt-dlp",
            "-f", fmt,
            "--merge-output-format", "mp4",
            "-o", f"{output_path}/%(title)s.%(ext)s",
            video_url
        ]
        print(f"Downloading: {v['title'][:70]}...")
        subprocess.run(args)


def format_duration(seconds: float) -> str:
    """Format duration as MM:SS."""
    mins, secs = divmod(int(seconds), 60)
    return f"{mins:02d}:{secs:02d}"
