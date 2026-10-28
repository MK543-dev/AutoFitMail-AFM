# AutoFitMail (AFM)

Tailor your resume to a job description and apply by email, with one review click.

Upload your resume and paste the job description (JD). AFM then: extracts the skills in both and shows a match score with the gaps · rewrites your resume so it mirrors the JD using **only facts already in your resume** (enforced by a code guard) · renders an ATS-friendly PDF · drafts the application email and sends it to the recruiter **only after you confirm** · saves every application in a tracker.

**Scope:** AFM works only for jobs applied to by resume + email. It does not fill web forms on company portals and does not automate LinkedIn / Naukri (they block bots).

## Features

- Resume upload (PDF / DOCX, max 5 MB) with text extraction and a clear error for scanned PDFs
- **Two-field New Application**: upload your resume + paste the whole job post (emojis and markdown are fine) — AFM auto-extracts the role, company and recruiter emails (**To + CC**), then runs the skill/match analysis
- Skill extraction (spaCy `PhraseMatcher` over `data/skills.json`, 133 skills + aliases) and a match score = matched required skills / total required; "nice to have" skills are reported separately and never lower the score
- Learning links for every missing skill
- Prompt-driven LLM rewrite (expert-resume-writer prompt: JD analysis, ATS keywords, action-verb bullets, honesty labels, one page) with the **no-invention guard**: employers, titles and numbers are verified against your resume; skills may also come from the JD so the resume can match the job (`ALLOW_JD_SKILLS=True`, the default — set `False` for resume-only skills)
- Editable generated resume + live PDF preview + download
- **Reference-style one-page PDF**: serif layout, centered header, navy section rules (LaTeX-style), with Summary, Skills, Experience, Projects, Education and **Certifications** sections
- Apply with your own resume too: upload your preferred PDF/DOCX right on the review page (it is sent **instead of** the generated PDF), or skip tailoring entirely with "Apply with my own resume" on the analysis page
- **Review before send**: a mandatory preview page; nothing is ever sent silently
- **AI-written application emails** from the JD + tailored resume (120–180 words, 3-paragraph structure, real contact details, subject line) with a clean fallback template · PDF attached, `Reply-To` set to the user, optional Cc, 20 sends/user/day cap, duplicate warning, `FAILED` states with a visible error and retry
- Tracker: Draft / Sent / Interview / Offer / Rejected, with filters and search
- Privacy: per-user data isolation, delete-my-data, secrets only in `.env`, no resume text in logs, public privacy page

## Tech stack

Django 5 · spaCy PhraseMatcher · Anthropic API (writing) · WeasyPrint for the ATS PDF, with an automatic `xhtml2pdf` fallback when the Pango runtime is unavailable · Bootstrap 5 (CDN) · SQLite in dev / PostgreSQL in production · WhiteNoise · Docker (gunicorn).

## Local setup

