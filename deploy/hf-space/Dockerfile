# AG-DATA farmer app + read-only API over the published gold layer (no Spark, no training, no API key).
# Built from the folder that scripts/build_space.sh assembles.
FROM python:3.12-slim
RUN useradd -m -u 1000 user
WORKDIR /home/user/agdata
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=user . .
USER user
ENV PYTHONPATH=/home/user/agdata/py \
    AGRI_GOLD_ROOT=data/gold \
    AGRI_RESULTS_ROOT=results/forecast \
    AGRI_APP_DIR=app \
    AGRI_REFRESH_STATUS=results/refresh/status.json \
    AGRI_API_TRUST_PROXY=1 \
    AGRI_API_RATE_PER_MIN=600 \
    AGRI_API_CORS_ORIGINS=https://kaushalrog.github.io
EXPOSE 7860
CMD ["uvicorn", "agri.api.app:app", "--host", "0.0.0.0", "--port", "7860", "--proxy-headers", "--forwarded-allow-ips", "*"]
