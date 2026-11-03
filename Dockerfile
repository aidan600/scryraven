FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt requirements-hosted.txt ./
RUN pip install --no-cache-dir -r requirements-hosted.txt
# Deliberately copy only runtime source: no local sessions, credentials or logs.
COPY core ./core
COPY scryraven ./scryraven
CMD ["python", "-m", "scryraven.wsgi"]
