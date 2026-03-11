# Lesson 05 — Human Review Queue

**Goal:** Build the quality gate that makes automation trustworthy.

---

## Why a review queue is non-negotiable

Every document intelligence system will encounter:
- Documents with unusual layouts it hasn't seen before
- Amounts that are ambiguous ("approx. EUR 5,000–6,000")
- Fields that partially overlap on the page
- Vendor names that match multiple entries in your database

For these, the right answer is not to reject the document or silently produce a wrong value —
it's to surface it to a human and make correction easy.

The review queue is what separates a useful system from an unreliable one.

---

## State machine

```
         upload
            ↓
         pending
            ↓
        processing
       ↙         ↘
  extracted    needs_review
       ↘         ↙
        approved
                ↘
             rejected
```

`extracted` = high-confidence, auto-approved, no human needed
`needs_review` = confidence below threshold, routed to queue
`approved` = human confirmed the extraction (possibly with corrections)
`rejected` = extraction was too wrong to fix, document needs manual processing

---

## Priority scoring

Not all uncertain documents are equally urgent. Priority = `1 - confidence`.

In production you'd extend this with:
- **Document value** — a EUR 500,000 invoice needs faster review than a EUR 50 receipt
- **Customer SLA** — some customers have strict processing windows
- **Document age** — older pending items escalate

For now: `priority_score = 1.0 - overall_confidence`. A 0.3 confidence document
gets a 0.7 priority score and jumps to the front of the queue.

---

## The feedback loop

When a reviewer corrects an extraction, those corrections are stored in `review_items.corrections_json`:

```json
{
  "total_amount": {"old": "13685.00", "new": "13640.00"},
  "currency": {"old": "USD", "new": "EUR"}
}
```

This creates a dataset of (document, wrong extraction, correct extraction) triples.
Over time, you can:
1. Analyze patterns — which fields fail most often? For which document layouts?
2. Use corrections to improve prompts (few-shot examples)
3. Fine-tune a model if you have enough corrections

---

## Exercise

```bash
python lessons/05_review_queue/exercise.py
```

The exercise builds a simple CLI reviewer that:
1. Shows queued documents with their extracted data highlighted for low-confidence fields
2. Accepts approve / reject / correct decisions
3. Stores corrections in the database
4. Prints a summary of the corrections made

---

## Key concepts

- [pipeline/review_queue.py](../../src/docint/pipeline/review_queue.py) — `ReviewTask`, `render_review_task`, `compute_corrections`
- [storage/repository.py](../../src/docint/storage/repository.py) — `get_pending_review_items`, `approve_review_item`, `reject_review_item`

---

## Next

→ [Lesson 06 — Production API](../06_production_api/README.md)
