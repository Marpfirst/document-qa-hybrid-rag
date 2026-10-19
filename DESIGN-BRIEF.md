# Design Brief

Material for working on the UI: what the product is, who uses it, and what must
not change.

## Product

Question answering over internal documents. Upload an SOP or handbook, ask about
its contents, and every answer points back to the section it came from.

What it sells is not fluent answers but traceability.

## Two opposing audiences

| User | Needs |
|---|---|
| Employee / HR | Fast answers, checkable evidence, plain language |
| Recruiter / engineer | Proof this is not a ChatGPT wrapper: trace panel, scores, citations |
| LinkedIn visitor | Can try it without preparing anything |

The first wants simple, the second wants to see the engine. Solve it with
hierarchy, not compromise: the answer dominates, the evidence is within reach,
and the technical detail can be opened.

## Flow

```
Arrive → upload PDF/DOCX or use the sample → wait for indexing
→ ask → trace panel fills in → answer streams → click a citation
```

The trace panel fills in before the answer appears. That is the most
distinctive moment of the product: retrieval finishes before the model speaks,
and that is shown.

## States that need a design

| State | Notes |
|---|---|
| Cold start ~30 seconds | Must be explicit; a plain spinner reads as broken |
| Server down | Mention `localhost:8000` |
| No documents yet | Chat input disabled |
| Indexing | 4 stages: queued, reading, indexing, ready |
| 3-document limit | Uploader disabled, with the reason |
| Nothing asked yet | Trace panel holds an explanation, not empty space |
| Answer not in the documents | A feature, not a failure |
| Citation rejected by the validator | Show the number |
| Failover to Groq | Mark it in the answer footer |
| OCR document | OCR badge + a warning that numbers may be wrong |

## Tone

The UI is bilingual (Indonesian and English). The Indonesian copy uses the
informal "kamu". Calm and factual. No emoji.

Technical terms in the trace panel (dense, sparse, RRF, reranker) stay as they
are: they are the part technical reviewers judge.

Short sentences. Do not explain what is already clear from the screen.

## Visual system

Two accents, deliberately kept apart:

- **indigo**: the product (brand, buttons, active state)
- **green**: grounding (citations and retrieval evidence)

A citation must never read as an ordinary button: the whole promise of this
product is an answer that can be traced.

Tokens live in `web/app/globals.css`, with a dark variant. The theme follows the
OS and can be overridden with the button in the header.

## Must not be violated

- The trace panel stays, and keeps showing raw scores. Hiding it for tidiness
  throws away the reason this project is not an ordinary "chat with PDF".
- Citations are clickable and show the original quotation, not just a number.
- The disclaimer and the 24-hour retention notice stay visible.
- Both themes keep working.
- No heavy UI dependencies.

## Measures of success

- A visitor with no document can see an answer within 15 seconds without
  reading instructions
- A technical reviewer finds evidence of hybrid retrieval without scrolling
- Score comparison is visible at a glance, not read one by one
- A phone screen is still useful: the retrieval trace is reachable
