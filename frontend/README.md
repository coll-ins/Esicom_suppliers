# Esicom Suppliers website

Premium multi-page Esicom Suppliers website with a warm ivory, forest-green and brass palette, locally stored category-specific product photography and the `SUPPLY. PRINT. BRAND.` positioning.

## Pages included

- `/` — Home
- `/products` — Product overview
- `/products/office-supplies` — Office stationery and essentials
- `/products/paper-filing` — Paper, files and filing
- `/products/computer-consumables` — Computer and printing consumables
- `/services/printing` — Bulk printing
- `/services/branding` — Corporate branding overview
- `/services/business-cards` — Business cards
- `/services/branded-apparel` — Branded shirts and apparel
- `/services/diaries-asset-tags` — Diaries, branded stationery and asset tags
- `/about` — About Esicom
- `/contact` — Contact and quotation form
- `/send-file` — QR-linked file submission and conversion page
- `/file-qr` — Printable/downloadable QR page for file submissions

Each category/service page has its own URL, page heading, imagery, specific service information and quotation CTA. Navigation and footer links connect the pages.

## Photography

The four homepage opening carousel images are kept as the existing locally stored files in `public/images/hero/`. Other page heroes and cards use topic-matched photography in `public/images/products/`. Standard office stationery stays generic and unbranded. Branding examples show the supplied Esicom polo plus ivory notebooks, a navy notebook-and-pen set adapted from the supplied layout reference, forest-green diaries, asset tags and Esicom business-card colourways. The navy notebook reference has been rebranded with Esicom artwork; third-party names and marks are not displayed. The brand mockups intentionally demonstrate varied typography, wordmark scale and placement while preserving the Esicom Suppliers name. Computer Consumables includes office printers and printer supplies. Branded design renders are illustrative mockups, not completed customer orders or confirmation of available stock. No generic legacy stock-photo set is included in the build.

## Build and preview locally

Start the Django backend in a separate PowerShell terminal first; the upload form and quote form need its API:

```powershell
cd ..\backend
.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py runserver 8000
```

In another terminal, from `frontend\`:

```bash
python build.py
python -m http.server 4173 --directory dist
```

Then open `http://localhost:4173`. Local previews on ports 4173 and 5173 automatically use the Django API at `http://127.0.0.1:8000`; both servers must stay running. The static site build does not require npm packages.

## Build for deployment

```bash
python build.py
python -m http.server 4173 --directory dist
```

Deploy the contents of `dist/` to a static host. Each service has its own generated page; no single-page application rewrite is required.

## Enquiries

Quote requests are submitted to `POST /api/quote/` and saved by the Django backend. Set `window.ESICOM_API_BASE_URL` in `public/site-config.js` for a local/manual build, or set the `ESICOM_API_BASE_URL` environment variable to the HTTPS backend origin during a production build. See the repository root README for Render/Vercel and CORS setup. Visitors can also contact Esicom directly using the email and WhatsApp links.

The file page accepts PDF, JPG, PNG, and WebP files, with a 15 MB maximum for email attachments and a 50 MB maximum for WhatsApp sharing. PDFs may be converted to DOCX; images can be converted among JPEG, PNG, and WebP. Email sends the actual uploaded/converted file as an attachment; configure SMTP for delivery (the local development console backend is not a real inbox). WhatsApp opens the phone's file-share sheet and requires the visitor to choose Esicom's chat and confirm Send. A private copy remains in Django Admin until staff deletes it. See the root and backend READMEs for deployment requirements and conversion limitations.

## Staff content editor

The Django Admin at `/admin/` is the staff-only editor for website copy and product listings. Sign in with a Django staff account, then use **Website pages** to change each page's heading, introduction and optional hero photo. Use **Products & merchandise** to add or edit listings and photos, choose their category page, set display order, feature them on the homepage, or unpublish them to remove them from the public site. Featured product photos also appear in the homepage carousel; changing, featuring or unpublishing products updates the carousel when the public site is connected to the API. Delete an item in Admin when it should be removed permanently. Use real Esicom product, workplace or branded-merchandise photos when available; the built-in local stock photographs are illustrative, not completed customer projects. The static site fetches published entries from `GET /api/site-content/`, so content changes appear on the public site without rebuilding when the deployed frontend and API are connected. Set `window.ESICOM_API_BASE_URL` in `public/site-config.js` for a local/manual separate-origin build, or set `ESICOM_API_BASE_URL` during the build; the frontend falls back to its built-in copy and illustrative product cards if the API is unavailable. See the root README for setup and production media-storage instructions.

## Business details

- Esicom Suppliers
- Email: `esicomsuppliers@gmail.com`
- Location: Chaka Place Building, Arwings Kodhek Road, Nairobi, Kenya
- Offerings: stationery and office supplies, printing paper, files and folders, notebooks, pens, toners, cartridges, computer appliances, bulk printing, business cards, branded shirts, asset tags, diaries, and corporate branding.
- Stock photographs illustrate the product categories and do not depict Esicom customer projects. Do not add unverified claims about customers, delivery times, partnerships or certifications.
