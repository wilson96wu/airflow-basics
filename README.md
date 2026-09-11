# Airflow (LocalExecutor) — Setup From Scratch

A runbook for reproducing this project from an empty directory. Airflow 3.3.1,
`LocalExecutor`, Postgres as the metadata DB, pgAdmin for DB inspection.

## Prerequisites
- Docker Desktop installed, running, with ≥8GB RAM / 2 CPUs allocated
  (Docker Desktop → Settings → Resources)
- `git`, `python3` available locally (python3 only needed to generate secrets)

## 1. Scaffold folders and git

```bash
git init
mkdir -p dags logs plugins config
```

`.gitignore`:
```
logs/
plugins/
config/
.env
__pycache__/
*.pyc
.DS_Store
```

## 2. `.env` — shared secrets

```bash
echo "AIRFLOW_UID=$(id -u)" > .env
python3 -c "import base64, os; print('FERNET_KEY=' + base64.urlsafe_b64encode(os.urandom(32)).decode())" >> .env
python3 -c "import secrets; print('JWT_SECRET=' + secrets.token_urlsafe(32))" >> .env
```

- `FERNET_KEY` encrypts connection/variable secrets at rest in the metadata DB.
- `JWT_SECRET` signs/validates the tokens tasks use to authenticate to the Airflow
  API server. **Must be identical across every Airflow container** (scheduler,
  api-server, dag-processor) — if left unset, each process generates its own
  random key and every task fails with `Invalid auth token`.

## 3. Compose files

Split into `docker-compose.infra.yaml` (Postgres + pgAdmin) and
`docker-compose.airflow.yaml` (the Airflow services), included from a top-level
`docker-compose.yaml`:

```yaml
# docker-compose.yaml
include:
  - docker-compose.infra.yaml
  - docker-compose.airflow.yaml
```

```yaml
# docker-compose.infra.yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
      POSTGRES_DB: airflow
    volumes:
      - postgres-db-volume:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "airflow"]
      interval: 10s
      retries: 5
      start_period: 5s
    restart: always

  pgadmin:
    image: dpage/pgadmin4
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@admin.com
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"
    depends_on:
      - postgres

volumes:
  postgres-db-volume:
```

```yaml
# docker-compose.airflow.yaml
x-airflow-common:
  &airflow-common
    image: ${AIRFLOW_IMAGE_NAME:-apache/airflow:3.3.1}
    env_file:
      - ${ENV_FILE_PATH:-.env}
    environment:
      &airflow-common-env
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__CORE__AUTH_MANAGER: airflow.providers.fab.auth_manager.fab_auth_manager.FabAuthManager
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres/airflow
      AIRFLOW__WORKERS__EXECUTION_API_SERVER_URL: http://airflow-apiserver:8080/execution/
      AIRFLOW__API_AUTH__JWT_SECRET: ${JWT_SECRET}
    volumes:
      - ./dags:/opt/airflow/dags
      - ./logs:/opt/airflow/logs
      - ./plugins:/opt/airflow/plugins
      - ./config:/opt/airflow/config

services:
  airflow-init:
    <<: *airflow-common
    command: db migrate
    restart: on-failure
    depends_on:
      postgres:
        condition: service_healthy

  airflow-apiserver:
    <<: *airflow-common
    command: api-server
    ports:
      - "8080:8080"
    depends_on:
      airflow-init:
        condition: service_completed_successfully

  airflow-scheduler:
    <<: *airflow-common
    command: scheduler
    depends_on:
      airflow-init:
        condition: service_completed_successfully

  airflow-dag-processor:
    <<: *airflow-common
    command: dag-processor
    depends_on:
      airflow-init:
        condition: service_completed_successfully
```

### Gotchas this config avoids (learned the hard way)
- **`volumes:` on `x-airflow-common` is mandatory.** Without it, none of the
  containers can see `dags/`, and `airflow dags list` silently returns nothing.
- **Airflow 3.x needs a dedicated `airflow-dag-processor` service.** The
  scheduler no longer parses DAG files itself (unlike Airflow 2.x) — without
  this service, DAGs never get parsed even if the folder is mounted correctly.
- **`airflow-apiserver` needs `ports: ["8080:8080"]`** or the UI is unreachable
  from the host.
- **The execution-API URL env var is `AIRFLOW__WORKERS__EXECUTION_API_SERVER_URL`,
  not `AIRFLOW__EXECUTION_API__EXECUTION_API_SERVER_URL`.** The latter is a
  same-named-but-unrelated config key; the executor's own client code reads
  `[workers] execution_api_server_url` (deprecated alias: `[core]`). Get this
  wrong and every task fails with `Connection refused` trying to reach
  `localhost:8080` (nothing listens there in the scheduler container).
- **`AIRFLOW__API_AUTH__JWT_SECRET` must be shared** across all Airflow
  services (see `.env` note above) or tasks fail with `Invalid auth token`.
- No `redis` / Celery config — not needed for `LocalExecutor`. Only add
  `redis` + `airflow-worker` + `AIRFLOW__CELERY__*` if switching to
  `CeleryExecutor`.

## 4. Bring it up

```bash
docker compose up airflow-init
docker compose up -d
```

Create a login user (FabAuthManager has no default admin/admin, unlike
`airflow standalone`):

```bash
docker compose exec airflow-apiserver airflow users create \
  --username admin --password admin \
  --firstname Admin --lastname User \
  --role Admin --email admin@example.com
```

## 5. Verify

```bash
docker compose ps                                    # all services healthy/up
docker compose exec airflow-scheduler airflow dags list         # local_executor_demo shows up
docker compose exec airflow-scheduler airflow dags trigger local_executor_demo
docker compose exec airflow-scheduler airflow dags list-runs local_executor_demo   # state: success
```

Open [http://localhost:8080](http://localhost:8080) (admin/admin) to see it in
the UI, and [http://localhost:5050](http://localhost:5050) (admin@admin.com/admin)
for pgAdmin — add a server there with host `postgres`, port `5432`, user/password
`airflow`/`airflow`.

## 6. Example DAG

`dags/local_executor_demo.py` — three independent tasks that each sleep 5s and
print their PID + start/end time, proving `LocalExecutor` runs them concurrently
(different PIDs, overlapping timestamps) rather than one-at-a-time.

## Teardown

```bash
docker compose down          # stop + remove containers, keep the postgres volume
docker compose down -v       # also wipe the postgres volume (full reset)
```
