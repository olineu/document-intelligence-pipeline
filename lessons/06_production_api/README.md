# Lesson 06 — Production API

**Goal:** Expose the pipeline as a service and understand the key architectural patterns.

---

## The upload/poll pattern

Document extraction is slow (multiple seconds per document for the LLM call).
You cannot block an HTTP request for that long — clients will time out.

The solution: **decouple upload from processing**.

```
Client                    API                      Background
  |                        |                            |
  |--- POST /upload -----→ |                            |
  |                        | save file                  |
  |                        | create DB record           |
  |                        | start background task ----→|
  |←-- 200 {id: "abc"} --- |                            |
  |                        |                            | parsing...
  |                        |                            | extracting...
  |--- GET /documents/abc →|                            |
  |←-- {status: "pending"} |                            |
  |                        |                            | storing...
  |--- GET /documents/abc →|                            |
  |←-- {status: "extracted", data: {...}} ←------------ |
```

The client gets an ID immediately. It polls `/documents/{id}` until `status` is not `pending`.
In production, you'd use webhooks instead of polling — push a callback when done.

---

## Why FastAPI's BackgroundTasks

FastAPI has a built-in `BackgroundTasks` system. The pipeline runs after the response
is sent. Simple and sufficient for moderate volume.

For high volume: replace `BackgroundTasks` with a proper job queue (Celery + Redis,
or ARQ). The interface stays the same — just swap the task dispatch mechanism.

---

## Session management

Each background task gets its own database session:

```python
async with request.app.state.session_factory() as session:
    await pipeline.process(session=session, ...)
```

This is important: sessions are not thread-safe and should not be shared across tasks.
The `async_sessionmaker` creates a fresh session per call.

---

## Exercise

```bash
# Start the full stack
docker-compose up

# In another terminal — upload a document
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@sample_documents/invoice_sample.pdf" \
  -F "schema_type=invoice"

# Poll for status
curl http://localhost:8000/documents/{document_id}

# Check the review queue
curl http://localhost:8000/review/queue

# Approve a review item
curl -X POST http://localhost:8000/review/{review_item_id}/approve \
  -H "Content-Type: application/json" \
  -d '{"reviewed_by": "your-name"}'
```

---

## Key concepts from `src/docint/api/`

- [main.py](../../src/docint/api/main.py) — app startup, lifespan, route registration
- [routes/documents.py](../../src/docint/api/routes/documents.py) — upload + poll endpoints
- [routes/review.py](../../src/docint/api/routes/review.py) — review queue endpoints

---

## What to explore next

Once the API is running:
1. Look at the FastAPI interactive docs at `http://localhost:8000/docs`
2. Submit the same document twice — observe that two separate records are created
3. Submit a messy document — watch it land in the review queue
4. Approve it via the API — observe the status change
5. Add a webhook route that calls an external URL when extraction completes
