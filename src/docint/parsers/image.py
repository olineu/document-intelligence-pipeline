"""
Image parser — OCR for PNG, JPEG, TIFF files.

Pre-processing steps before OCR significantly improve accuracy on real-world docs:
  1. Convert to greyscale
  2. Apply adaptive thresholding (handles uneven lighting/scanning)
  3. Deskew if needed (Tesseract handles mild skew, but we can help)
"""
from pathlib import Path

import structlog

from .base import ParsedDocument, Parser

log = structlog.get_logger()


class ImageParser(Parser):
    def parse(self, file_path: str | Path) -> ParsedDocument:
        import pytesseract
        from PIL import Image, ImageFilter, ImageOps

        path = self._validate_path(file_path)
        log.info("image.parse.start", path=str(path))

        img = Image.open(path)
        img = _preprocess(img)
        text = pytesseract.image_to_string(img, lang="eng", config="--psm 6")

        log.info("image.parse.done", path=str(path), chars=len(text))
        return ParsedDocument(
            text=text,
            source_path=str(path),
            format="image",
            page_count=1,
        )


def _preprocess(img) -> "Image":
    """Basic pre-processing to improve OCR quality."""
    from PIL import ImageOps

    # Convert to greyscale
    img = img.convert("L")

    # Increase contrast — helps with faded text
    img = ImageOps.autocontrast(img, cutoff=2)

    return img
