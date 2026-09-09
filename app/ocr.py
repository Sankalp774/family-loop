from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

TESSERACT = shutil.which("tesseract") or "/opt/homebrew/bin/tesseract"


def image_to_text(data: bytes, suffix: str = ".png") -> str:
    """OCR a Screen Time / Digital Wellbeing screenshot to plain text."""
    if not data:
        return ""
    suffix = suffix if suffix.startswith(".") else f".{suffix}"
    if suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp", ".heic", ".gif", ".tif", ".tiff"}:
        suffix = ".png"
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / f"shot{suffix}"
        src.write_bytes(data)
        out = Path(tmp) / "out"
        cmd = [TESSERACT, str(src), str(out), "-l", "eng", "--psm", "6"]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            # Looser page segmentation if the first pass fails.
            try:
                subprocess.run(
                    [TESSERACT, str(src), str(out), "-l", "eng", "--psm", "4"],
                    check=True,
                    capture_output=True,
                    timeout=30,
                )
            except Exception as exc:
                raise RuntimeError(f"Could not read text from the photo ({exc}).") from exc
        text_path = Path(str(out) + ".txt")
        return text_path.read_text(encoding="utf-8", errors="replace") if text_path.exists() else ""
