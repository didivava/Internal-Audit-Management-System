FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./
COPY accounts ./accounts
COPY audit_platform ./audit_platform
COPY core ./core
COPY manage.py ./
COPY templates ./templates
COPY static ./static

RUN python -m pip install --no-cache-dir . \
    && DJANGO_DEBUG=true python manage.py collectstatic --noinput

RUN addgroup --system app \
    && adduser --system --ingroup app app \
    && chown -R app:app /app/staticfiles

USER app

EXPOSE 8000

CMD ["gunicorn", "audit_platform.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-", "--error-logfile", "-"]
