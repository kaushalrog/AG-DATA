# Security, privacy and operational safety

## Secrets
* The only secret is the optional data.gov.in API key, `AGRI_DATA_GOV_IN_API_KEY`, read from the environment. `.env.example` holds a blank placeholder. `.env` is git-ignored.
* `DataGovInClient` keeps the key out of logs, exceptions and checkpoints:
  * the key is redacted from every error message;
  * provenance URLs are built without the `api-key` parameter;
  * checkpoints store only these key-free URLs.

  Tests `test_fetch_paginates_validates_and_redacts` and `test_gives_up_after_max_retries_without_leaking_key` check this.
* The frontend contains **no secrets**. The static app calls only the project's own API.
* No key is present in the repository or its Git history (checked with `git log -p | grep -i api-key` during the final audit).

## Public surface
* **Public:** the API (`/api/v1/*`, GET only) and the static PWA, served by the same process or by a static host.
* **Private:** HDFS (9870/9000/9864–9866), Kafka (9092), the Spark UI (4040) and the Docker network. `docker/docker-compose.yml` publishes HDFS ports to the developer machine only. In any cloud deployment they must be bound to a private subnet or security group, never 0.0.0.0 on a public host.

## API hardening (`py/agri/api/app.py`)
* **Read-only.** Every query is parameterised through DuckDB `?` binding. The only interpolated values are the integers `LIMIT` and `OFFSET`, validated by FastAPI as bounded ints.
* **Input validation.** String filters are at most 64 characters with no control characters. Enums use regex patterns. Numeric parameters are range-checked. Unknown ids return 404.
* **Errors.** Errors come back as `{"error":{"code","message"}}`. Unhandled exceptions return a generic 500. Stack traces, file paths, HDFS URIs and infrastructure names are never returned (`test_not_ready_without_gold` asserts the gold path is not leaked).
* **Rate limiting.** A token bucket per client IP (`AGRI_API_RATE_PER_MIN`), kept in memory. Behind a reverse proxy, configure the proxy to forward the real client address, and add limiting at the edge too (Cloudflare or nginx `limit_req`).
* **CORS.** Allow-list from `AGRI_API_CORS_ORIGINS`, GET only. The default allows only the local origin.
* **Headers.** `X-Content-Type-Options: nosniff` is set. When behind TLS, the proxy should also set CSP and HSTS.

## Privacy
* No accounts, no personal data and no analytics.
* The app stores language, default location and cost assumptions in `localStorage` on the device only. Settings has a "clear saved data" control.
* The service worker caches only public market data, never request bodies or anything user-specific.

## Data and model integrity
* Models are written as Spark `PipelineModel` directories under an experiment id. The manifest records git commit, dirty flag, Spark/Java versions, seed and data ranges. Load models only from trusted storage: Spark ML deserialisation is not designed for untrusted input.
* The gold layer is produced by batch jobs and mounted read-only by the API.

## Containers
* The Hadoop images run as root to match the existing volumes (development only) and use `dfs.permissions.enabled=false`. For a shared deployment:
  * enable HDFS permissions;
  * run DataNodes as a non-root user;
  * put the cluster on a private network;
  * use Kerberos if more than one team uses it.

## Dependency hygiene
* Python dependencies are declared in `pyproject.toml`. Run `pip-audit` (or `uv pip audit`) in CI. Scala dependencies are pinned in `build.sbt`. The PWA has no third-party runtime dependencies.

## Safe operations
* No script deletes user data. `scripts/hdfs_setup.sh destroy` asks for confirmation. `BuildForecastFeatures` deletes only its own `_stage_*` intermediates.
