FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --system --uid 10001 --home /app app && chmod +x deploy/entrypoint.sh \
    && mkdir -p /app/staticfiles && chown -R app /app/staticfiles
EXPOSE 8000
# Development (docker-compose.yml) overrides this with runserver.
CMD ["deploy/entrypoint.sh"]
