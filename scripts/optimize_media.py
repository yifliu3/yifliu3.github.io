"""Build homepage previews without modifying the original media.

Keep source frame rates up to 30 fps and use CRF 25 for smoother, clearer video.
Install Pillow and imageio-ffmpeg, then run: python3 scripts/optimize_media.py
"""

from pathlib import Path
import subprocess

import imageio_ffmpeg
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "media"


def main():
    OUTPUT.mkdir(exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    for name in ("Hy-Nomas", "HYWorld1.1", "WorldMirror", "MonoSplat"):
        original = ROOT / "vid" / f"{name}.mp4"
        preview = OUTPUT / f"{name}.mp4"
        subprocess.run([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(original), "-map", "0:v:0", "-an",
            "-vf", "scale=640:-2:flags=lanczos,fps='min(source_fps,30)'",
            "-c:v", "libx264", "-preset", "slow", "-crf", "25",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(preview),
        ], check=True)
        poster = OUTPUT / f"{name}.webp"
        if name == "Hy-Nomas":
            with Image.open(ROOT / "pic/hy-nomas-poster.jpg") as image:
                image.thumbnail((640, 640), Image.Resampling.LANCZOS)
                image.save(poster, quality=82, method=6)
        else:
            subprocess.run([
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-ss", "1", "-i", str(preview), "-frames:v", "1",
                "-c:v", "libwebp", "-quality", "82", str(poster),
            ], check=True)
        print(f"{name}: {original.stat().st_size:,} -> {preview.stat().st_size:,} bytes", flush=True)

    images = (
        ("pic/YIFANLIU.PNG", "portrait.webp", (480, 480)),
        ("pic/IMG_EndoGaussianJ.PNG", "endogaussian.webp", (960, 960)),
        ("pic/IMG_ukan.jpg", "ukan.webp", (960, 960)),
        ("images/education/cuhk.png", "cuhk.webp", (84, 84)),
        ("images/education/hust.png", "hust.webp", (84, 84)),
    )
    for source, name, size in images:
        with Image.open(ROOT / source) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail(size, Image.Resampling.LANCZOS)
            image.save(OUTPUT / name, quality=85, method=6)
            print(f"{name}: {image.width}x{image.height}, {(OUTPUT / name).stat().st_size:,} bytes", flush=True)


if __name__ == "__main__":
    main()
