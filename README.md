# Esicom Suppliers — website, ledger and dashboard

Premium multi-page business website for Esicom Suppliers. Each core service has a dedicated page and URL; this is not a one-page anchor website. The frontend production build is dependency-free Python and emits static HTML, CSS, JavaScript, and locally stored category-specific product photography. The website shows no prices: customers request a quote. Django stores quotation requests, runs the staff **ledger** (sales, invoices, receipts, quotations, credit notes, payments, stock) and serves the customer file-upload page. The **dashboard** (`dashboard/`, React) is the staff screen for the ledger.

## Included pages

- `/` — Home
- `/office-supplies/` — Office supplies
- `/computer-consumables/` — Computer consumables
- `/bulk-printing/` — Bulk printing
- `/branding/` — Corporate branding
- `/about/` — About Esicom Suppliers
- `/contact/` — Contact and request a quote
- `/upload/` — Customer file upload (served by Django through a Vercel rewrite; reached by scanning the QR code in the shop)
- `/paper-filing/`, `/business-cards/`, `/branded-apparel/`, `/diaries-asset-tags/` — supporting category pages

Older route paths from the previous archive redirect to the relevant dedicated page. Site photographs are stored locally, so pages do not rely on a third-party image server at visit time. Ordinary office stationery remains unbranded; the branding section includes illustrative Esicom-branded notebook, asset-tag and business-card design mockups, the supplied polo reference, and computer/printer product examples. Mockups illustrate possible designs; they are not completed customer orders or proof of stock. See the frontend README for details.

## Confirmed business details

- Business: Esicom Suppliers
- Email: `esicomsuppliers@gmail.com`
- WhatsApp: `0728 942 669` (international link uses `254728942669`)
- Address: Chaka Place Building, Argwings Kodhek Road, Nairobi, Kenya
- Positioning: `Quality Supplies. Greater Productivity.`

The site intentionally does not claim nationwide delivery, SME support, years of experience, customer counts, same-day delivery, certifications, authorised distributorships, or unconfirmed payment methods.

## Build and preview (Windows PowerShell)

Install Python 3.10+ and Node.js/npm only if you want to use the npm script wrapper. The website build itself does not download npm packages.

```powershell
cd path\to\Esicom-Suppliers-Website\frontend
python build.py
npm.cmd run build
npm.cmd run preview
```

Then open `http://localhost:4173`. You can also preview without npm using:

```powershell
python -m http.server 4173 --directory dist
```

The production output is `frontend/dist/`. It is plain static content; deploy that directory to a static host. The custom paths are real directories with their own `index.html` files, so no SPA rewrite is required.

## Django quote backend

In a second terminal:

```powershell
cd path\to\Esicom-Suppliers-Website\backend
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 8000
```

Local frontend quote submissions use the same-origin `/api/quote/` endpoint by default. To test with a separately served static frontend, set `window.ESICOM_API_BASE_URL` in `frontend/dist/site-config.js` to `http://127.0.0.1:8000` before previewing. Django CORS defaults allow localhost:5173 and 127.0.0.1:5173; add the actual preview origin to `CORS_ALLOWED_ORIGINS` if needed.

The API is `POST /api/quote/`; health check is `GET /api/health/`. Submitted requests are saved to the `QuoteRequest` database table. Email notifications use Django's configured email backend. The development default prints email to the server console; configure SMTP in production if real email notifications are required. Admin users can review saved enquiries at `/admin/`.

### Customer file uploads (`/upload/`)

The public upload page does one thing: a customer picks a file (PDF, Word `.docx`, JPG, PNG or WebP, up to 50 MB), optionally converts PDF to Word or Word to PDF, adds an optional name, Kenyan phone and note, and sends it. Every file is saved privately and emailed to `esicomsuppliers@gmail.com`. Files up to 15 MB are attached; larger ones are listed in the email with a link to the dashboard. If the email fails, the file is still saved and listed in the dashboard under **File uploads**.

The QR code for this page is shown **only in the staff dashboard** (Upload QR code, with a Print button). There is no public QR page and no public download link; staff download files from the dashboard or Django Admin after logging in. Word to PDF uses mammoth and WeasyPrint: text, headings, lists, tables and pictures come through, but exact Word layout can differ. PDF to Word is best-effort; scanned PDFs become pictures.

## Staff website editor

Create a Django superuser, run the backend, and sign in at `/admin/`. This is the browser-based site editor:

