"""
Lesson 10 — Document Q&A with Source Citations

Builds a per-document RAG system that:
  1. Chunks a document into passages
  2. Retrieves relevant passages for a question
  3. Generates answers with citations
  4. Abstains when the answer isn't in the document

Run: python lessons/10_document_qa/exercise.py
Requires: ANTHROPIC_API_KEY in .env
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))

from dotenv import load_dotenv
load_dotenv()

import json
import math
from dataclasses import dataclass


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


# ── Sample contract document ──────────────────────────────────────────────────

CONTRACT_TEXT = """
SERVICE AGREEMENT
Agreement No: SA-2024-0042

This Service Agreement ("Agreement") is entered into as of November 1, 2024,
between Acme Software GmbH ("Service Provider") and TechCorp Europe BV ("Client").

SECTION 1 — SERVICES
1.1 Service Provider agrees to deliver the following services:
    (a) Annual software license for the Acme Platform
    (b) Implementation support up to 20 hours per month
    (c) 24/7 technical support via email and phone

1.2 Service Provider shall maintain 99.5% uptime for the Acme Platform,
    measured monthly. Scheduled maintenance windows are excluded from uptime calculations.

SECTION 2 — FEES AND PAYMENT
2.1 Client shall pay EUR 8,500 per year for the software license.
2.2 Implementation support shall be billed at EUR 150 per hour.
2.3 Invoices are due within 30 days of issuance (Net 30).
2.4 Late payments shall incur a penalty of 1.5% per month on the outstanding balance,
    calculated from the due date until the date of actual payment.

SECTION 3 — TERM AND TERMINATION
3.1 This Agreement commences on November 1, 2024 and continues for one (1) year.
3.2 Either party may terminate this Agreement upon 60 days written notice.
3.3 Client may terminate immediately if Service Provider fails to meet the
    uptime SLA for three consecutive months.

SECTION 4 — LIMITATION OF LIABILITY
4.1 Service Provider's total liability under this Agreement shall not exceed
    the total fees paid by Client in the twelve months preceding the claim.
4.2 Neither party shall be liable for indirect, incidental, or consequential damages.

SECTION 5 — CONFIDENTIALITY
5.1 Both parties agree to maintain the confidentiality of proprietary information
    received from the other party for a period of three (3) years after disclosure.
5.2 Confidential information does not include information that is publicly available
    or independently developed without reference to the disclosing party's information.

SECTION 6 — GOVERNING LAW
6.1 This Agreement shall be governed by the laws of Germany.
6.2 Any disputes shall be resolved by the courts of Munich, Germany.
"""


# ── Chunking ──────────────────────────────────────────────────────────────────

@dataclass
class Chunk:
    id: str
    text: str
    section: str  # e.g. "SECTION 2 — FEES AND PAYMENT"


def chunk_by_section(text: str) -> list[Chunk]:
    """
    Split document at section headers.
    This is a simplified version — Dockling would do this semantically.
    """
    import re

    chunks = []
    sections = re.split(r"(?=SECTION \d+\s*—)", text)

    for i, section_text in enumerate(sections):
        if not section_text.strip():
            continue

        # Extract section title from first line
        lines = section_text.strip().split("\n")
        title = lines[0].strip()
        body = "\n".join(lines[1:]).strip()

        if body:
            chunks.append(Chunk(
                id=f"chunk_{i:02d}",
                text=f"{title}\n{body}",
                section=title,
            ))

    return chunks


section("Exercise 1: Document chunking")
chunks = chunk_by_section(CONTRACT_TEXT)
print(f"Document split into {len(chunks)} chunks:\n")
for c in chunks:
    preview = c.text[:80].replace("\n", " ")
    print(f"  [{c.id}] {c.section}")
    print(f"          {preview}...")
    print()


# ── Embedding + retrieval ─────────────────────────────────────────────────────

def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x**2 for x in a))
    norm_b = math.sqrt(sum(x**2 for x in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed texts using Anthropic embeddings (text-embedding-3-small via OpenAI as fallback)."""
    try:
        # Anthropic doesn't have a direct embedding endpoint — use a simple TF-IDF-like approach for demo
        # In production, use: openai.embeddings.create() or voyageai.Client().embed()
        from collections import Counter
        import re

        def tfidf_embed(text: str, vocab: set) -> list[float]:
            words = re.findall(r'\w+', text.lower())
            counts = Counter(words)
            return [counts.get(w, 0) / (len(words) or 1) for w in sorted(vocab)]

        # Build vocabulary from all texts
        all_words = set()
        for text in texts:
            all_words.update(re.findall(r'\w+', text.lower()))
        vocab = sorted(all_words)

        return [tfidf_embed(text, set(vocab)) for text in texts]
    except Exception as e:
        return [[0.0] * 10 for _ in texts]


