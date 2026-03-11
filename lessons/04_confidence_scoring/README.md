# Lesson 04 — Confidence Scoring

**Goal:** Understand the two layers of confidence and why both matter.

---

## Why confidence matters

At scale, you can't manually review every extracted document. You want the system to
handle confident extractions automatically and only surface uncertain ones for review.

But how do you know when to trust the extraction?

---

## Layer 1: LLM self-reported confidence

In the extraction schema, each field is accompanied by a `FieldConfidence` object:

```python
class FieldConfidence(BaseModel):
    field_name: str
    score: float   # 0.0 to 1.0
    reason: str    # why the model is or isn't confident
```

The LLM is prompted to score its own confidence:
- `1.0` — exact match, unambiguous
- `0.8–0.9` — high confidence, minor ambiguity
- `0.5–0.7` — moderate confidence, some interpretation
- `0.0–0.4` — low confidence, value may be wrong

This is already useful, but LLM self-reported confidence is **not calibrated** — it tends
to be overconfident. A model that says "0.9" is not correct 90% of the time.

---

## Layer 2: Deterministic validators

After the LLM extraction, we run rule-based validators on specific fields:

```python
def _validate_iban(value: str, score: float) -> tuple[float, str]:
    cleaned = value.replace(" ", "").upper()
    if not re.match(r"^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$", cleaned):
        return min(score, 0.3), f"does not look like a valid IBAN"
    return score, ""
```

These validators:
- Can only **lower** the score, never raise it (conservative)
- Catch hallucinated values (an IBAN that doesn't match the format)
- Catch format errors (currency code "Euro" instead of "EUR")
- Enforce cross-field consistency (total ≠ sum of line items → lower confidence)

The final score per field = `min(llm_score, validator_score)`.

---

## Document-level confidence

The overall document confidence is the average of all field confidence scores:

```python
def overall_confidence(self) -> float:
    return sum(f.score for f in self.field_confidence) / len(self.field_confidence)
```

This drives the routing decision:
- `overall >= 0.75` → auto-approve → status: `extracted`
- `overall < 0.75` → route to human review → status: `needs_review`

The threshold (`CONFIDENCE_THRESHOLD=0.75`) is configurable in `.env`.

---

## What this lesson teaches you

The pattern of "LLM output → deterministic post-processing" is fundamental.
LLMs are good at fuzzy matching and understanding context; they're bad at
format validation and arithmetic. Always combine both.

---

## Exercise

```bash
python lessons/04_confidence_scoring/exercise.py
```

The exercise demonstrates:
1. Raw LLM confidence scores on a real extraction
2. Running deterministic validators that adjust scores
3. The difference between before and after validation
4. What gets routed to the review queue

---

## Key concepts from `src/docint/extraction/`

- [confidence.py](../../src/docint/extraction/confidence.py) — validators and score adjustment
- [schemas/base.py](../../src/docint/extraction/schemas/base.py) — `FieldConfidence` and `overall_confidence()`

---

## Next

→ [Lesson 05 — Human Review Queue](../05_review_queue/README.md)