- Choose **Open visual website editor** in the admin header to see a live website preview. Click visible page text or a photo to select it, then change its wording, font, size, colour, visibility or image in the side panel. Header and footer edits are shared across pages. **Add a section** creates a new text/photo section on the selected page.
- **Website pages** changes each page's eyebrow, heading, introduction and hero photo.
- **Website photos** replaces the built-in photos used across existing pages. Choose the named photo slot, upload a JPG, PNG or WebP up to 8 MB, and save. Delete the replacement to restore the original built-in photo.
- **Extra page sections** manages, reorders, publishes or removes sections added in the visual editor.

Changes appear on the public site through the content API without rebuilding the frontend. The editor manages content inside the existing page designs; changing the layout, creating entirely new page templates, and editing form/system wording still requires a developer. For a separate frontend/backend deployment, set `ESICOM_EDITOR_PREVIEW_URL` to the website URL, point `window.ESICOM_API_BASE_URL` to Django, and allow the frontend origin in Django's `CORS_ALLOWED_ORIGINS`. Uploaded images must be JPG, PNG or WebP and no larger than 8 MB.

The public site reads published content from `GET /api/site-content/`. Public editor images are served only from the `pages/` media folder. Submission files are stored under `private/` and are never returned by the public media route; staff downloads require a logged-in dashboard or admin session. On Render, attach a persistent disk and set `DJANGO_MEDIA_ROOT` as described below; without a persistent disk, uploaded files can be lost when the service restarts or deploys.

## Ledger and dashboard

The ledger lives in `backend/ledger/` (Django REST Framework, all endpoints under `/api/ledger/`, every one needs a logged-in owner or staff user except login and password reset). The dashboard in `dashboard/` (React, Vite, Tailwind) is the only screen for it.

What it does:

- **Record a sale**: pick or add a customer (or Walk-in, pays now), add stock items or custom lines (services and branding jobs do not touch stock), choose Paid now (M-Pesa, cash, bank) or On credit, review, save. Saving takes items off stock and issues the invoice; a receipt is made only when the customer wants one. Sales above the stock on hand are blocked with the count left.
- **Running tabs**: per customer, choose "Invoice per sale" or "Running tab". Tab items add up; **Print invoice now** bills only the items not yet billed and the tab stays open; **Close tab** puts the rest on a final invoice.
- **Money rules**: prices are entered before VAT, in whole shillings. VAT (16% by default, Settings) is worked out per line and rounded to the whole shilling. Products can be VAT exempt (owner sets it, staff only if allowed). Part payments are off unless the owner allows them per customer or per invoice. Overpayments are refunded by default or kept as credit, which pays the next invoice automatically. The same M-Pesa code cannot be recorded twice.
- **Corrections**: issued documents are never edited. Void (restores stock; money already paid becomes credit) or issue a credit note (optionally returning items to stock). Voided documents keep their number.
- **Numbering**: `ESI-INV-2026-0001`, `ESI-RCP-…`, `ESI-QTN-…`, `ESI-CN-…`, sequential per type and year, never reused, no gaps (the counter is locked inside the same database transaction as the document).
- **Documents**: A4 PDFs rendered with WeasyPrint from `ledger/templates/ledger/`, fonts shipped in `ledger/static/ledger/fonts/`. Bank, paybill, till and KRA PIN print only once filled in Settings. Send by email (PDF attached) or WhatsApp (opens `wa.me` with a message; staff attach the downloaded PDF).
- **Stock**: stock on hand is the sum of movements (starting stock, receive, sale, take out, return, void); it is never typed over. The buy list shows products at or below their reorder level with an order quantity of reorder level + average monthly sales over the last 3 months.
- **Credit limits**: none by default; when a customer goes over the owner's limit, the owner and staff get an alert in the dashboard and by email.
- **Reminders**: invoice emails 3 days before the due date, on it, and 7 days after. They run on the first request of each day; `.github/workflows/daily-ping.yml` pings the backend every morning so this happens even on quiet days. A reminder date missed while the server slept is skipped, never sent late. Run by hand with `python manage.py run_daily_jobs`.
- **Statements**: only when someone asks (customer page, Statement: open PDF or email).
- **Reports**: money in and out, money owed by age (0-30, 31-60, 61-90, 90+ days), sales by customer and product, profit (owner only), monthly VAT.
- **Website leads**: the website's Request a quote form, with a Create quotation button.
- **Users**: only the owner at first. The owner adds and removes staff. Login is email + password; 5 wrong passwords lock the account for 15 minutes; Forgot password emails a 6-digit code. Sessions last until Log out; **Log out everywhere** ends every session. Staff cannot see costs or profit, change settings, manage users, or void unless the owner allows it. Every change is in the audit log (owner only).
- **eTIMS**: not integrated (needs KRA certification). Each invoice has an optional eTIMS number field for the number from the KRA portal.