```bash
python -m venv venv
# Windows: venv\Scripts\activate    |    macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
copy .env.example .env        # then edit it (see the table below)
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000, sign up, upload a resume and paste a JD. The flow is: **Upload & JD → Analysis → Tailored resume → Review & send → Tracked**.

Notes:

- **PDF engine:** WeasyPrint needs the Pango runtime. Linux: `sudo apt install libpango-1.0-0 libpangoft2-1.0-0`. Windows: install the GTK runtime — or just let AFM use its automatic `xhtml2pdf` fallback. The Docker image already includes Pango.
- **No API key?** The writer automatically uses a deterministic offline stub that only reuses resume text, so the whole flow (and the tests) work before you add `ANTHROPIC_API_KEY`.
- **Any Anthropic-compatible provider works:** set `ANTHROPIC_BASE_URL` in `.env` (e.g. AshnaAI: `https://api.ashna.ai/v1/api`) with the provider's key in `ANTHROPIC_API_KEY` — the no-invention guard and review-before-send stay exactly the same. Prefer Google Gemini? Set `LLM_PROVIDER=gemini` + `GEMINI_API_KEY` (free key: https://aistudio.google.com/apikey) — `python check_llm.py` tests whichever provider is configured.
- **Generation fails?** Run `python check_llm.py` inside `afm/` — it prints the exact HTTP error (401 wrong key, 403 model not allowed, 404 unknown model, 429 rate limit). Test a specific model with `python check_llm.py glm-5.3-flash`. Note: Ashna's **free plan cannot fund API calls** (their API replies 429 "External API usage is available on a paid plan only") — that one needs their paid plan or another provider.
- **Emails in development:** with `DEBUG=True`, AFM uses Django's console email backend — pressing "Confirm and send" prints the complete email in the terminal instead of sending it. To send for real from your own machine, fill `EMAIL_HOST_USER` + `EMAIL_HOST_PASSWORD` (a Gmail app password) in `.env` and uncomment `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, then restart the server.
- **Send fails with "Connection unexpectedly closed"?** Your network is blocking the SMTP port. Test it in PowerShell: `Test-NetConnection smtp.gmail.com -Port 587`. If it fails, switch to Gmail's alternate port in `.env`: `EMAIL_PORT=465`, `EMAIL_USE_SSL=True`, `EMAIL_USE_TLS=False`, restart and retry. Also check antivirus mail-shield/firewall, and try another network (e.g. a phone hotspot). For a precise diagnosis, run `python check_smtp.py` inside `afm/` — it reports exactly which step fails (connect / TLS / login). If the helper reports `getaddrinfo failed`, it's **DNS**: run `ipconfig /flushdns` and retry; if it persists, set your DNS servers to `8.8.8.8` / `1.1.1.1` or use another network — browsers can still work in that state because they use their own DNS.
- **Send fails with a 534/535 auth error, or "Connection unexpectedly closed" at the login step?** The app password is wrong, belongs to a different account, or the value is your normal account password (which never works). Create a fresh app password for the exact sending account (16 letters; 2-Step Verification must be ON) — stray spaces are ignored automatically. If Gmail keeps cutting the login: sign in to that account in the browser and approve any "blocked sign-in attempt" alert (inbox or `https://myaccount.google.com/notifications`), retry from another network if it persists (campus/shared networks are sometimes flagged), and remember that repeated failures pause app logins for 30–60 minutes.
- **Send fails with "network is unreachable" (WinError 10051)?** Your network hands out unreachable IPv6 addresses for Gmail (common on campus/shared Wi-Fi). Set `EMAIL_BACKEND=config.email_backend.IPv4SMTPBackend` in `.env` (prefers IPv4, with automatic fallback), restart, and retry — `check_smtp.py` already prefers IPv4.

## Environment variables

