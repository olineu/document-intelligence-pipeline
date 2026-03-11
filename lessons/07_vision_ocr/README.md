# Lesson 07 — Vision LLM as OCR

**Goal:** Replace Tesseract with a Vision Language Model for dramatically better OCR on complex documents.

---

## Why Tesseract fails on real documents

Tesseract works by:
1. Segmenting the image into individual characters
2. Classifying each character using a trained model
3. Reconstructing words and lines from character positions

This works well for clean, single-column text in a standard font. It breaks on:
- **Multi-column layouts** — text from different columns gets interleaved
- **Tables within images** — cell boundaries confuse the line reconstruction
- **Non-standard fonts** — logos, handwriting, artistic typography
- **Mixed content** — a page with a chart next to a table next to a paragraph

The failure mode is silent and insidious: Tesseract returns *something*, just wrong.

---

## How Vision LLMs approach OCR differently

A VLM (Llama 3.2 Vision, Claude, Qwen VL, Gemma 3) takes the whole page image as input
and generates text as output — same as answering a question about an image.

This means:
- It sees layout, column structure, table borders, and text together
- It can follow reading order the way a human does
- It can handle handwriting, stamps, watermarks
- For structured content, you can ask it to output Markdown tables directly

The cost: VLM OCR is 10–50× more expensive per page than Tesseract.
The benefit: it works on documents that Tesseract garbles completely.

---

## Three approaches covered in this lesson

### 1. Claude Vision API (cloud, best quality)
Send the page as a base64-encoded image. Ask Claude to transcribe it.
Best for: complex documents where accuracy is critical.

### 2. Llama 3.2 Vision via Ollama (local, no cost)
Run Llama 3.2 Vision locally with Ollama. Same API pattern, zero token cost.
The `llama-ocr` project shows this pattern.
Best for: high volume, privacy-sensitive documents.

### 3. Hybrid strategy (cost-optimised)
Use Tesseract first. Measure text quality (character count, word detection rate).
If quality is below threshold, escalate to VLM OCR.
Best for: production pipelines with mixed document quality.

---

## Exercise

```bash
# Requires Ollama + llama3.2-vision (no API key):
#   brew install ollama && ollama pull llama3.2-vision

# OR set ANTHROPIC_API_KEY for Claude vision

python lessons/07_vision_ocr/exercise.py
```

The exercise:
1. Takes a sample scanned image
2. Runs Tesseract OCR and shows output
3. Runs Claude vision OCR on the same image
4. Runs Llama 3.2 Vision OCR (if Ollama is available)
5. Compares all three outputs

---

## Updating the pipeline parser

After this lesson, you'll swap the `ImageParser._preprocess` + Tesseract path in
[src/docint/parsers/image.py](../../src/docint/parsers/image.py) for a VLM call:

```python
def _extract_with_vision_llm(self, path: Path) -> str:
    import anthropic, base64
    client = anthropic.Anthropic()
    with open(path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64",
                  "media_type": "image/png", "data": image_data}},
                {"type": "text", "text":
                  "Transcribe all text in this document image. "
                  "Preserve tables as markdown tables. "
                  "Preserve the reading order (left-to-right, top-to-bottom)."}
            ]
        }]
    )
    return response.content[0].text
```

---

## Key concepts

- VLM OCR = treating document transcription as a vision-to-text task
- Local VLMs (Llama 3.2 Vision via Ollama) can match Tesseract quality at zero marginal cost
- The hybrid strategy is what you'd use in production: Tesseract for easy docs, VLM for hard ones
- Quality signal: measure character count, check for common OCR artifacts (`l` vs `1`, `0` vs `O`)

---

## Next

→ [Lesson 08 — Semantic Document Parsing with Dockling](../08_dockling/README.md)