### Run locally

```powershell
# backend (terminal 1)
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
$env:DJANGO_DEBUG="true"
python manage.py migrate
python manage.py ensure_owner --email you@example.com --name "Your Name"
python manage.py runserver 8000

# dashboard (terminal 2)
cd dashboard
npm install
npm run dev     # http://localhost:5173 ; /ledger-api is proxied to Django
```

The first owner has no password: on the dashboard login page choose **Forgot password, or first time here?** and use the emailed code (with the console email backend the code is printed in the Django terminal). WeasyPrint needs Pango on the machine; on Windows install it with the WeasyPrint documentation's MSYS2 steps, or run the backend in Docker.

### Tests

```powershell
cd backend;   python -m pytest;  python -m ruff check ledger
cd dashboard; npm test;          npm run lint
```

## Push this project to GitHub (Windows PowerShell)

The GitHub repository used for this project is `https://github.com/coll-ins/Esicom_suppliers`. Before pushing, decide whether the repository should be **Private** (recommended if you do not want the backend source visible). The Python source is not a secret, but a public repository makes it readable by everyone. Never put passwords, API keys, private uploads, database files, or production environment values in GitHub.

Review the files first. `.gitignore` excludes local environment files, SQLite databases, virtual environments, generated build output, and `backend/media/`, but ignore rules do not remove a file that was already committed:

```powershell
git status --short --ignored
git ls-files backend/.env backend/db.sqlite3 backend/media frontend/dist backend/.venv
git diff --cached --check
```

The `git ls-files` command should print nothing for those private/local paths. If it prints a credential or customer file, stop: remove that file from Git history and rotate any exposed credential before pushing. Removing a file in a later commit does not erase it from earlier commits.

After reviewing the staged changes, use:

```powershell
git add -A
git diff --cached --check
git diff --cached --name-only
git commit -m "Prepare Esicom website for deployment"
git remote -v
```

If `git remote -v` prints no remote, add the project repository and push the current `master` branch:

```powershell
git remote add origin https://github.com/coll-ins/Esicom_suppliers.git
git push -u origin master
```

If an `origin` is already listed, do not add it again; confirm it is the intended repository, then run `git push -u origin master`. Do not use `git push --force` to work around a rejected push. If GitHub says the histories differ, stop and reconcile the histories instead of overwriting the remote.

## Deploy the backend to Render

Use a Render **Web Service** connected to this GitHub repository:

1. Set **Root Directory** to `backend` and **Runtime** to **Docker** (Render uses `backend/Dockerfile`). Docker is required because invoice PDFs use WeasyPrint, which needs the Pango libraries from the operating system; Render's plain Python runtime cannot install them. Render does not switch an existing Python service to Docker, so create a new Docker web service and update the backend URL in `vercel.json`, `frontend/vercel.json`, `dashboard/vercel.json` and `.github/workflows/daily-ping.yml` if its URL changes.
2. The image's start command runs migrations, creates the owner from `LEDGER_OWNER_EMAIL` if there is none, and starts Gunicorn. No build or start command is needed in Render.
3. Use the Neon PostgreSQL connection string as `DATABASE_URL` (it must include `sslmode=require`). Create a Redis/Key Value instance if you want the upload and quote rate limits to be shared across workers; set `REDIS_URL` to its internal connection string.
4. Attach a persistent disk to the web service, mounted at `/var/data`. Set `DJANGO_MEDIA_ROOT=/var/data/media`. The application serves only public content images from `pages/`; files in `private/` remain outside the public media route.
5. Add the following environment variables in Render's dashboard (never in GitHub or Vercel):

   | Variable | Value |
   |---|---|
   | `DJANGO_DEBUG` | `false` |
   | `DJANGO_SECRET_KEY` | A new random value; generate locally with `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
   | `DJANGO_ALLOWED_HOSTS` | Your Render backend hostname only, e.g. `esicom-api.onrender.com` |
   | `CORS_ALLOWED_ORIGINS` | Your exact HTTPS Vercel site origin, e.g. `https://esicom-suppliers.vercel.app` (comma-separate additional approved origins) |
   | `DATABASE_URL` | Render PostgreSQL internal connection string |
   | `REDIS_URL` | Render Redis/Key Value internal connection string, if enabled |
   | `DJANGO_MEDIA_ROOT` | `/var/data/media` |
   | `ESICOM_PUBLIC_SITE_URL` | The public HTTPS Vercel website origin |
   | `ESICOM_EDITOR_PREVIEW_URL` | The same public HTTPS Vercel website origin |
   | `DJANGO_EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` |
   | `EMAIL_HOST` | `smtp.gmail.com` when using Gmail |
   | `EMAIL_PORT` | `587` |
   | `EMAIL_USE_TLS` | `true` |
   | `EMAIL_HOST_USER` | The sender mailbox |
   | `EMAIL_HOST_PASSWORD` | A Google App Password, not the mailbox login password |
   | `DEFAULT_FROM_EMAIL` | The sender mailbox |
   | `ESICOM_ENQUIRY_EMAIL` | `esicomsuppliers@gmail.com` |
   | `ESICOM_DASHBOARD_URL` | The HTTPS dashboard origin on Vercel; also trusted for CSRF automatically |
   | `LEDGER_OWNER_EMAIL` | The owner's login email (first start only) |
   | `LEDGER_OWNER_NAME` | The owner's name |

   Render also needs `DJANGO_DEBUG=false`, PostgreSQL, and the HTTPS public-site URL at build time because the build command runs Django. Use a distinct random secret in each environment. Do not set `DJANGO_ALLOWED_HOSTS` to `*`.

