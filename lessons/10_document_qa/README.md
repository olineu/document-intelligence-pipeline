# Lesson 10 — Document Q&A with Source Citations

**Goal:** Go beyond extraction (pulling known fields) to answering arbitrary questions about documents — with citations that make answers verifiable.

---

## Extraction vs. Q&A

Everything up to Lesson 09 is **extraction**: you define the fields you want, and the pipeline finds them.
Extraction works when you know what you're looking for.

**Q&A** is different: the question is open-ended.
- "What are the late payment penalties in this contract?"
- "Which line items were for professional services?"
- "Is there a limitation of liability clause, and if so, what is the cap?"

You can't define a Pydantic schema for these — the questions vary per document and per user.

---

## Why citations are non-negotiable

If a system says "the late payment penalty is 2% per month" and that's wrong,
the business consequence is real (incorrect payment, contract dispute, legal exposure).

Without a citation, the user has no way to verify the answer. The system is asking to be trusted.

The correct pattern: **cite-or-abstain**.
- If the answer is in the document, answer it and cite the exact passage
- If the answer is not clearly in the document, say so — don't guess

```
Q: What is the late payment penalty?

A: "A penalty of 2% per month shall apply to overdue invoices,
    not to exceed a maximum of 10% of the invoice total."

    Source: Section 4.2 — Payment Terms, paragraph 3
```

---

## The RAG architecture for document Q&A

```
Document
    ↓
[Parser → Dockling]          ← Lesson 08: semantic structure
    ↓
[Chunker]                    ← split into retrievable passages
    ↓
[Embedder] → [Vector Store]  ← index chunks by semantic meaning
    ↓
User Question
    ↓
[Retriever]                  ← find the most relevant chunks
    ↓
[Answer Generator]           ← answer using retrieved chunks only
    ↓
Answer + Citations (chunk references)
```

This is RAG (Retrieval-Augmented Generation) applied to a single document.
The vector store is scoped to the document, not a corpus.

---

## Trustworthy RAG: when to abstain

The `trustworthy-rag` project introduces **Trustworthy Language Models (TLM)** —
a technique that adds calibrated confidence to RAG answers.

Even without TLM, you can implement a basic version:
1. Ask the model to rate its own confidence in the answer
2. Ask the model to quote the exact passage that supports the answer
3. If the model can't find a supporting passage, it must say "not found in document"

System prompt principle:
> "Answer only from the provided passages. If the answer is not clearly present,
> respond with 'This information is not found in the provided document sections.'
> Never speculate or infer beyond what is explicitly stated."

---

## Exercise

```bash
python lessons/10_document_qa/exercise.py
```

The exercise:
1. Chunks a sample contract into passages
2. Embeds passages and builds a simple in-memory index
3. Answers questions with retrieved context + citations
4. Demonstrates the abstain behaviour when the answer isn't in the document

---

## Key concepts

- RAG on a single document = per-document Q&A (vs. corpus-wide search)
- Dockling chunks are better than character-split chunks (section boundaries preserved)
- Citation = chunk ID + passage text — always return both with the answer
- Abstain > hallucinate — design the prompt to make "not found" a valid, expected answer
- Trustworthy RAG: confidence score on the answer, not just the retrieval

---

## Next steps after this lesson

You now have a complete document intelligence platform:
- Parse any format (Lessons 01, 07, 08)
- Extract structured fields (Lessons 02–04)
- Route uncertain docs to review (Lesson 05)
- Serve via API (Lesson 06)
- Handle complex multi-document validation (Lesson 09)
- Answer arbitrary questions with citations (Lesson 10)

The next frontier: connect it to a real-time data source (ERP, CRM) for cross-document
validation at scale. See `process-agent` in the project roadmap.
