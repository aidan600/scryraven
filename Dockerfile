FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-noto-core fonts-noto-cjk fonts-noto-mono \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements-hosted.txt requirements-pdf.txt ./
RUN pip install --no-cache-dir -r requirements-hosted.txt -r requirements-pdf.txt
# Deliberately copy only runtime source: no local sessions, credentials or logs.
COPY core ./core
COPY scryraven ./scryraven
CMD ["python", "-m", "scryraven.wsgi"]
