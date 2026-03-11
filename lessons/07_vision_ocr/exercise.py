"""
Lesson 07 — Vision LLM as OCR Exercise

Compares three OCR approaches on the same document image:
  1. Tesseract (classical)
  2. Claude Vision API
  3. Llama 3.2 Vision via Ollama (local, optional)

Run: python lessons/07_vision_ocr/exercise.py

Requirements:
  - ANTHROPIC_API_KEY in .env for Claude approach
  - Ollama + llama3.2-vision for local approach (optional)
    Install: brew install ollama && ollama pull llama3.2-vision
"""
import sys
import base64
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from dotenv import load_dotenv
load_dotenv()


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def create_sample_image() -> bytes:
    """
    Create a simple test image with text for demonstration.
    In practice you'd load a real scanned document.
    """
    from PIL import Image, ImageDraw, ImageFont
    import io

    img = Image.new("RGB", (600, 400), color="white")
    draw = ImageDraw.Draw(img)

    # Simulate a simple invoice layout
    lines = [
        ("INVOICE", 40, 30, 18),
        ("Invoice No: INV-2024-0042", 40, 70, 12),
        ("Date: 2024-11-15", 40, 95, 12),
        ("Vendor: Acme GmbH", 40, 130, 12),
        ("Total: EUR 13,685.00", 40, 155, 12),
        ("IBAN: DE89 3704 0044 0532 0130 00", 40, 190, 11),
        ("Payment Terms: Net 30", 40, 215, 11),
    ]

    for text, x, y, size in lines:
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
        except Exception:
            font = ImageFont.load_default()
        draw.text((x, y), text, fill="black", font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── Exercise 1: Generate / load sample image ─────────────────────────────────

section("Exercise 1: Sample document image")

try:
    from PIL import Image
    image_bytes = create_sample_image()
    print(f"Created sample invoice image ({len(image_bytes)} bytes)")
    print("(In practice: load a real scanned PDF page or image file)")
except ImportError:
    print("Pillow not installed — using placeholder bytes")
    image_bytes = b""


# ── Exercise 2: Tesseract OCR ────────────────────────────────────────────────

section("Exercise 2: Tesseract OCR (baseline)")

def tesseract_ocr(image_bytes: bytes) -> str:
    try:
        import pytesseract
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(image_bytes)).convert("L")  # greyscale
        text = pytesseract.image_to_string(img, lang="eng", config="--psm 6")
        return text.strip()
    except ImportError:
        return "[Tesseract not installed — pip install pytesseract and install tesseract-ocr]"
    except Exception as e:
        return f"[Tesseract error: {e}]"

tesseract_result = tesseract_ocr(image_bytes)
print("Tesseract output:")
print(f"  {tesseract_result.replace(chr(10), chr(10) + '  ')}")


# ── Exercise 3: Claude Vision API ───────────────────────────────────────────

section("Exercise 3: Claude Vision API OCR")

def claude_vision_ocr(image_bytes: bytes) -> str:
    try:
        import anthropic
        client = anthropic.Anthropic()
        image_b64 = base64.standard_b64encode(image_bytes).decode()

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Transcribe all text in this document image. "
                            "Preserve the exact text and layout. "
                            "If there are tables, format them as markdown tables. "
                            "Output only the transcribed text, no commentary."
                        ),
                    },
                ],
            }],
        )
        return response.content[0].text.strip()
    except ImportError:
        return "[anthropic not installed]"
    except Exception as e:
        return f"[Claude API error: {e}]"

if image_bytes:
    claude_result = claude_vision_ocr(image_bytes)
    print("Claude Vision output:")
    print(f"  {claude_result.replace(chr(10), chr(10) + '  ')}")
else:
    print("No image bytes — skipping Claude Vision call")
    claude_result = ""


# ── Exercise 4: Llama 3.2 Vision via Ollama (local) ─────────────────────────