6. Deploy and confirm `https://<your-backend-host>/api/health/` returns `{"status":"ok"}`. Then open the dashboard, choose **Forgot password, or first time here?**, enter the owner email and set the password from the emailed code. For the website editor at `/admin/`, give that account staff access from Render's Shell (`python manage.py createsuperuser` also works).

The HTTPS redirect, secure session/CSRF cookies, HSTS, allowed-host checks, and production secret/database checks are enabled when `DJANGO_DEBUG=false`. WhiteNoise serves Django Admin static files. Rate limiting uses Redis when `REDIS_URL` is configured; without Redis, the local-memory fallback is not shared between workers and is not a production-grade limit.

## Deploy the frontend to Vercel

1. Import the same GitHub repository as a Vercel project.
2. Set **Root Directory** to `frontend`, **Framework Preset** to **Other**, **Build Command** to `python build.py`, and **Output Directory** to `dist`. The build is Python standard-library only and does not need `npm install`.
3. Add `ESICOM_API_BASE_URL` as a **Production** environment variable with the Render backend HTTPS origin, for example `https://esicom-api.onrender.com` (no `/api` suffix and no trailing slash). This is a public API URL, not a secret. The build writes it into the generated `site-config.js`; never add database, SMTP, Django secret, or Redis credentials to Vercel. Also add `ESICOM_PUBLIC_SITE_URL` as the production frontend HTTPS origin (for example `https://esicom-suppliers.vercel.app`, with no path or trailing slash). This enables absolute canonical/Open Graph URLs and a sitemap; without it the build omits origin-dependent URLs.
4. Deploy, then use the Vercel HTTPS origin in Render's `CORS_ALLOWED_ORIGINS`, `ESICOM_PUBLIC_SITE_URL`, and `ESICOM_EDITOR_PREVIEW_URL`. Redeploy Render after changing its environment values. If you connect a custom domain, add its exact `https://` origin to `CORS_ALLOWED_ORIGINS` and set it as the public-site URL.
5. Test the quote form, upload page, QR code, public CMS images, admin login, editor preview, and email delivery on the deployed domains. The admin lives at `https://<your-backend-host>/admin/`, not on the public Vercel site.

## Deploy the dashboard to Vercel

1. Import the same repository as a second Vercel project. **Root Directory** `dashboard`, **Framework Preset** Vite, **Build Command** `npm run build`, **Output Directory** `dist`. No environment variables.
2. `dashboard/vercel.json` rewrites `/ledger-api/*` to the Render backend's `/api/ledger/*`, so the login cookie is first-party and no CORS is needed. All other paths serve the app.
3. Set Render's `ESICOM_DASHBOARD_URL` to the dashboard's HTTPS origin and redeploy Render.

## Email through the Gmail API

Render's free plan blocks the ports email servers use (SMTP), so the backend sends through the Gmail API over HTTPS instead. One-time setup, logged in to Google as **esicomsuppliers@gmail.com**:

1. Go to console.cloud.google.com, create a project called `Esicom ledger`, then open **APIs & Services → Library**, search **Gmail API** and press **Enable**.
2. **OAuth consent screen**: choose **External**, app name `Esicom ledger`, support email esicomsuppliers@gmail.com, save. Under **Audience**, press **Publish app** (otherwise Google stops the access after 7 days).
3. **Credentials → Create credentials → OAuth client ID**, type **Web application**. Under **Authorised redirect URIs** add `https://developers.google.com/oauthplayground`. Create, and keep the **Client ID** and **Client secret**.
4. Open developers.google.com/oauthplayground. Press the gear icon, tick **Use your own OAuth credentials**, paste the Client ID and secret. In the box on the left type `https://www.googleapis.com/auth/gmail.send`, press **Authorize APIs**, choose esicomsuppliers@gmail.com and allow it (Google warns the app is unverified; choose **Advanced → Go to Esicom ledger**). Press **Exchange authorization code for tokens** and copy the **Refresh token**.
5. In Render, service **esicom-backend → Environment**, add `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET` and `GMAIL_REFRESH_TOKEN`, then **Save, rebuild and deploy**.

