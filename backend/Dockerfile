FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
# Data (product, price and store databases) lives on the persistent volume mounted at /data, not in the image.
ENV OFF_LOCAL=/data/off_local.db OP_LOCAL=/data/op_local.db OFF_CACHE=/data/off_cache.db DATABASE_URL=sqlite:////data/mieux.db
EXPOSE 8010
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]
