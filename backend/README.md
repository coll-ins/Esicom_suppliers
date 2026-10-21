# Esicom Django API

## Local setup (Windows Command Prompt)

```cmd
cd backend
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 8000
```

Keep this terminal open. The API is at `http://127.0.0.1:8000/api/quote/`; health check: `http://127.0.0.1:8000/api/health/`. The default development email backend does not deliver real email. Quote enquiries are still saved locally, while choosing email for a file submission returns a clear "email is not configured" error. Configure SMTP before testing real email delivery.

## QR file submissions

The static website provides `/file-qr/` for printing the QR and `/send-file/` for the upload form. The QR PNG is served by `GET /api/file-upload-qr/`; `POST /api/file-submissions/` accepts one PDF, JPG, PNG, or WebP file up to 50 MB. PDFs can be converted to DOCX; images can be converted between JPEG, PNG, and WebP. PDF-to-Word conversion is best-effort and may change complex layouts; scanned PDFs need OCR for editable text. Visitors choose email or WhatsApp. Email sends the actual file as an attachment to Esicom, limited to 15 MB because email providers commonly cap attachment size. WhatsApp opens the phone's file-share screen; the visitor selects Esicom's chat and confirms Send. A website cannot send WhatsApp files silently.

File submissions appear under **File submissions** in Django Admin. The email notification includes the actual file attachment, a private backup download link and a staff admin link. WhatsApp submissions are saved for staff but do not also send an email. Files live under `MEDIA_ROOT/private/`, are not served as public media, and remain available until staff deletes the submission; deleting the record in the admin also removes original and converted files. The upload endpoint allows up to 200 attempts per client IP per hour. Configure SMTP for email delivery. In production, block direct Nginx access to `/media/private/` and use the included 55 MB request limit. Configure `ESICOM_PUBLIC_SITE_URL` to the real public HTTPS website origin before printing the QR; it defaults to `http://localhost:4173` for local development.

Admin: `http://127.0.0.1:8000/admin/` — sign in with the superuser you created. **Website pages** edits page headings, copy and optional hero photos; **Products & merchandise** lets staff upload, edit, publish and order real product photos for category pages and the homepage. Only published entries are public. Use authentic Esicom product and branded-merchandise photos; the built-in stock photos are illustrative. Uploads must be JPG, PNG or WebP and no larger than 8 MB. **Quote requests** contains submitted enquiries. Do not share admin credentials.

The public site reads published copy and products from `GET /api/site-content/`. In local development, product/page photos are served from `/media/`; production must configure persistent media storage and serve that path through the web server. Customer submissions are kept under `/media/private/` and must never be served directly. See the root README for frontend-origin and deployment details.

## Email notifications

For Gmail, enable 2-Step Verification on `esicomsuppliers@gmail.com` and create a Google App Password for the website. In the backend host's environment-variable settings, set `DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST=smtp.gmail.com`, `EMAIL_PORT=587`, `EMAIL_USE_TLS=true`, `EMAIL_HOST_USER=esicomsuppliers@gmail.com`, `EMAIL_HOST_PASSWORD` to the generated App Password, and `DEFAULT_FROM_EMAIL=esicomsuppliers@gmail.com`. Restart the backend and send a small test file to confirm delivery. Use the App Password, not the account's normal password, and never share or commit it. These settings are read from process environment variables; a local `.env` file is not loaded automatically.

On Windows, stop any existing backend server with Ctrl+C, then start a Gmail-configured local server from PowerShell using `powershell -ExecutionPolicy Bypass -File "C:\Users\ADMIN\Downloads\Esicom-Suppliers-Website\backend\start_with_gmail.ps1"`. The script prompts securely for the App Password, verifies SMTP login, and starts Django only after a successful check. Keep that PowerShell window open; the upload page must use this server on port 8000.

## Production checklist

- Set `DJANGO_DEBUG=false`, a long unique `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, and exact `CORS_ALLOWED_ORIGINS`.
- Use PostgreSQL for production, HTTPS, a managed Redis/shared cache for rate limiting, backups and monitoring.
- Set `ESICOM_PUBLIC_SITE_URL` to the public HTTPS frontend origin and keep `/media/private/` blocked from direct web access. Delete submissions staff no longer needs from Django Admin.
- Configure real SMTP delivery and test receipt at `esicomsuppliers@gmail.com`.
- Add production security settings (secure cookies, HTTPS redirect, HSTS) at the hosting/proxy layer once HTTPS is confirmed.
- The public form endpoint is intentionally CSRF-exempt because it accepts cross-origin JSON from a public site; it validates inputs, includes a honeypot, and applies basic IP throttling. Put stronger edge rate limiting/WAF in front for production.
