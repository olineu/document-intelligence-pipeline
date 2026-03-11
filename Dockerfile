FROM python:3.11-slim

# Tesseract OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN pip install -e "."

COPY src/ src/
COPY schemas/ schemas/

CMD ["uvicorn", "src.docint.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
