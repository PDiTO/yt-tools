# cli.py - Unified CLI for YouTube download and transcription

import argparse
import os
import sys

from yt_tools.download import (
    download_videos,
    filter_videos,
    format_duration,
    list_videos,
)
from yt_tools.transcribe import (
    DEFAULT_CHUNK_SECONDS,
    DEFAULT_MODEL_REPO,
    DEFAULT_OVERLAP_SECONDS,
    Spinner,
    download_audio_with_ytdlp,
    transcribe_audio,
    write_transcripts,
)


def cmd_download(args):
    """Handle the download subcommand."""
    filters = {
        "keywords": args.keywords,
        "min_duration": 0 if args.shorts or args.only_shorts else 60,
        "max_duration": 60 if args.only_shorts else None,
    }

    print(f"Fetching videos from {args.url}...")
    videos = list_videos(args.url)
    videos = filter_videos(videos, filters)

    if args.max:
        videos = videos[:args.max]

    if not videos:
        print("No videos match the filters.")
        return 1

    print(f"\nFound {len(videos)} videos:\n")
    for i, v in enumerate(videos, 1):
        dur = float(v["duration"]) if v["duration"] != "NA" else 0
        print(f"{i:3}. [{format_duration(dur)}] {v['title']}")

    if args.download:
        print()
        download_videos(videos, args.output, args.resolution)

    return 0


def cmd_transcribe(args):
    """Handle the transcribe subcommand."""
    import shutil

    source = args.source
    outdir = args.outdir
    is_url = source.startswith("http://") or source.startswith("https://")

    if is_url:
        print("Downloading audio with yt-dlp ...")
        wav_path, base_name = download_audio_with_ytdlp(source, outdir)
    else:
        if not os.path.isfile(source):
            print(f"Error: file not found: {source}", file=sys.stderr)
            return 1
        if not source.lower().endswith(".wav"):
            print(
                "Error: local files must be WAV. Provide a YouTube URL instead, "
                "or convert your file to WAV (16kHz mono recommended)",
                file=sys.stderr,
            )
            return 1
        os.makedirs(outdir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(source))[0]
        dest_wav_path = os.path.join(outdir, f"{base_name}.wav")
        if os.path.abspath(source) != os.path.abspath(dest_wav_path):
            shutil.copyfile(source, dest_wav_path)
        wav_path = dest_wav_path

    with Spinner("Transcribing (first run downloads model)"):
        result = transcribe_audio(
            wav_path,
            model_repo=args.model,
            chunk_seconds=args.chunk_seconds,
            overlap_seconds=args.overlap_seconds,
        )

    text_path, json_path = write_transcripts(outdir, base_name, result)

    print(f"Saved transcript: {text_path}")
    print(f"Saved full JSON: {json_path}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="yt",
        description="YouTube video downloader and transcriber",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Download subcommand
    dl_parser = subparsers.add_parser(
        "download",
        aliases=["dl"],
        help="Download videos from a channel or playlist",
        epilog="Examples:\n"
               "  yt download URL                      # List all full videos\n"
               "  yt download URL crossing             # Videos with 'crossing' in title\n"
               "  yt download URL -d crossing          # Download at 1080p max\n"
               "  yt download URL -d crossing -r 720   # Download at 720p max\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    dl_parser.add_argument("url", help="YouTube channel or playlist URL")
    dl_parser.add_argument("keywords", nargs="*", help="Keywords that must appear in title")
    dl_parser.add_argument("-d", "--download", action="store_true", help="Download (default: list only)")
    dl_parser.add_argument("-n", "--max", type=int, help="Maximum number of videos")
    dl_parser.add_argument("-o", "--output", default="./downloads", help="Output directory")
    dl_parser.add_argument("-r", "--resolution", default="1080", help="Max resolution: 720, 1080, or best")
    dl_parser.add_argument("--shorts", action="store_true", help="Include shorts (<=60s)")
    dl_parser.add_argument("--only-shorts", action="store_true", help="Only shorts")
    dl_parser.set_defaults(func=cmd_download)

    # Transcribe subcommand
    tr_parser = subparsers.add_parser(
        "transcribe",
        aliases=["tr"],
        help="Transcribe a YouTube video or local audio file",
        description="Download audio from YouTube and transcribe with Parakeet-MLX."
    )
    tr_parser.add_argument("source", help="YouTube URL or local WAV file path")
    tr_parser.add_argument("--outdir", default="transcriptions", help="Output directory")
    tr_parser.add_argument("--model", default=DEFAULT_MODEL_REPO, help="Parakeet-MLX model repo")
    tr_parser.add_argument("--chunk-seconds", type=float, default=DEFAULT_CHUNK_SECONDS, help="Chunk size")
    tr_parser.add_argument("--overlap-seconds", type=float, default=DEFAULT_OVERLAP_SECONDS, help="Overlap between chunks")
    tr_parser.set_defaults(func=cmd_transcribe)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
