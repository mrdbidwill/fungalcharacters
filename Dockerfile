FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
# gettext: compiles the translation files (locale/*/LC_MESSAGES/django.po -> .mo)
RUN apt-get update && apt-get install -y --no-install-recommends gettext && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN DJANGO_SECRET_KEY=build-only python manage.py compilemessages -v 0
# Every file readable by the unprivileged app user, whatever its mode on the Mac.
RUN useradd --system --uid 10001 --home /app app && chmod -R a+rX /app && chmod +x deploy/entrypoint.sh \
    && mkdir -p /app/staticfiles && chown -R app /app/staticfiles
EXPOSE 8000
# Development (docker-compose.yml) overrides this with runserver.
CMD ["deploy/entrypoint.sh"]
