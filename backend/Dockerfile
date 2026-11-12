FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY scripts/import_store_prices.py scripts/build_brand_chains.py scripts/build_value_reference.py scripts/build_type_index.py scripts/build_taxonomy_index.py scripts/build_quick_index.py ./scripts/
RUN touch scripts/__init__.py
# Data (product, price and store databases) lives on the persistent volume mounted at /data, not in the image.
ENV OFF_LOCAL=/data/off_local.db OP_LOCAL=/data/op_local.db OFF_CACHE=/data/off_cache.db DATABASE_URL=sqlite:////data/mieux.db
ENV OFF_LOCAL_US=/data/off_local_us.db OFF_QUICK_US=/data/off_quick_us.db OFF_CACHE_US=/data/off_cache_us.db OP_LOCAL_US=/data/op_local_us.db
EXPOSE 8010
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8010"]
