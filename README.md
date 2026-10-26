# Shelf-Check

The existing three-panel shelf-checking demo, with benchmark-informed model selection
and a real API recognition path. Inventory and planograms remain simulated.

## Run locally

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm --prefix app ci
./run_demo.sh
```

Open http://127.0.0.1:8000. The homepage accepts one JPG, PNG or WebP shelf photo
up to 20 MB / 40 megapixels. Choose the shelf planogram and select **Analyze shelf**.
After upload, the browser routes to `/analysis?bay=...&upload=...` and starts
recognition when the service is configured. **Explore a sample** opens the existing
three-panel analysis with saved benchmark readings, without requiring credentials.

For live recognition, copy `server/.env.example` to `server/.env`, set
`ANTHROPIC_API_KEY` and optionally `GEMINI_API_KEY`, and restart the server.
Submitting a new photo starts a paid scan when configured; loading the homepage
or a saved sample makes no model calls. On sample analysis, select **Run a new
analysis** to rescan the sample. Unsupported proxy/OpenAI credentials are not
advertised as working integrations. Model names are kept in server-side metadata
and audit records, and are hidden throughout the user-facing interface.

Straive LLM Foundry SSO and inference are not yet integrated into the app. The
manual connectivity probe at `qa/probe_foundry_vision.py` reads a token through a
hidden prompt and sends exactly one request without retries. Use
`.venv/bin/python qa/probe_foundry_vision.py --hi` for a text-only check, or omit
`--hi` to send the included public benchmark crop. Run it only when a gateway
request is intended. Tokens are never saved; local result reports are ignored.
The latest local text and image attempts both timed out before any HTTP response,
so token validity, vision support and access from the office network remain
unverified.

Uploads preserve the original image bytes and EXIF orientation. The server validates
the decoded image, not its filename or declared content type. Files and metadata
are stored locally under ignored `server/uploads/<upload_id>/`, outside the frontend
bundle. Completed results are saved per upload and selected shelf so browser refresh
restores the same photo and result without another paid scan. New uploads always
use the high-accuracy default for unknown shelf difficulty; the sample bay's
difficulty does not determine how a new photograph is read. Uploaded photos never
use saved sample recognition as a fallback. Failed or unavailable recognition shows
the uploaded image and an explicit pending/error state, without invented results.

## Model and image policy

Source: [Atharva Sharma's Bookshelf Benchmark](https://atharva-729.github.io/bookshelf-benchmark/).

| Shelf | Default measured setup | Saved reply source |
| --- | --- | --- |
| Easy / tidy | Gemini 3.8 Flash, extended/high thinking | Experiment 1, run 2 |
| Medium | Claude Opus 5.5, high effort | Experiment 1, run 2 |
| Hard / crowded | Claude Opus 5.5, high effort | Experiment 2, one photo per chat |

Flash had the highest pooled easy-shelf F1 in both runs; Opus high had the highest
overall F1 in run 2. This is a policy by difficulty, not per-photo selection of the
best-looking trial. Live easy-shelf scans fall back to Opus high if only Anthropic
is configured. A medium/hard scan requires Anthropic; it never silently substitutes
Flash or a replay when live recognition fails. Provider model identifiers are
`claude-opus-5-5` and `gemini-3.8-flash`; returned model identity is checked.

Live recognition:

1. Correct EXIF orientation to the same frame the browser displays.
2. Cover the full image with native-resolution tiles up to 1,400 px per side and
   20% overlap. Use lossless PNG crop encoding, with no upscaling or whole-photo
   shrinking. A 24 MP photo typically needs 20 tiles / 40 model calls and can take
   many minutes. Tiles are sequential to bound memory and rate-limit pressure.
3. Read each crop with high effort/thinking and structured JSON output. Original
   script and volume numbers are preserved; unreadable authors stay null.
4. Independently reread each crop rotated 90 degrees clockwise, without sending
   previous candidate titles. Map its coordinates back to the upright photograph.
5. Deduplicate normalized exact titles across overlap/copies. Only two clear
   readings of the same title at an overlapping location can be labelled agreed;
   conflicting titles remain review items. Agreement is not calibrated confidence.
6. Compare the readings to the catalogue in deterministic code. Recognition calls
   never receive the catalogue, planted exceptions or frozen ground truth.

Short franchise labels, differing volume numbers, ambiguous catalogue matches and
conflicting authors receive conservative handling. Matching is one-to-one across
the full catalogue. Bay-specific stable inventory IDs prevent duplicate titles
from overwriting each other's records. Identical titles allocated to several bays
can match their valid local allocation without generating a false move task.
An unrecognized expected title becomes **presence unconfirmed**,
not a confirmed stockout or phantom inventory. Recognition counts unique titles,
not copies. Reviewing tasks changes only this browser session; it neither writes
inventory nor artificially increases the observed title-match percentage.

Live progress is streamed from actual work, with heartbeats and cancellation.
Transient 429/502/503/529 responses have bounded retries; bad credentials, invalid
JSON, out-of-bounds coordinates, refusals, model substitutions and truncated replies
fail explicitly. Partial output is never accepted as a completed scan.

## Evidence and limitations

The report's Opus high six-photo run 2 had precision **0.968**, recall **0.817** and
F1 **0.886**. Those are historical chat-app scores, not scores for this API harness.
The report proposed, but did not implement or measure, the crop/verification
harness. The 1,400 px tile size, 20% overlap and independent rotated rereading are
engineering choices to test, not experimentally proven optima. Only six benchmark
photos and at most two runs were available. Human checks remain necessary.

Saved predictions and their source paths are in `pipeline/benchmark_sources.json`.
Regenerate replay assets with:

```sh
.venv/bin/python pipeline/run_replay_scans.py
```

Replays contain saved model predictions, not new inference. Their book positions
are null and outlines are disabled; the benchmark did not annotate title positions.
Unmeasured confidence, per-photo latency, tokens and cost are null. Live outlines
are model estimates, not hand-labelled boxes. Live latency and provider-reported
tokens are measured; unmeasured cost remains null.

Each live run writes an ignored `server/runs/<run_id>.json` audit with the image
hash, profile, crop coordinates, returned model identities, raw visible responses,
usage and final merge. It contains no API keys, full images or hidden reasoning.
Failed/cancelled runs are labelled. The app does not claim improved accuracy until
fresh live outputs have been evaluated against the frozen answer key.

```sh
.venv/bin/python -m pytest
npm --prefix app run build
node --experimental-strip-types --test qa/test_scan_stream.mjs
```

API contract tests use mocked providers; they do not establish real-world model
accuracy. Optional data-generation/scorer checks need the source benchmark checkout
at `reference/bookshelf-benchmark`; the shipped app and replay generator do not.
Browser checks are in `qa/check_accuracy_ui.cjs` (requires Playwright; accepts
`PLAYWRIGHT_MODULE`, `CHROME_PATH` and `SHELF_CHECK_URL`). They exercise all bays,
zoom, review/reset, responsive layouts and mocked live completion/failure/cancellation.
`qa/check_upload_ui.cjs` additionally checks the real local upload, drag/drop,
validation, navigation and refresh, plus mocked recognition completion, cancellation,
saved-result restoration, error handling and model-name hiding. Browser tests block
real recognition requests and do not incur provider charges.