section("Exercise 2: Embedding and retrieval")
print("Embedding document chunks... (using simplified TF-IDF for demo)")
print("In production: use a real embedding model (voyage-3, text-embedding-3-large)\n")

all_texts = [c.text for c in chunks]
embeddings = embed_texts(all_texts)
print(f"Embedded {len(embeddings)} chunks, vector size: {len(embeddings[0])}")


def retrieve(question: str, chunks: list[Chunk], embeddings: list, top_k: int = 3) -> list[Chunk]:
    """Find the most relevant chunks for a question."""
    q_embedding = embed_texts([question])[0]
    scores = [(cosine_similarity(q_embedding, emb), chunk)
              for emb, chunk in zip(embeddings, chunks)]
    scores.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scores[:top_k]]


# Test retrieval
test_question = "What is the late payment penalty?"
relevant = retrieve(test_question, chunks, embeddings)
print(f"\nFor question: '{test_question}'")
print(f"Retrieved chunks: {[c.id for c in relevant]}")


# ── Q&A with citations ────────────────────────────────────────────────────────

section("Exercise 3: Document Q&A with citations")

SYSTEM_PROMPT = """You are a document analysis assistant. Answer questions using ONLY
the provided document passages. You must:

1. Base your answer strictly on the provided passages
2. Quote the relevant text that supports your answer
3. Reference the section where the quote appears
4. If the answer is not clearly present in the passages, respond with exactly:
   "NOT FOUND: This information is not in the provided document sections."

Format:
Answer: [your answer]
Quote: "[exact relevant text from passage]"
Section: [section reference]
"""

def answer_with_citation(
    question: str,
    chunks: list[Chunk],
    embeddings: list,
) -> dict:
    try:
        import anthropic
        client = anthropic.Anthropic()

        relevant_chunks = retrieve(question, chunks, embeddings, top_k=3)
        context = "\n\n---\n\n".join(
            f"[{c.id} | {c.section}]\n{c.text}"
            for c in relevant_chunks
        )

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Question: {question}\n\nRelevant document passages:\n{context}"
            }],
        )

        answer_text = response.content[0].text
        return {
            "question": question,
            "answer": answer_text,
            "source_chunks": [c.id for c in relevant_chunks],
            "sources": [c.section for c in relevant_chunks],
        }
    except ImportError:
        return {"question": question, "answer": "[anthropic not installed]", "source_chunks": []}
    except Exception as e:
        return {"question": question, "answer": f"[Error: {e}]", "source_chunks": []}


questions = [
    "What is the late payment penalty?",
    "What is the uptime SLA?",
    "What is the termination notice period?",
    "What is the limitation of liability cap?",
    "Does the contract include a warranty for fitness for purpose?",  # not in document
    "What is the jurisdiction for disputes?",
]

try:
    import anthropic  # test if available

    for q in questions:
        result = answer_with_citation(q, chunks, embeddings)
        print(f"Q: {q}")
        print(f"   {result['answer'][:200]}")
        print(f"   Sources: {result['sources']}")
        print()

except ImportError:
    print("Set ANTHROPIC_API_KEY in .env to run Q&A exercises")


# ── Exercise 4: Abstain behaviour ────────────────────────────────────────────

section("Exercise 4: Abstain vs hallucinate")
print("""
The last question above — "Does the contract include a warranty for fitness for purpose?"
— is NOT in the document. The system should say "NOT FOUND", not invent an answer.

Why this matters:
  If a lawyer asks "does this contract exclude implied warranties?" and the system
  says "yes" when the clause doesn't exist, the consequence is real legal exposure.

The system prompt enforces cite-or-abstain:
  → If found: answer + exact quote + section reference
  → If not found: "NOT FOUND: This information is not in the provided document sections."

This is more useful than a confident wrong answer.

Production hardening:
  - Add a "confidence" field to each answer (0.0–1.0)
  - Route low-confidence answers to human review (same pattern as extraction)
  - Log all "NOT FOUND" answers — they reveal gaps in your document coverage
  - Consider secondary search: if not in this document, search the document corpus
""")

print("="*60)
print("Lesson 10 complete — full course finished.")
print("="*60)
print("""
What you've built:
  01: Parse any document format
  02: Extract structured fields with tool_use
  03: Design extraction schemas
  04: Score and validate confidence
  05: Route uncertain docs to human review
  06: Serve via FastAPI
  07: Use Vision LLMs for better OCR
  08: Semantic parsing with Dockling
  09: Multi-step agentic document workflows
  10: Document Q&A with citations

Next: apply this to a real document type from your work.
""")
