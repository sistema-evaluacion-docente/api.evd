FROM python:3.12-slim

WORKDIR /app

# WeasyPrint (PDF de los formatos oficiales) necesita Pango/HarfBuzz del sistema;
# fonts-liberation aporta una serif métricamente compatible con Times New Roman.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 \
    libffi-dev libjpeg-dev libopenjp2-7-dev fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/docker/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker/docker-entrypoint.sh"]