| Variable | Purpose |
|---|---|
| `DEBUG` | `True` locally; `False` in production (enables HTTPS / HSTS hardening) |
| `SECRET_KEY` | Django secret; long and random |
| `ALLOWED_HOSTS` | Comma-separated hostnames, e.g. `127.0.0.1,localhost` |
| `DATABASE_URL` | `sqlite:///db.sqlite3` in dev; the Postgres URL in production |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | Gmail address + app password (used for real sends when `DEBUG=False`) |
| `EMAIL_BACKEND` | Optional override: set to `django.core.mail.backends.smtp.EmailBackend` to send real mail even while `DEBUG=True`; default is console in dev, SMTP in production |
| `ANTHROPIC_API_KEY` | Enables the real LLM writer (empty = offline stub) |
| `ANTHROPIC_BASE_URL` | Optional: point the writer at any Anthropic-Messages-compatible provider (e.g. `https://api.ashna.ai/v1/api` for AshnaAI). Empty = Anthropic's own API |
| `ANTHROPIC_MODEL` | Model id (set to a Claude model you have access to) |
| `DAILY_SEND_LIMIT` | Sends per user per day (default 20) |
| `ALLOW_JD_SKILLS` | `True` (default): skills named in the JD may appear even if absent from the resume; `False` = resume-only skills |
| `CSRF_TRUSTED_ORIGINS` | e.g. `https://yourapp.onrender.com` in production |
| `LLM_PROVIDER` | `anthropic` (default; works with Anthropic-compatible gateways) or `gemini` |
| `GEMINI_API_KEY` | Google AI Studio key (https://aistudio.google.com/apikey) when `LLM_PROVIDER=gemini` |
| `GEMINI_MODEL` | Gemini model id (default `gemini-3.8-flash`; if your key rejects it, Google's error message names the right current one) |

## Tests

```bash
python manage.py test
```

52 tests cover: scorer + required/optional split, alias matching, JD auto-extraction (role, company, To + CC emails), recruiter-email detection, PDF/DOCX parsing (including corrupt and scanned-like files), the no-invention guard, the offline writer stub, PDF rendering, the full signup → analysis → generate → edit flow, the mailer (attachment type, `Reply-To`, daily cap, SMTP failure → `FAILED`, no-send-without-review-checkbox), duplicate-send protection, per-user isolation (404s), login rate limiting, and the review-page resume upload (own file replaces the generated PDF, bad file types rejected, remove-to-fallback, apply-without-generating), the AI email generator (JSON subject/body + offline template fallback), and JD-skill allowance (JD-named skills pass the guard; strict mode rejects them).

## Deploy (Render, via Docker)

1. Push the repo to GitHub — confirm `.env` is **not** committed.
2. Create a PostgreSQL instance and copy its internal URL into `DATABASE_URL`.
3. Create a Web Service from the repo using the `Dockerfile`; add the environment variables from the table above (`DEBUG=False`, `CSRF_TRUSTED_ORIGINS=https://yourapp.onrender.com`).
4. Add a persistent disk mounted at `/app/media` for uploads and generated PDFs, and set the pre-deploy command to `python manage.py migrate`.
5. Open the live URL and run the flow: upload → analyze → generate → send to a test inbox.

The gunicorn timeout is 120 s because resume generation waits for the LLM. WeasyPrint's Pango libraries are installed inside the image, so PDF rendering uses WeasyPrint in production.

## Folder structure

```
afm/
├─ manage.py
├─ requirements.txt
├─ Dockerfile / .dockerignore
├─ .env.example / .gitignore
├─ config/            # settings, urls, wsgi/asgi
├─ accounts/          # signup, login (+ per-IP rate limit), delete-my-data
├─ analyzer/          # resume upload, JD form, match analysis
│  └─ services/       # parser.py, jd_utils.py, skills.py, scorer.py, roadmap.py
├─ resume_gen/        # generation, editing, PDF
│  └─ services/       # writer.py, guard.py, stub.py, pdf.py
├─ applications/      # email apply + tracker
│  └─ services/       # draft.py, mailer.py
├─ data/skills.json   # skill catalog + free learning links
├─ templates/         # base.html, partials, one folder per app
├─ static/css/        # afm.css
└─ media/             # uploads + generated PDFs (git-ignored)
```

## Demo script (90 seconds)

| Time | Show |
|---|---|
| 0:00 | Problem: the same resume for every job fails ATS keyword checks |
| 0:10 | Upload a resume, paste a JD |
| 0:25 | Score ring, missing skills, learning path |
| 0:40 | Generate the tailored resume, edit a bullet, show the PDF |
| 1:00 | Email preview, tick the review box, send |
| 1:15 | Tracker with the new Sent row |

## Limitations & roadmap

Current limitations:

- Skill detection is bounded by `data/skills.json`; new technologies need an entry with aliases.
- Required vs "nice to have" uses simple keyword markers (`nice to have`, `preferred`, `bonus`, ...).
- Emails are sent from the app mailbox with the user's address in `Reply-To`; per-user OAuth sending is planned.
- Generation runs inside the web request (up to ~30 s).

Roadmap: 1.1 move generation to Celery + Redis with a progress page · 1.2 send from the user's own Gmail via OAuth · 1.3 cover-letter generation with the same no-invention guard · 1.4 more PDF templates + DOCX export · 1.5 follow-up reminders after 7 days · 2.0 charts (applications per week, response rate), skill-demand stats, interview tips.