Test it: on the dashboard login page use **Forgot password**; the code should arrive in the inbox.

## Moving the database to Neon

1. Create a free project at neon.tech (region close to Render's Oregon, e.g. US West). Copy the connection string (it starts with `postgresql://` and ends with `sslmode=require`).
2. In Render, service **esicom-backend → Environment**, add `NEON_DATABASE_URL` with that string and deploy. On start the app runs `manage.py move_database`: it copies every table into Neon, checks the row counts match, and never copies into a database that already has data. The log says `move_database: copied.`
3. Then set `DATABASE_URL` to the Neon string, delete `NEON_DATABASE_URL`, and deploy. The app now runs on Neon.
4. Check the dashboard and website leads, then delete the old Render database.

## Backups and restore test

The database is Neon PostgreSQL. Neon keeps point-in-time history (the window depends on the Neon plan). Test a restore before launch and every few months:

1. In Neon, create a branch from a past time (for example one hour ago).
2. Point a local backend at that branch's connection string (`DATABASE_URL=...`, `DJANGO_DEBUG=true`) and run `python manage.py check`.
3. Open the dashboard locally and confirm the latest invoices, payments and stock before that time are there.
4. Delete the test branch.

Uploaded customer files are stored on the backend's disk, not in the database. Attach a Render persistent disk at `/var/data` and set `DJANGO_MEDIA_ROOT=/var/data/media`, or files are lost on each deploy. Every file is also emailed to Esicom when sent.

## How requests and files flow

- Vercel serves only the generated public static website from `frontend/dist/`. Its pages call the Render API using the public `ESICOM_API_BASE_URL`; no private credentials are included in that build.
- Render runs Django/Gunicorn, stores enquiries in PostgreSQL, and stores uploads on the attached persistent disk. Redis is shared by backend workers for throttling when configured.
- Django Admin and editor changes require staff authentication. Public site content includes only published page and section content. Uploaded editor images are public by design and are limited to the `pages/` path.
- Customer submissions are written to the separate `private/file-submissions/` storage path. `/media/private/...` and all other non-public media paths return 404. Staff file downloads require a logged-in dashboard or admin session.
- GitHub contains application source and public website assets, not the production database, runtime uploads, virtual environments, or secrets. Environment variables belong in Render; only the frontend API origin belongs in Vercel.

No hosting setup can honestly be called “bulletproof.” Keep dependencies updated, restrict GitHub visibility and staff accounts, use strong unique passwords and MFA, back up PostgreSQL and the Render disk, test restores, and rotate any credential that may have been exposed.

## Production checklist — required before launch

1. Set `DJANGO_DEBUG=false`, a unique strong `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, and production `CORS_ALLOWED_ORIGINS`.
2. Configure PostgreSQL using `DATABASE_URL` and Redis using `REDIS_URL` for a shared production rate-limit cache. SQLite and local-memory cache are for development only.
3. Configure and test SMTP using the actual email provider. The API deliberately saves the request even if the email notification fails; check server logs for delivery errors.
4. Serve the site and `/api/` over HTTPS, and route `/api/` to Django on the production domain. Set `ESICOM_API_BASE_URL` only if the API lives on a separate origin.
5. Set `ESICOM_PUBLIC_SITE_URL` to the public HTTPS website origin; the dashboard QR code is generated from this value and points to `/upload/`.
6. Confirm the Render disk is persistent, verify direct `/media/private/...` URLs return 404, and regularly delete submissions staff no longer needs from Django Admin.
7. Confirm the WhatsApp number opens the correct company account, and test both forms, file conversions, QR scanning, and staff file deletion on the production host.
8. The current locally stored stock photographs are illustrative, not completed Esicom projects. Replace them with properly licensed Esicom product, workplace and team photography when available.
9. Back up the database and test a restore before launch.

## Build validation

Run `python build.py` from `frontend/`. The build gate checks required page files, local photography, required contact details, rejects unsupported company claims, and fails if the removed catalogue, send-file or file-qr pages come back. Django dependencies must be installed before running `python manage.py check` or the backend tests.
