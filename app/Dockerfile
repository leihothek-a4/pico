FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY src/ ./src/

WORKDIR /app/src

EXPOSE 5000

ENV PYTHONUNBUFFERED=1

# SQLite database is written next to the app sources.
VOLUME ["/app/src"]

# Optional: SECRET_KEY, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET,
# GITHUB_ALLOWED_USERS, API_KEY
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "app:app"]
