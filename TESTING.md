# Test Guide

## Where the data comes from

There is no dataset to download. The app is empty until you upload something.

| | Contents | Location | In git |
|---|---|---|---|
| Sample document | 1 fictional SOP (in Indonesian) | `web/public/contoh-sop-cuti.docx` | yes |
| Your documents | whatever you upload | `api/data/qdrant/` | no |

The sample document deliberately has nested headings to exercise the chunking.
The facts inside it are the answer key:

- annual leave is **12 working days**; more than 5 days needs the **Division Head**
- long leave is **30 calendar days** after **6 years**
- maternity leave is **3 months**
- being late by **more than 30 minutes** = minor violation

If the bot answers differently from these, there is a bug.

Accepted formats: **PDF with a text layer** and **DOCX**. Cap of 5 MB per file,
3 files, 100 pages. Scanned PDFs are skipped with a message saying how many
pages were skipped.

Data disappears when you delete it manually, after 24 hours, or if the
`api/data/` folder is removed.

---

## Running

```bash
cp .env.example .env
```

Fill in `GEMINI_API_KEY` and `SESSION_SECRET` in `.env`, not in `.env.example`.

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Two terminals:

```bash
cd api && uv sync --extra dev
uv run uvicorn app.main:app --reload
```

```bash
cd web && npm install && npm run dev
```

Check the backend:

```bash
curl http://localhost:8000/health
```

It should return `"status":"ok"` with `llm_provider` filled in.

The first download is about 500 MB (the embedding and reranker models run
locally). The first request is also slow, about 30 seconds, while the models
load into memory.

---

## Testing in the browser

1. Click **Use the sample SOP**
2. Wait for status `ready`: **11 chunks**
3. Click one of the example questions

What to check:

| Check | Expected |
|---|---|
| Trace panel | Filled in before the answer text appears |
| Dense and sparse scores | Both non-zero |
| Number chips in the answer | Clickable; the popover shows the heading path + the quoted passage |
| Answer text | No raw `[doc:1]` visible |

### Four scenarios

The sample document is in Indonesian, so the questions are asked in Indonesian.

| Ask | Correct answer | Tests |
|---|---|---|
| Berapa hari cuti tahunan? (How many days of annual leave?) | 12 working days | Basic retrieval |
| Berapa cuti tahunan dan siapa penyetuju kalau lebih dari 5 hari? (How much annual leave, and who approves more than 5 days?) | 12 days + Division Head | Multiple citations |
| **Berapa denda kalau terlambat 10 menit? (What is the fine for being 10 minutes late?)** | **not in the document** | **Grounding** |
| Apa aturan cuti besar? (What are the long-leave rules?) | 30 days, 6 years, once | Specific section |

The third scenario is the most important. The document mentions *30 minutes*,
never a *fine* and never *10 minutes*. The bot must admit it does not know.

### Isolation

Open an incognito window and ask anything. It must say there are no documents
yet: a new cookie means a new workspace.

---

## Testing from the terminal

```bash
curl -c jar.txt -X POST -F "file=@web/public/contoh-sop-cuti.docx" \
  http://localhost:8000/documents

curl -b jar.txt http://localhost:8000/documents     # wait for status ready

curl -N -b jar.txt -X POST http://localhost:8000/chat/stream \
  -H 'content-type: application/json' \
  -d '{"message":"Berapa hari cuti tahunan?"}'
```

`-c` saves the session cookie and `-b` sends it. Without them each command gets
a fresh workspace and the document seems to vanish. `-N` turns off buffering so
the stream is visible.

The correct event order is `retrieval` → `delta` → `citation` → `done`. In the
`citation` event look for `"precision":1.0` and `"rejected":0`.

Isolation:

```bash
curl -N -c other.txt -b other.txt -X POST http://localhost:8000/chat/stream \
  -H 'content-type: application/json' -d '{"message":"Berapa hari cuti tahunan?"}'
```

A different cookie jar must answer that there are no documents.

---

## Automated tests

```bash
cd api && uv run pytest -q      # 45 passed
```

| File | Covers |
|---|---|
| `test_isolation.py` | Workspace A's documents do not leak into B |
| `test_citation_guard.py` | A fake `[doc:99]` is dropped; the `[doc:1, doc:2]` variant is parsed |
| `test_router.py` | Page verdicts: digital / scanned / blank / broken |
| `test_parsers.py` | Heading paths and offsets are accurate |
| `test_chunk.py` | Splits at section boundaries |

Check that your keys are being read:

```bash
cd api && uv run python -c "
from app.config import settings
print('gemini:', bool(settings.gemini_api_key))
print('groq  :', bool(settings.groq_api_key))
print('secret:', settings.session_secret != 'dev-only-change-me')
"
```

---

## When you get stuck

| Symptom | Fix |
|---|---|
| `Tidak ada penyedia LLM yang terkonfigurasi` (no LLM provider configured) | `.env` is not being read. Run the key check above |
| `404 model is no longer available` | Google retired the old model. See the list-models command in the README |
| Always "no documents" | The cookie is not being carried. Use `-b jar.txt` and do not block cookies |
| Sparse score always 0 | Delete `api/data/` and upload again |
| `429` during chat | Gemini quota exhausted. With a `GROQ_API_KEY` it fails over automatically |
| Frontend cannot reach the backend | `CORS_ORIGINS` must include `http://localhost:3000` |
| `Storage folder already accessed` | Embedded Qdrant allows only one process. Stop the other instance |
| Hydration mismatch mentioning `bis_register` | A browser extension, not an app bug. Already handled |

Full reset:

```bash
rm -rf api/data
```

---

## Checklist

- [ ] `/health` returns `status: ok`
- [ ] Sample document is `ready`, 11 chunks
- [ ] Trace panel appears before the answer text
- [ ] Dense and sparse scores are non-zero
- [ ] Citation chips are clickable
- [ ] No raw `[doc:N]` in answers
- [ ] The fine question is answered with "not in the document"
- [ ] Incognito does not see another session's documents
- [ ] `uv run pytest -q` → 45 passed
- [ ] `cd web && npm run build` succeeds
