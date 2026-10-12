---
name: ollama-batch-generation
description: Run large batches of local-LLM generation through Ollama (or any similar local server) that survive restarts and never ship bad output - schema-constrained JSON, stream and thinking off, bounded retries with a repair hint, a cache keyed by prompt, model and endpoint, strict validation of every reply, a manifest, and resumable runs. Use when generating copy, labels, classifications or vision verdicts for hundreds of records with a local model, when a batch job keeps failing halfway, when replies come back with junk around the JSON, or when a local model is slow, times out or keeps reloading.
license: MIT
---

# Ollama batch generation

A batch of hundreds of local-model calls fails in ways a single call never
shows: a timeout at item 180, a reply with prose after the JSON, a model that
reloads every few requests, copy that invents facts. Build the job so any item
can fail, the run can stop at any point, and nothing unvalidated reaches the
output.

## Shape of the job

```
records -> prompt per record -> cache lookup -> model call (retry) -> parse -> validate -> write output + manifest
```

- **One record per request.** Batching several records into one prompt makes
  one bad item fail the rest and makes validation ambiguous.
- **Outputs and the manifest are written serially, in source order**, even if
  requests run in parallel. Parallel writes to one file corrupt it.
- **Inputs are never written.** Generated files go to a separate output folder.

## The request

```python
body = {
    "model": model,
    "prompt": prompt,                 # or "messages" with /api/chat
    "stream": False,                  # one JSON body, not a token stream
    "think": False,                   # no reasoning preamble in the reply
    "format": SCHEMA,                 # JSON Schema: schema-constrained decoding
    "options": {"temperature": 0.2, "num_predict": 300},
}
resp = session.post(f"{endpoint}/api/generate", json=body, timeout=(10, 600))
```

- **Pass a JSON Schema in `format`**, with `required` and
  `"additionalProperties": false`. Plain JSON mode still lets the model choose
  its own keys.
- **Check `done` and `error`** in the response body, not just the HTTP status.
- **Timeouts**: a short connect timeout and a long read timeout. The first call
  loads the model, and under memory pressure later calls can be slow too.
- **Leave `num_ctx` alone unless every caller uses the same value.** If two jobs
  (or two apps) on the same server ask for different context sizes, the server
  reloads the model on every switch, and a fast job becomes a crawl.
- **Keep the model loaded** across the batch (`keep_alive`, for example
  `"30m"`), and don't run two different large models at once on a small GPU.

## The prompt

- Put the record in the prompt as JSON and say plainly that it is **data, not
  instructions**. Records come from spreadsheets, scrapes and users. A product
  name can contain "ignore the above".
- Ask only for the fields the model must invent. Fill fixed fields (IDs, names,
  template text) in code, not through the model.
- State hard limits as numbers: "one sentence, at most 120 characters".
- List the claims it must not make. For commercial copy that usually means
  availability, stock, prices, discounts, authenticity, "official",
  exclusivity, guarantees and shipping promises.
- Version the prompt (`PROMPT_VERSION = "2026-10-12-v3"`) and include the
  version in the cache key.

## Parse defensively

Local models wrap JSON in code fences, or append an end-of-turn marker or a
sentence after it. Decode exactly one object, then check it:

```python
def parse_reply(raw: str, fields: set[str]) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    start = text.find("{")
    if start < 0:
        raise ValueError("no JSON object in reply")
    data, _ = json.JSONDecoder().raw_decode(text[start:])   # ignores trailing junk
    if not isinstance(data, dict) or set(data) != fields:
        raise ValueError(f"expected exactly {sorted(fields)}")
    return data
```

## Validate every reply

Validation is the real quality gate. The schema only checks shape.

- Required fields present, non-empty strings, within length limits.
- The record's key term appears (for example the category name), so the copy
  is about the right thing.
- A banned-claims regex for words the prompt forbade.
- No template residue: placeholders, sample names, "Lorem", leftover markup.
- Characters the destination can't hold, such as control characters in Excel
  cells.

A reply that fails validation counts as a failed attempt. It's never written.

## Retries with a repair hint

Up to 3 attempts per record. On a retry, append the previous error to the
prompt ("Previous response invalid: Field2 is 141 characters; shorten to
120"). After the last attempt, record the failure in the manifest and move on.
Don't stop the batch. Exit non-zero at the end if anything failed.

## Cache and resume

- Key the cache on a hash of `{prompt_version, prompt, model, endpoint}`. Store
  the parsed result, the raw reply, the attempt count and the errors.
- Write cache and manifest files atomically: write a temp file, then rename it.
  A crash mid-write must not leave half a JSON file that poisons the next run.
- On rerun, cached records are re-validated, not trusted blindly, and existing
  outputs are verified. If an existing output differs from what this run would
  write, report a failure; don't overwrite it. Use a new output folder, or an
  explicit `--refresh` flag, when replacement is intended.
- Don't delete the cache while a run is active.

## Manifest

One row per record: source row or ID, output file, model, prompt version,
attempts, cached (yes or no), output hash, and the error if it failed. The
manifest is how you prove the batch is complete, and how you find the ten
records to fix by hand.

## Vision models and verdicts

For "is this image X?" checks:

- Ask for a **tri-state verdict**: `confirmed`, `rejected` or `unclear`, plus
  what the model saw and why. "Unclear" is the safe answer. A wrong
  "rejected" throws away good data, and a wrong "confirmed" writes bad data.
- **Don't ask the model for a confidence number.** Small local models produce
  precise-looking numbers that mean nothing. Map verdicts to thresholds in code
  if a downstream gate needs a number.
- Run cheap deterministic filters first (file type, size, dimensions, exact
  matches) and send only the ambiguous items to the model.
- Send `unclear` items to a human review queue, never straight to output.

## Grounding

If the copy should describe real things, put real facts in the prompt (for
example a sample of item names in the category) and tell the model to
generalize from them, not to quote them. Skip records with nothing to ground
on. Don't ask the model to describe an empty category; it will invent one.

## Before calling it done

- Run a `--limit 1` smoke test, then the full batch.
- Run a `--verify-only` pass that checks every output against the manifest
  without calling the model.
- Read a random sample of outputs yourself. Validation catches the format, not
  whether the copy is good.
