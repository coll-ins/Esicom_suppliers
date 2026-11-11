# Backend image for Render. WeasyPrint needs Pango/HarfBuzz from the OS, which pip cannot install.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libharfbuzz-subset0 \
      libjpeg62-turbo libopenjp2-7 shared-mime-info fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

# Static files are collected at build time. These values exist only so settings load;
# collectstatic never connects to a database. Real values come from Render's environment.
RUN DJANGO_SECRET_KEY=build-only-not-a-secret-build-only-not-a-secret-build-only \
    DATABASE_URL=postgres://build:build@localhost:5432/build \
    ESICOM_PUBLIC_SITE_URL=https://example.invalid \
    python manage.py collectstatic --noinput

RUN useradd --create-home app && mkdir -p /var/data && chown app /var/data
USER app

EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py ensure_owner && exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120"]
