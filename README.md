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

Submissions are listed in Django Admin under **File submissions**. Email submissions include the actual file attachment and a private backup download link; WhatsApp submissions are kept in the staff admin but do not also send an email. Files and backup links remain available until staff deletes the submission. Production SMTP must be configured for email delivery. Production Nginx must block direct access to `/media/private/` and allow request bodies up to 55 MB; the provided example is configured for this.

## Staff website editor

Create a Django superuser, run the backend, and sign in at `/admin/`. Staff can edit each page's eyebrow, heading, introduction and optional hero photo under **Website pages**, and add or update product and branded-merchandise entries under **Products & merchandise**. For an item to appear on the public site, mark it published; featured items also appear on the homepage. Select its relevant category page and set the display order to control the listing. Upload genuine Esicom product or brand photos; the built-in stock photographs remain illustrative until staff publish actual product photos. Uploaded images must be JPG, PNG or WebP and no larger than 8 MB.

The public site reads published content from `GET /api/site-content/`. In a same-origin deployment the frontend needs no API-base setting. For a separate-origin development preview, set `window.ESICOM_API_BASE_URL` in `frontend/public/site-config.js` to the Django origin and add the frontend origin to `CORS_ALLOWED_ORIGINS`. The local Django server serves uploads from `/media/` in development; in production, configure persistent media storage and serve that path through the web server (the example Nginx config maps it to `backend/media/`). Back up uploaded media along with the database.

## Production checklist — required before launch

1. Set `DJANGO_DEBUG=false`, a unique strong `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, and production `CORS_ALLOWED_ORIGINS`.
2. Configure PostgreSQL using `DATABASE_URL` and install the listed `dj-database-url` dependency; configure `REDIS_URL` for a shared production rate-limit cache. SQLite and local-memory cache are for development only.
3. Configure and test SMTP using the actual email provider. The API deliberately saves the request even if the email notification fails; check server logs for delivery errors.
4. Serve the site and `/api/` over HTTPS, and route `/api/` to Django on the production domain. Set `ESICOM_API_BASE_URL` only if the API lives on a separate origin.
5. Set `ESICOM_PUBLIC_SITE_URL` to the public HTTPS website origin; the QR code is generated from this value and points to `/send-file/`.
6. Confirm the production media storage is persistent and private, and regularly delete submissions staff no longer needs from Django Admin.
7. Confirm the WhatsApp number opens the correct company account, and test both forms, file conversions, QR scanning, and staff file deletion on the production host.
8. The current locally stored stock photographs are illustrative, not completed Esicom projects. Replace them with properly licensed Esicom product, workplace and team photography when available.
9. Back up the database and test a restore before launch.

## Build validation

Run `python build.py` from `frontend/`. The build gate checks required page files, local photography and catalogue assets, required contact details, and rejects unsupported company claims. Django dependencies must be installed before running `python manage.py check` or the backend tests.
