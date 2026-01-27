# transcribe.py - Transcribe YouTube videos or local audio files

import json
import os
import shutil
import sys
import threading
import time
from dataclasses import asdict, is_dataclass
from itertools import cycle
from typing import Optional, Tuple

from tqdm import tqdm
from yt_dlp import YoutubeDL

try:
    import numpy as np
except Exception:
    np = None

DEFAULT_MODEL_REPO = "mlx-community/parakeet-tdt-0.6b-v2"
DEFAULT_CHUNK_SECONDS = 120.0
DEFAULT_OVERLAP_SECONDS = 15.0


def ensure_ffmpeg_available() -> None:
    """Ensure ffmpeg is installed and available on PATH."""
    if shutil.which("ffmpeg") is None:
        print(
            "Error: ffmpeg is required but not found on PATH.\n"
            "On macOS: brew install ffmpeg\n"
            "On Ubuntu/Debian: sudo apt-get install ffmpeg\n",
            file=sys.stderr,
        )
        sys.exit(1)


def download_audio_with_ytdlp(
    url: str,
    output_directory: str,
    target_format: str = "wav",
    sample_rate_hz: int = 16000,
    audio_channels: int = 1,
) -> Tuple[str, str]:
    """Download a YouTube video's audio as a WAV file using yt-dlp."""
    ensure_ffmpeg_available()
    os.makedirs(output_directory, exist_ok=True)

    progress_holder: dict[str, Optional[tqdm]] = {"bar": None}

    def progress_hook(d: dict) -> None:
        status = d.get("status")
        if status == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            if progress_holder["bar"] is None:
                progress_holder["bar"] = tqdm(
                    total=total or 0,
                    unit="B",
                    unit_scale=True,
                    desc="Downloading",
                    leave=True,
                )
            bar = progress_holder["bar"]
            if bar is not None:
                if total and bar.total != total:
                    bar.total = total
                bar.n = downloaded
                bar.refresh()
        elif status == "finished":
            bar = progress_holder.get("bar")
            if bar is not None:
                if bar.total and bar.n < bar.total:
                    bar.n = bar.total
                bar.close()
                progress_holder["bar"] = None
            tqdm.write("Converting to WAV...")
        elif status == "postprocessing":
            tqdm.write("Post-processing audio...")

    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "noprogress": True,
        "noplaylist": True,
        "restrictfilenames": True,
        "outtmpl": os.path.join(output_directory, "%(title)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": target_format,
                "preferredquality": "0",
            },
        ],
        "postprocessor_args": ["-ar", str(sample_rate_hz), "-ac", str(audio_channels)],
        "progress_hooks": [progress_hook],
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        prepared_path = ydl.prepare_filename(info)
        base_path, _ = os.path.splitext(prepared_path)
        wav_path = base_path + f".{target_format}"

    base_name = os.path.basename(base_path)
    return wav_path, base_name


def transcribe_audio(
    audio_path: str,
    model_repo: str = DEFAULT_MODEL_REPO,
    chunk_seconds: float = DEFAULT_CHUNK_SECONDS,
    overlap_seconds: float = DEFAULT_OVERLAP_SECONDS,
):
    """Transcribe an audio file with Parakeet-MLX and return the result object."""
    from parakeet_mlx import from_pretrained

    model = from_pretrained(model_repo)
    model.encoder.set_attention_model("rel_pos_local_attn", (256, 256))

    result = model.transcribe(
        audio_path,
        chunk_duration=chunk_seconds,
        overlap_duration=overlap_seconds,
    )
    return result


def write_transcripts(
    output_directory: str,
    base_name: str,
    result,
) -> Tuple[str, str]:
    """Write .txt and .json transcripts to the specified output directory."""
    text_path = os.path.join(output_directory, f"{base_name}.txt")
    json_path = os.path.join(output_directory, f"{base_name}.json")

    with open(text_path, "w", encoding="utf-8") as f:
        f.write(result.text)

    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(to_jsonable(result), jf, ensure_ascii=False, indent=2)

    return text_path, json_path


def to_jsonable(obj):
    """Recursively convert an object to a JSON-serializable structure."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if is_dataclass(obj):
        return to_jsonable(asdict(obj))
    if np is not None:
        try:
            if isinstance(obj, np.generic):
                return obj.item()
            if isinstance(obj, np.ndarray):
                return obj.tolist()
        except Exception:
            pass
    to_dict = getattr(obj, "to_dict", None)
    if callable(to_dict):
        try:
            return to_jsonable(to_dict())
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        try:
            return {k: to_jsonable(v) for k, v in vars(obj).items() if not k.startswith("_")}
        except Exception:
            pass
    return repr(obj)


class Spinner:
    """Simple CLI spinner as a context manager."""

    def __init__(self, message: str = "Working") -> None:
        self.message = message
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _run(self) -> None:
        for ch in cycle("|/-\\"):
            if self._stop_event.is_set():
                break
            print(f"\r{self.message} {ch}", end="", flush=True)
            time.sleep(0.1)
        print("\r" + " " * (len(self.message) + 2) + "\r", end="", flush=True)

    def __enter__(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join()
