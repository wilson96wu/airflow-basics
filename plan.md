# Clean Airflow Project Init (vanilla, no GCS/terraform)

## Already done
- [x] Removed `airflow_gcs_setup_guide.md` (was for a different GCS/terraform exercise)
- [x] `git init` (default branch is `master` — rename with `git branch -m main` if you want `main`)
- [x] Created `dags/`, `logs/`, `plugins/`, `config/`

## Remaining steps

1. **Add `.gitignore`**:
   ```
   logs/
   plugins/
   config/
   .env
   __pycache__/
   *.pyc
   ```
   (Track `dags/` and the compose file.)

2. **Get the official Compose file**:
   ```bash
   curl -LfO 'https://airflow.apache.org/docs/apache-airflow/stable/docker-compose.yaml'
   ```

3. **Create `.env`**:
   ```bash
   echo "AIRFLOW_UID=$(id -u)" > .env
   python3 -c "import os, base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
   # append the printed value as FERNET_KEY=<generated> in .env
   ```

4. **Add a minimal example DAG** at `dags/hello_world.py` (plain TaskFlow API, no external
   provider) — e.g. a two-task DAG that prints a greeting and today's date, so there's
   something to verify Airflow against.

5. **Initialize and start Airflow**:
   ```bash
   docker compose up airflow-init
   docker compose up -d
   ```

6. **Add a short `README.md`** documenting: prerequisites, how to start/stop
   (`docker compose up -d` / `docker compose down`), and where DAGs live.

## Prerequisites (already verified on this machine)
- Docker `29.6.2` (Compose `v5.3.1`), daemon running ✓
- Docker Desktop resources: 14 CPUs / ~7.75 GB RAM — official quick-start recommends ≥8GB.
  Bump to 8GB in Docker Desktop → Settings → Resources before starting Airflow (manual,
  not scriptable).
- Python `3.14.6` ✓ (used to generate the Fernet key)
- Git `2.54.0` ✓

## Verification
- `docker compose ps` — all services (webserver, scheduler, triggerer, postgres) healthy.
- Open http://localhost:8080, log in with `airflow` / `airflow`.
- Confirm `hello_world` appears in the DAGs list, unpause and trigger it, check the task
  logs show the expected output.
- `docker compose down` cleanly stops everything afterward if desired.
