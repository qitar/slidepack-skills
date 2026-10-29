# SlidePack API workflow

Source: https://docs.slidepack.io/md/reference/endpoints.md (also in llms-full.txt).
Base URL for SlidePack calls: `https://slidepack.io`.

SlidePack renders a PPTX from a zip (`template.pptx` + `data.json` + assets)
through a fixed **4-step sequence**. Each step needs output from the previous.

```
1. Create session   → POST /sessions                      (auth) → uuid + S3 upload params
2. Upload zip to S3  → POST {upload.action}               (no auth, multipart)
3. Render            → POST /sessions/{uuid}/render        (auth) → render_succeeded, download_url
4. Download          → GET  {download_url}
```

## 1. Create a session

```
POST https://slidepack.io/sessions
Authorization: Bearer {API_TOKEN}
```
Response contains two objects: `session` (with `uuid` etc.) and `upload`
(`{ action, method, enctype, params: { ... } }`). The session id is
`session.uuid`. `upload.method` (`POST`) and `upload.enctype`
(`multipart/form-data`) tell you how to send the upload in step 2.

Creating a session **deletes any existing un-rendered session** (one live
un-rendered session per account).

## 2. Upload the zip to S3

`POST` to `upload.action` as `multipart/form-data`. Include **every**
`upload.params` key as a form field, in order, **then** the file last as `file`.

```python
upload = resp["upload"]               # resp = { "session": {...}, "upload": {...} }
params = dict(upload["params"])      # all S3 params first…
params["file"] = open("input.zip", "rb")   # …file LAST
r = requests.post(upload["action"], files=params)   # expect 204 No Content
```
Missing/modified S3 params → `403 Forbidden` from AWS.

## 3. Render

```
POST https://slidepack.io/sessions/{uuid}/render
Authorization: Bearer {API_TOKEN}
```
Response shape mirrors create-session: `{ session: {...}, download_url }`,
where `download_url` is a top-level sibling of `session`.

A failed render still returns **HTTP 200**. Always check `session.render_succeeded`:
- `session.render_succeeded == true` → use the top-level `download_url`.
- `session.render_succeeded == false` → read `session.render_message` for the error.

## 4. Download

`GET {download_url}` from the render response. The URL expires in **5 minutes**.
To get a fresh one: `POST /sessions/{uuid}/download_url`.

## Expiry limits

| Resource | TTL | When expired |
|---|---|---|
| Session | 24 hours | create a new session |
| S3 upload params | 1 hour | create a new session |
| Download URL | 5 minutes | `POST /sessions/{uuid}/download_url` |

Don't cache S3 params across many renders — create a fresh session per render.

## Zip structure

`template.pptx` and `data.json` must be at the **zip root** (exact filenames).
Asset files go at the relative paths referenced in `data.json`.

```
input.zip
├── template.pptx        ← required, exact name
├── data.json            ← required, exact name
├── images/hero.png      ← only if referenced in data.json
└── videos/promo.mp4     ← only if referenced in data.json
```

```bash
zip input.zip template.pptx data.json            # minimal
zip -r input.zip template.pptx data.json images/ videos/   # with assets
```

## Session object fields

```
uuid                string        session id
created_at          string        UTC timestamp. Docs show ISO 8601
                                  ("2020-08-13T13:14:32.000000Z") but the live API
                                  has returned "YYYY-MM-DD HH:MM:SS" — parse defensively.
rendered_at         string|null
render_succeeded    boolean|null  ← check before downloading
render_slide_count  integer|null
render_message      string|null   error detail when render_succeeded is false
```
