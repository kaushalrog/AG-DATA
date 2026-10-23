# Deployment

**Status (2026-10-22):** the local deployment has been run and verified (see "Verified"). **No public deployment exists:** no cloud account or credentials were available. No public URL is claimed anywhere in this repository.

## 1. Local, single machine (verified)

Prerequisites: Java 21 (`openjdk@21`), sbt 1.11, Spark 4.2 (Homebrew), Python ≥ 3.11, Node ≥ 22 (tests only), Kafka 4.x (Homebrew, KRaft), and Docker (HDFS only).

```bash
source scripts/env.sh
uv venv .venv -p 3.12 && uv pip install -p .venv/bin/python -e ".[test]"
sbt compile test                                    # Scala tests
.venv/bin/python -m pytest -q tests/python          # Python tests
node --test app/tests/                              # PWA tests

scripts/run_forecast_pipeline.sh fc_main_v3         # features -> benchmark -> backtest -> report -> gold
PYTHONPATH=py .venv/bin/uvicorn agri.api.app:app --app-dir py --port 8000
open http://localhost:8000/                         # PWA served by the API; AGRI_API_DOCS=1 enables /api/docs
```

Static demo only, without a backend: `python3 -m http.server -d app 8080`. The app then reads the exported real-data snapshot in `app/demo/`.

## 2. Container (API + PWA)

```bash
docker build -f Dockerfile.api -t agri-api .
docker run --rm -p 8000:8000 \
  -v "$PWD/data/gold:/srv/data/gold:ro" -v "$PWD/results/forecast:/srv/results/forecast:ro" \
  -e AGRI_API_CORS_ORIGINS=https://your-frontend.example agri-api
```

The image runs as a non-root user, mounts data read-only, and has a health check on `/api/v1/ready`. It contains no Spark, Kafka or credentials.

## 3. Data platform (development cluster)

```bash
docker compose -f docker/docker-compose.yml --profile spark up -d   # HDFS 1 NN + 3 DN, Spark master + 2 workers
# HDFS RPC is published on 127.0.0.1:19000 (set HDFS_RPC_HOST_PORT to change); inside Docker it is namenode:9000
scripts/hdfs_verify.sh                                              # layout, load, fsck, cluster job, DataNode failure
scripts/streaming_demo.sh 20000 2000                                # Kafka replay -> Structured Streaming -> parity
```

## 4. Recommended production layout (not deployed)

| Component | Where | Why |
|---|---|---|
| PWA (static `app/`) | Cloudflare Pages or GitHub Pages | Static, cached at the edge, free. Set `<meta name="agri-api-base">` to the API URL |
| API container | A small VM or container service (e.g. Cloud Run, Fly.io, an Azure Container App) behind TLS | Stateless and read-only. 0.5 vCPU / 512 MB is enough for the gold tables (about 100k rows) |
| Gold layer | Object storage (S3/GCS/R2), synced to the API's disk at start-up, or baked into the image per publish | Small (tens of MB). Versioned by `model_version` |
| Spark batch + HDFS/object store + Kafka | A **private** network (managed Spark such as Dataproc or EMR, or a self-managed cluster) | Never exposed publicly. A nightly job runs `ForecastPublish` and uploads the gold layer |
| Secrets | The cloud secret manager, injected as `AGRI_DATA_GOV_IN_API_KEY` into the ingestion job only | Never in the frontend or the API |

GitHub Pages and Cloudflare Pages host only the static app. They cannot run the API, Spark, Kafka or HDFS.

### Publish cadence
1. Ingest from the data.gov.in adapter, or replay.
2. Kafka and streaming write bronze/silver and alerts.
3. The nightly batch rebuilds silver → features → `ForecastPublish` (no retraining).
4. Retrain monthly with `ForecastBenchmark` on a moving window, and promote the new model only if its validation metrics beat the incumbent's.

Retraining cadence has **not** been evaluated (KNOWN_LIMITATIONS #10).

## Verified (2026-10-23)
| Item | Status | How |
|---|---|---|
| Local API + PWA on real gold data | PASS | `uvicorn` on :8000; `/ready` returns `data_as_of 2026-04-20, model fc_main_v3`. The PWA was walked through in Tamil in the built-in browser at 375 px |
| Container image | PASS | `docker build -f Dockerfile.api` (2 s with `.dockerignore`). The container runs as uid 10001, reaches health `healthy`, serves `/` (200), and `/api/docs` is off (404) |
| HDFS data lake | PASS (single host) | `results/hdfs/summary.md` |
| Kafka + Structured Streaming | see `results/streaming/demo_summary.json` | `scripts/streaming_demo.sh` |
| Public cloud deployment | **BLOCKED** | no cloud account or credentials available. No URL exists |
| Physical 4 GB Android phone | **NOT RUN** | — |
