FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# poker.db lives here; mount a Fly.io volume at this path so it survives
# restarts/redeploys (SQLite is otherwise lost on any ephemeral filesystem).
ENV DB_PATH=/data/poker.db

EXPOSE 8080
CMD ["uvicorn", "api.routes:app", "--host", "0.0.0.0", "--port", "8080"]
