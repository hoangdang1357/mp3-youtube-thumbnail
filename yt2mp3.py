#!/usr/bin/env python3
import os
import sys
import tempfile
import yt_dlp
from urllib.parse import urlparse
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error
from yt_dlp.utils import sanitize_filename
from PIL import Image

def get_ext_from_url(url):
    """Extract file extension from a URL (default to jpg)."""
    path = urlparse(url).path
    ext = os.path.splitext(path)[1].lstrip(".")
    return ext if ext else "jpg"

def download_youtube_audio(url, output_dir):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"},
            {"key": "FFmpegMetadata"},
        ],
        "writethumbnail": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = sanitize_filename(info.get("title", "output"))

        # Final mp3 path
        mp3_path = os.path.join(output_dir, f"{title}.mp3")

        # yt-dlp writes thumbnail alongside audio with video extension
        base_filename = ydl.prepare_filename(info).rsplit(".", 1)[0]
        possible_exts = ["webp", "jpg", "png"]
        thumb_file = None

        for ext in possible_exts:
            candidate = f"{base_filename}.{ext}"
            if os.path.exists(candidate):
                thumb_file = candidate
                break

        if thumb_file and thumb_file.endswith(".webp"):
            # Convert webp to jpg for compatibility
            img = Image.open(thumb_file).convert("RGB")
            jpg_file = thumb_file.rsplit(".", 1)[0] + ".jpg"
            img.save(jpg_file, "JPEG")
            thumb_file = jpg_file

        return mp3_path, thumb_file, title

def embed_thumbnail(mp3_path, thumb_path):
    if not thumb_path or not os.path.exists(thumb_path):
        print("⚠️ No thumbnail found, skipping embedding.")
        return

    audio = MP3(mp3_path, ID3=ID3)

    try:
        audio.add_tags()
    except error:
        pass

    # Guess mime type
    mime = "image/jpeg"
    if thumb_path.lower().endswith("png"):
        mime = "image/png"

    with open(thumb_path, "rb") as img:
        audio.tags.add(
            APIC(
                encoding=3,
                mime=mime,
                type=3,  # front cover
                desc="Cover",
                data=img.read()
            )
        )
    audio.save()
    print(f"✅ Embedded thumbnail into {mp3_path}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python yt2mp3.py <YouTube URL>")
        sys.exit(1)

    url = sys.argv[1]
    with tempfile.TemporaryDirectory() as tmpdir:
        mp3_path, thumb_path, title = download_youtube_audio(url, tmpdir)

        final_mp3 = f"{title}.mp3"
        if os.path.exists(final_mp3):
            os.remove(final_mp3)  # overwrite if exists

        os.rename(mp3_path, final_mp3)

        embed_thumbnail(final_mp3, thumb_path)

        print(f"🎵 Done! Saved as {final_mp3}")

if __name__ == "__main__":
    main()
