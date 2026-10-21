# Esicom Suppliers — multi-page website + Django quotation backend

Premium multi-page business website for Esicom Suppliers. Each core service has a dedicated page and URL; this is not a one-page anchor website. The frontend production build is dependency-free Python and emits static HTML, CSS, JavaScript, locally stored Unsplash photography and a downloadable PDF catalogue. Django stores quotation requests and attempts to send email notifications.

## Included pages

- `/` — Home
- `/office-supplies/` — Office supplies
- `/computer-consumables/` — Computer consumables
- `/bulk-printing/` — Bulk printing
- `/branding/` — Corporate branding
- `/about/` — About Esicom Suppliers
- `/contact/` — Contact and request a quote
- `/send-file/` — Upload a file to Esicom, convert supported PDFs/images, and optionally share the result to WhatsApp
- `/file-qr/` — Print or download the QR code for the file upload page
- `/paper-filing/`, `/business-cards/`, `/branded-apparel/`, `/diaries-asset-tags/` — supporting category pages
- `/catalogue/esicom-suppliers-catalogue.pdf` — downloadable product and services catalogue

Older route paths from the previous archive redirect to the relevant dedicated page. Site photographs are optimized WebP copies stored locally, so pages do not rely on a third-party image server at visit time. The images illustrate product and service categories; they are not presented as completed Esicom client work. Photo sources are documented in the frontend README.

## Confirmed business details

- Business: Esicom Suppliers
- Email: `esicomsuppliers@gmail.com`
- WhatsApp: `0728 942 669` (international link uses `254728942669`)
- Address: Chaka Place Building, Arwings Kodhek Road, Nairobi, Kenya
- Positioning: `SUPPLY. PRINT. BRAND.`

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

### QR file submissions

The printable QR page at `/file-qr/` links to `/send-file/`. Customers can upload one PDF, JPG, PNG, or WebP file, optionally convert PDFs to editable DOCX or convert images between JPEG, PNG, and WebP, then choose email or WhatsApp. Email sends the actual file as an attachment to Esicom (up to 15 MB, to accommodate email provider limits); larger files can use the WhatsApp share option (up to 50 MB). WhatsApp opens the phone's share sheet; the visitor must select Esicom's chat and confirm Send. PDF-to-Word conversion is best-effort; complex layouts and scanned PDFs may need corrections or OCR.

Submissions are listed in Django Admin under **File submissions**. Email submissions include the actual file attachment and a private backup download link; WhatsApp submissions are kept in the staff admin but do not also send an email. Files and backup links remain available until staff deletes the submission. Production SMTP must be configured for email delivery. The provided Nginx example blocks `/media/private/` as defense in depth and allows request bodies up to 55 MB; Render instead uses Django's restricted media route and also needs the 55 MB request limit.

## Staff website editor

Create a Django superuser, run the backend, and sign in at `/admin/`. This is the browser-based site editor:

- Choose **Open visual website editor** in the admin header to see a live website preview. Click visible page text or a photo to select it, then change its wording, font, size, colour, visibility or image in the side panel. Header and footer edits are shared across pages. **Add a section** creates a new text/photo section on the selected page.
- **Website pages** changes each page's eyebrow, heading, introduction and hero photo.
- **Website photos** replaces the built-in photos used across existing pages. Choose the named photo slot, upload a JPG, PNG or WebP up to 8 MB, and save. Delete the replacement to restore the original built-in photo.
- **Products & merchandise** adds, edits, publishes, orders or removes product cards and their photos. Choose a category page; featured items also appear on the homepage.
- **Extra page sections** manages, reorders, publishes or removes sections added in the visual editor. **Products & merchandise** remains available for product-card management.

Changes appear on the public site through the content API without rebuilding the frontend. The editor manages content inside the existing page designs; changing the layout, creating entirely new page templates, and editing form/system wording still requires a developer. For a separate frontend/backend deployment, set `ESICOM_EDITOR_PREVIEW_URL` to the website URL, point `window.ESICOM_API_BASE_URL` to Django, and allow the frontend origin in Django's `CORS_ALLOWED_ORIGINS`. Uploaded images must be JPG, PNG or WebP and no larger than 8 MB.

The public site reads published content from `GET /api/site-content/`. Public editor images are served only from the `catalog/` and `pages/` media folders. Submission files are stored under `private/` and are never returned by the public media route; staff downloads require an authenticated admin session. The upload response also contains an unguessable download URL for the person completing the upload and the delivery workflow. Treat that URL as a bearer secret: anyone who obtains it can download that submission until staff deletes it. On Render, attach a persistent disk and set `DJANGO_MEDIA_ROOT` as described below; without a persistent disk, uploaded files can be lost when the service restarts or deploys.

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