section("Exercise 4: Llama 3.2 Vision via Ollama (local, optional)")
print("This approach runs entirely locally — no API key, no cost.")
print("Install: brew install ollama && ollama pull llama3.2-vision\n")

def ollama_vision_ocr(image_bytes: bytes) -> str:
    try:
        import ollama
        image_b64 = base64.standard_b64encode(image_bytes).decode()
        response = ollama.chat(
            model="llama3.2-vision",
            messages=[{
                "role": "user",
                "content": (
                    "Transcribe all text in this document image exactly as written. "
                    "Output only the text, no commentary."
                ),
                "images": [image_b64],
            }],
        )
        return response["message"]["content"].strip()
    except ImportError:
        return "[ollama Python package not installed: pip install ollama]"
    except Exception as e:
        return f"[Ollama not available or model not pulled: {e}]"

if image_bytes:
    ollama_result = ollama_vision_ocr(image_bytes)
    print("Llama 3.2 Vision output:")
    print(f"  {ollama_result.replace(chr(10), chr(10) + '  ')}")


# ── Exercise 5: Comparison + cost analysis ───────────────────────────────────

section("Exercise 5: When to use each approach")
print("""
Approach comparison:

┌─────────────────────┬──────────┬──────────────┬────────────────────────────┐
│ Approach            │ Cost     │ Quality      │ Best for                   │
├─────────────────────┼──────────┼──────────────┼────────────────────────────┤
│ Tesseract           │ Free     │ Good (simple)│ Clean, single-column text  │
│                     │          │ Poor (complex│ High-volume, low cost req. │
├─────────────────────┼──────────┼──────────────┼────────────────────────────┤
│ Claude Vision API   │ ~$0.003/ │ Excellent    │ Complex layouts, tables    │
│                     │ page     │              │ Critical accuracy required │
├─────────────────────┼──────────┼──────────────┼────────────────────────────┤
│ Llama 3.2 Vision    │ Free     │ Good-very    │ Privacy-sensitive docs     │
│ (Ollama, local)     │ (compute)│ good         │ High volume with GPU       │
└─────────────────────┴──────────┴──────────────┴────────────────────────────┘

Production strategy — hybrid approach:
  1. Try Tesseract first (free, fast)
  2. Check quality: if len(text) < threshold or error_rate > X: escalate
  3. Escalate to VLM OCR only for documents that need it

Quality signals to check after Tesseract:
  - Character count (< 50 chars per page = likely failed)
  - Word count vs expected word density for document type
  - Presence of common OCR garbage: "l1l1l", "0O0O", random symbols
  - Test: try re-parsing a random word — does it appear in an English dictionary?
""")


# ── Exercise 6: Update the pipeline ─────────────────────────────────────────

section("Exercise 6: Integrating VLM OCR into the pipeline")
print("""
The current ImageParser in src/docint/parsers/image.py uses Tesseract.
To switch it to Claude Vision, you'd update _preprocess + image_to_string:

  class ImageParser(Parser):
      def parse(self, file_path) -> ParsedDocument:
          path = self._validate_path(file_path)
          with open(path, "rb") as f:
              image_bytes = f.read()

          # Try Tesseract first
          text = self._tesseract_ocr(image_bytes)

          # Escalate to VLM if quality is too low
          if len(text.strip()) < 50:
              text = self._vision_llm_ocr(image_bytes)

          return ParsedDocument(text=text, source_path=str(path), format="image")

The same pattern applies to the PDF OCR fallback in pdf.py:
  _extract_with_ocr() currently uses Tesseract.
  Swap it for VLM OCR for complex scanned PDFs.

Task: implement vision_llm_ocr() in ImageParser as an alternative to Tesseract.
Add an environment variable VLM_OCR_PROVIDER=tesseract|claude|ollama to control which
provider is used, so you can switch without code changes.
""")

print("="*60)
print("Lesson 07 complete. Move on to: lessons/08_dockling/")
print("="*60)
