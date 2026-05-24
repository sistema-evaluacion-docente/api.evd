FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

RUN chmod +x /app/docker/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/docker/docker-entrypoint.sh"]