# Executive Agents — HTML Frontend (Vercel-ready)

A lightweight HTML/CSS/JavaScript interface connected to the existing Python CFO, CMO and COO agents.

## Deploy to Vercel

1. Push the **contents of this folder** to your Git repository (the `index.html`, `api/`, `base.py`, `data.py`, `cfo.py`, `cmo.py`, `coo.py`, and `vercel.json` must be at the project root).
2. Import that repository into Vercel and deploy. The static page is `index.html`; `api/ask.py` and `api/status.py` are Python serverless functions.
3. After deployment, open `https://YOUR-DOMAIN.vercel.app/api/status`. It should return JSON with `"ok": true`.
4. Test a question in the frontend. The browser posts to `/api/ask` on the same domain.

### Optional Claude API mode

In Vercel → Project → Settings → Environment Variables, add `ANTHROPIC_API_KEY` with your key. Optionally add `EXEC_AGENTS_MODEL`. Redeploy after setting environment variables. Do not put secrets in `index.html`.

Without the key, the agents use the built-in offline keyword router. The `anthropic` dependency is included for API mode.

## Run locally

Python 3.10+:

```bash
python server.py
```

Open http://127.0.0.1:8000. The local standard-library server remains included.

## Important

`data.py` contains fictional demonstration data. The current agent logic is intended as a prototype; add authentication, rate limiting and production safeguards before public use. Financial outputs are not professional financial advice.