1. Set **Root Directory** to `backend`, **Runtime** to Python, and **Build Command** to `pip install -r requirements.txt && python manage.py collectstatic --noinput`.
2. Set **Start Command** to `python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`.
3. Create a Render PostgreSQL database and set `DATABASE_URL` to its **internal** connection string. Create a Redis/Key Value instance if you want the upload and quote rate limits to be shared across workers; set `REDIS_URL` to its internal connection string.
4. Attach a persistent disk to the web service, mounted at `/var/data`. Set `DJANGO_MEDIA_ROOT=/var/data/media`. The application serves only public content images from `catalog/` and `pages/`; files in `private/` remain outside the public media route.
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

   Render also needs `DJANGO_DEBUG=false`, PostgreSQL, and the HTTPS public-site URL at build time because the build command runs Django. Use a distinct random secret in each environment. Do not set `DJANGO_ALLOWED_HOSTS` to `*`.

6. Deploy and confirm `https://<your-backend-host>/api/health/` returns `{"status":"ok"}`. Then open `https://<your-backend-host>/admin/` and create the first staff superuser from Render's Shell with `python manage.py createsuperuser`.

The HTTPS redirect, secure session/CSRF cookies, HSTS, allowed-host checks, and production secret/database checks are enabled when `DJANGO_DEBUG=false`. WhiteNoise serves Django Admin static files. Rate limiting uses Redis when `REDIS_URL` is configured; without Redis, the local-memory fallback is not shared between workers and is not a production-grade limit.

## Deploy the frontend to Vercel

1. Import the same GitHub repository as a Vercel project.
2. Set **Root Directory** to `frontend`, **Framework Preset** to **Other**, **Build Command** to `python build.py`, and **Output Directory** to `dist`. The build is Python standard-library only and does not need `npm install`.
3. Add `ESICOM_API_BASE_URL` as a **Production** environment variable with the Render backend HTTPS origin, for example `https://esicom-api.onrender.com` (no `/api` suffix and no trailing slash). This is a public API URL, not a secret. The build writes it into the generated `site-config.js`; never add database, SMTP, Django secret, or Redis credentials to Vercel.
4. Deploy, then use the Vercel HTTPS origin in Render's `CORS_ALLOWED_ORIGINS`, `ESICOM_PUBLIC_SITE_URL`, and `ESICOM_EDITOR_PREVIEW_URL`. Redeploy Render after changing its environment values. If you connect a custom domain, add its exact `https://` origin to `CORS_ALLOWED_ORIGINS` and set it as the public-site URL.
5. Test the quote form, upload page, QR code, public CMS images, admin login, editor preview, and email delivery on the deployed domains. The admin lives at `https://<your-backend-host>/admin/`, not on the public Vercel site.

## How requests and files flow

- Vercel serves only the generated public static website from `frontend/dist/`. Its pages call the Render API using the public `ESICOM_API_BASE_URL`; no private credentials are included in that build.
- Render runs Django/Gunicorn, stores enquiries in PostgreSQL, and stores uploads on the attached persistent disk. Redis is shared by backend workers for throttling when configured.
- Django Admin and editor changes require staff authentication. Public site content includes only published page/product/section content. Uploaded editor images are public by design and are limited to the `catalog/` and `pages/` paths.
- Customer submissions are written to the separate `private/file-submissions/` storage path. `/media/private/...` and all other non-public media paths return 404. Staff file downloads require an authenticated admin session; the upload workflow's random-token download URL is a bearer link, so keep it private and delete submissions when no longer needed.
- GitHub contains application source and public website assets, not the production database, runtime uploads, virtual environments, or secrets. Environment variables belong in Render; only the frontend API origin belongs in Vercel.

No hosting setup can honestly be called “bulletproof.” Keep dependencies updated, restrict GitHub visibility and staff accounts, use strong unique passwords and MFA, back up PostgreSQL and the Render disk, test restores, and rotate any credential that may have been exposed.

## Production checklist — required before launch

1. Set `DJANGO_DEBUG=false`, a unique strong `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, and production `CORS_ALLOWED_ORIGINS`.
2. Configure PostgreSQL using `DATABASE_URL` and Redis using `REDIS_URL` for a shared production rate-limit cache. SQLite and local-memory cache are for development only.
3. Configure and test SMTP using the actual email provider. The API deliberately saves the request even if the email notification fails; check server logs for delivery errors.
4. Serve the site and `/api/` over HTTPS, and route `/api/` to Django on the production domain. Set `ESICOM_API_BASE_URL` only if the API lives on a separate origin.
5. Set `ESICOM_PUBLIC_SITE_URL` to the public HTTPS website origin; the QR code is generated from this value and points to `/send-file/`.
6. Confirm the Render disk is persistent, verify direct `/media/private/...` URLs return 404, and regularly delete submissions staff no longer needs from Django Admin.
7. Confirm the WhatsApp number opens the correct company account, and test both forms, file conversions, QR scanning, and staff file deletion on the production host.
8. The current locally stored stock photographs are illustrative, not completed Esicom projects. Replace them with properly licensed Esicom product, workplace and team photography when available.
9. Back up the database and test a restore before launch.

## Build validation

Run `python build.py` from `frontend/`. The build gate checks required page files, local photography and catalogue assets, required contact details, and rejects unsupported company claims. Django dependencies must be installed before running `python manage.py check` or the backend tests.
