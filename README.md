# Shelf Check

A local three-panel bookshelf analysis app with saved benchmark samples and optional
live recognition through a user's Straive LLM Foundry sign-in. Planograms and
inventory remain simulated.

## Run locally on Windows

Requirements: Python 3.13 and Node.js 22.12 or newer.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm --prefix app ci
npm --prefix app run build
.\run_demo.ps1
```

Open http://127.0.0.1:8000. If that port is already in use, leave the other
process untouched and start this app on another port:

```powershell
$env:PORT = "8001"
.\run_demo.ps1
```

To stop the app, press **Ctrl+C** in the server terminal. To restart it, run
`.\run_demo.ps1` again. To run the API directly without the launcher:

```powershell
.\.venv\Scripts\python.exe -m uvicorn server.main:app --host 127.0.0.1 --port 8000
```

## Run locally on macOS or Linux

Requirements: Python 3.13 and Node.js 22.12 or newer.

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm --prefix app ci
npm --prefix app run build
./run_demo.sh
```

Open http://127.0.0.1:8000. Stop with **Ctrl+C** and restart with
`./run_demo.sh`. Set `PORT=8001` before running the launcher if port 8000 is busy.

The homepage accepts one JPG, PNG or WebP photo up to 20 MB / 40 megapixels.
Choose a shelf and select **Analyze shelf**. The actual uploaded image is retained
on the analysis page, including when sign-in or inference is unavailable. Uploads
wait for an explicit **Analyze photo** click; refreshing the page does not start
or repeat inference. Every manual scan attempt starts from the first photo
section and makes fresh gateway requests. Results from a failed or previous
attempt are never reused.
**Explore a sample** opens saved recognition data without requiring a sign-in or
making a model request.

## Straive sign-in and inference

Use **Sign in** in the top-right status area. The app checks the user session at
`https://llmfoundry.straivedemo.com/token` and redirects through that host's
`/login?next=...` flow. The separate inference route is
`https://llmfoundry.straive.com/gemini/v1beta/models/gemini-3.1-pro-preview:streamGenerateContent?alt=sse`.
The distinct authentication and inference hosts follow the supplied Straive app
sign-in guide and gateway endpoint.

Once signed in, the app holds the returned token only in transient browser memory.
For each live scan it sends the token in an HTTPS `Authorization` header to this
local backend, which immediately uses it for the gateway request. Tokens are not
put in URLs, browser persistent storage, uploaded-image metadata, saved analyses,
audit files, or application logs. The app does not use personal Anthropic, Gemini,
or other provider API keys; no secret configuration is needed.

Live inference uses only the supplied Gemini 3.1 Pro Preview endpoint and the
non-secret Foundry project label `llmproxy-playground`. Saved benchmark responses
are separate from live inference. The live model and crop/verification harness have
not been measured against the benchmark and no accuracy score is claimed for them.
The gateway may reject a valid sign-in if the account lacks access to this model or
project; the app reports authentication and permission failures separately and
never substitutes saved sample results.

The browser must be able to reach the sign-in host, and this computer's backend
must be able to reach the inference host over verified TLS. The sign-in endpoint
was reachable cross-origin from the local browser and returned an empty session
when tested signed out. A company login, inference request, proxy requirement,
certificate requirement, and acceptance of a localhost login return URL have not
yet been verified. The Foundry CORS guide notes that browser third-party-cookie
restrictions can prevent credentialed session checks; allow cookies only as
approved by company policy. The app does not disable TLS verification or bypass
network controls. If sign-in or inference fails, check the office-approved proxy
and certificate settings with IT; do not paste tokens into chat or source files.

For an optional one-request diagnostic, the probe prompts for a token without
echoing it and never saves it. Use the venv Python:

```powershell
.\.venv\Scripts\python.exe qa\probe_foundry_vision.py --hi
.\.venv\Scripts\python.exe qa\probe_foundry_vision.py
```

Run the image request only after the text request succeeds. It sends one request
without retries, using the included public shelf crop; its ignored report contains
the status, completion reason, and returned text/titles but not the token.

## Image processing and result behavior

Uploads preserve original image bytes and EXIF orientation. The server validates
the decoded image, not its name or declared media type. Files are stored locally
under ignored `server/uploads/<upload_id>/`, outside the frontend bundle. Completed
results are saved per upload and shelf so refresh restores the same photo and
result without another inference request. A failed rescan leaves the prior
completed result unchanged. Uploaded photos are never matched to saved sample
recognition as a fallback. Without a usable sign-in, the photo remains visible in
an explicit pending state.

Live recognition:

1. Correct EXIF orientation to the same frame the browser displays.
2. Cover the full image with native-resolution tiles up to 1,400 px per side and
   20% overlap. Use lossless PNG crop encoding, with no upscaling or whole-photo
   shrinking. A 24 MP photo typically needs 20 tiles / 40 model calls and can take
   many minutes. A full scan starts with up to 40 Gemini requests; oversized
   sections may require additional split-crop requests. Tiles are sequential to
   bound memory and rate-limit pressure.
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
Each gateway request is attempted once; authentication failures, permission
failures, rate limits, invalid JSON, model substitutions, provider errors, and
truncated replies fail explicitly. Individual malformed book entries are omitted
and disclosed when the rest of a section is valid; partial output is never
accepted as a completed model response. When a reading or verification crop hits
the output-token limit, it is split into four overlapping crops, with a second
split level available for still-dense crops. Splits happen within that scan
attempt only; a manual retry starts over and makes fresh requests. Fractional,
pixel, percentage, and 0–1000 coordinate formats are normalized before box
validation; a crop with entirely invalid boxes is split rather than aborting
immediately. Each request has a four-minute deadline.

## Evidence and limitations

The cited report's Opus high six-photo run 2 had precision **0.968**, recall
**0.817** and F1 **0.886**. Those are historical chat-app scores, not scores for
this app, the current gateway model, or its crop/verification harness. The report
proposed, but did not implement or measure, this harness. The 1,400 px tile size,
20% overlap and independent rotated rereading are engineering choices to test, not
experimentally proven optima. Only six benchmark photos and at most two runs were
available. Human checks remain necessary.

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
usage and final merge. It contains no session tokens, full images or hidden
reasoning. Failed/cancelled runs are labelled. The app does not claim measured
accuracy until fresh live outputs have been evaluated against the frozen answer key.

```sh
.venv/bin/python -m pytest
npm --prefix app run build
node --experimental-strip-types --test qa/test_scan_stream.mjs
node --experimental-strip-types --test qa/test_foundry_auth.mjs
```

On Windows, run the Python suite with
`.\.venv\Scripts\python.exe -m pytest`; the npm and Node commands are the same.

API contract tests mock gateway responses and auth; they do not establish live
inference access or real-world model accuracy. Optional data-generation/scorer checks need the source benchmark checkout
at `reference/bookshelf-benchmark`; the shipped app and replay generator do not.
Browser checks are in `qa/check_accuracy_ui.cjs` (requires Playwright; accepts
`PLAYWRIGHT_MODULE`, `CHROME_PATH` and `SHELF_CHECK_URL`). They exercise all bays,
zoom, review/reset, responsive layouts and mocked live completion/failure/cancellation.
`qa/check_upload_ui.cjs` additionally checks the real local upload, drag/drop,
validation, navigation and refresh, plus mocked recognition completion, cancellation,
saved-result restoration, error handling and model-name hiding. Browser tests block
real recognition requests and do not incur provider charges.
