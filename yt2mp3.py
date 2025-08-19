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

def download_youtube_audio(url, output_dir):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"},
            {"key": "FFmpegMetadata"},
        ],
        "writethumbnail": True,
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = sanitize_filename(info.get("title", "output"))
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

        # Convert webp → jpg if needed
        if thumb_file and thumb_file.endswith(".webp"):
            img = Image.open(thumb_file).convert("RGB")
            jpg_file = thumb_file.rsplit(".", 1)[0] + ".jpg"
            img.save(jpg_file, "JPEG")
            thumb_file = jpg_file

        return mp3_path, thumb_file, title

def embed_thumbnail(mp3_path, thumb_path):
    if not thumb_path or not os.path.exists(thumb_path):
        print(f"⚠️ No thumbnail found for {mp3_path}, skipping embedding.")
        return

    audio = MP3(mp3_path, ID3=ID3)
    try:
        audio.add_tags()
    except error:
        pass

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

def process_url(url):
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            mp3_path, thumb_path, title = download_youtube_audio(url, tmpdir)
            final_mp3 = f"{title}.mp3"

            if os.path.exists(final_mp3):
                os.remove(final_mp3)

            os.rename(mp3_path, final_mp3)
            embed_thumbnail(final_mp3, thumb_path)
            print(f"🎵 Done! Saved as {final_mp3}")
        except Exception as e:
            print(f"❌ Failed to process {url}: {e}")

def main():
    if len(sys.argv) != 2:
        print("Usage:")
        print("  python yt2mp3.py <YouTube URL>")
        print("  python yt2mp3.py list.csv")
        sys.exit(1)

    arg = sys.argv[1]

    if arg.lower().endswith(".csv"):
        if not os.path.exists(arg):
            print(f"❌ File {arg} not found.")
            sys.exit(1)

        with open(arg, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]

        print(f"📄 Found {len(urls)} URLs in {arg}")
        for url in urls:
            print(f"➡️ Processing {url}")
            process_url(url)
    else:
        # Single URL mode
        process_url(arg)

if __name__ == "__main__":
    main()
