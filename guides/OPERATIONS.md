# Operations guide

[Project overview](../README.md) · [Chinese guide](OPERATIONS_CN.md)

## Configuration

The default Compose deployment uses MySQL and exposes only `127.0.0.1:8080`. The API and database do not publish host ports.

| Variable | Purpose |
| --- | --- |
| `MYSQL_DATABASE`, `MYSQL_USER` | Application database and database user |
| `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD` | Database credentials; replace local defaults before shared deployment |
| `WEB_PORT` | Local web port, default 8080 |
| `APP_ORIGINS` | Exact allowed browser origins, separated by commas |
| `COOKIE_SECURE` | Set to `true` when using HTTPS |
| `DATABASE_URL` | Optional direct-development database URL; Compose constructs its own MySQL URL |

The Compose database URL interpolates the password directly: use URL-safe characters such as letters, digits, underscores, and hyphens in this configuration. Changing MySQL initialization variables does not change credentials in an existing volume.

For an HTTPS deployment, point your reverse proxy to the web service, configure the exact origin including any non-default port, and enable secure cookies. Compose sets `TRUST_PROXY=true` for the internal API; Nginx overwrites X-Real-IP. Do not expose that API directly while trusting proxy headers.

## Backup and restore

Run the following from the repository root using **PowerShell**. Files are copied through Docker to avoid PowerShell changing SQL dump encoding. The commands read credentials inside the container.

```powershell
New-Item -ItemType Directory -Force data/backups | Out-Null
docker compose exec -T mysql sh -c 'MYSQL_PWD="$MYSQL_PASSWORD" mysqldump -u "$MYSQL_USER" --single-transaction --no-tablespaces --set-gtid-purged=OFF --result-file=/tmp/stockgod-backup.sql "$MYSQL_DATABASE"'
docker compose cp mysql:/tmp/stockgod-backup.sql data/backups/stockgod-backup.sql
```

Keep dated copies before upgrades. To check a backup, restore it into a **new verification database**, leaving the active database untouched:

```powershell
docker compose exec -T mysql sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -u root -e "CREATE DATABASE stockgod_restore_check CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs"'
docker compose cp data/backups/stockgod-backup.sql mysql:/tmp/stockgod-restore.sql
docker compose exec -T mysql sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -u root stockgod_restore_check < /tmp/stockgod-restore.sql'
docker compose exec -T mysql sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -u root stockgod_restore_check -e "SELECT count(*) AS players FROM players; SELECT sum(cash_delta) AS ledger_cash FROM ledger;"'
```

Use a different verification database name if one already exists. Check row counts and application behavior before planning a downtime window to switch databases. Also retain `content/`, `data/market/`, and deployment configuration.

Full database backups contain password hashes and sessions. Personal JSON exports contain only the signed-in user's business records, including review items and review attempts. They are intended for inspection and do not replace a restorable database backup.

## Legacy anonymous records

Older versions stored one anonymous player named `local`. Migrations preserve that player and never assign its records to the first person who registers.

After confirming ownership, an administrator can bind the legacy player to a **newly registered account without learning, trading, or experiment activity**:

```sh
docker compose exec -T api python scripts/claim-legacy.py YOUR_REGISTERED_USERNAME
```

The tool reuses the registered account's password hash and revokes its sessions. Sign in again after binding. It refuses to overwrite an active account and is not exposed as an HTTP endpoint.

`scripts/transfer-database.py` exports old anonymous PostgreSQL records and imports them into an empty target database. It validates table counts and the ledger sum before committing. Use full database backups for registered-user deployments.

## Review behavior

The versioned review bank is `content/questions/reviews-v1.json`. Each original quiz question maps to one knowledge point with two alternative cases.

A mistake becomes immediately due. A successful review schedules the next attempt after 1 day, then 3 days, then 7 days. The fourth successful attempt completes that cycle. An incorrect answer resets the stage and makes another case available immediately. These are elapsed 24-hour intervals, independent of the simulated market clock; displayed dates use Asia/Shanghai.

The server validates ownership, case version, revision, and the due time. Old tabs cannot submit outdated cases. Retrying the same request returns its original result. Review records do not grant XP or unlock a course; course quizzes retain their own completion rules.

## MySQL regression tests

Tests rebuild tables, so only the dedicated database name `stockgod_tests` is accepted. Start a disposable MySQL instance:

```powershell
docker run --rm -d --name stockgod-mysql-test -p 127.0.0.1:55433:3306 -e MYSQL_ROOT_PASSWORD=stockgod_test_root -e MYSQL_USER=stockgod -e MYSQL_PASSWORD=stockgod_test_only -e MYSQL_DATABASE=stockgod_tests mysql:8.4.6
# Wait until the test database is ready, then:
$env:TEST_DATABASE_URL='mysql+pymysql://stockgod:stockgod_test_only@127.0.0.1:55433/stockgod_tests?charset=utf8mb4'
.\.venv\Scripts\python.exe -m pytest tests -q
Remove-Item Env:TEST_DATABASE_URL
docker stop stockgod-mysql-test
```

## Browser tests

Use three terminals. The API helper creates a fresh SQLite file by default and runs a test worker. Do not point it at a real player's database.

```powershell
# Terminal 1, repository root
.\.venv\Scripts\python.exe scripts/serve-e2e.py
```

```powershell
# Terminal 2, repository root
cd frontend
$env:API_TARGET='http://127.0.0.1:8001'
node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5174
```

```powershell
# Terminal 3, repository root
cd frontend
npx.cmd playwright install chromium
$env:E2E_BASE_URL='http://127.0.0.1:5174'
npm.cmd run test:e2e
```

## Before committing

`.gitignore` excludes `.env`, runtime data, backups, dependencies, build output, and local `docs/` working documents. Public instructions live in `guides/`; README screenshots live in `.github/assets/`. Preserve these exclusions when contributing.
