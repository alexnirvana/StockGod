# 运维说明

[项目介绍](../README_CN.md) · [英文运维说明](OPERATIONS.md)

## 配置

默认 Compose 使用 MySQL，只开放 `127.0.0.1:8080`。API 和数据库不发布宿主机端口。

| 变量 | 用途 |
| --- | --- |
| `MYSQL_DATABASE`、`MYSQL_USER` | 业务数据库与数据库用户 |
| `MYSQL_PASSWORD`、`MYSQL_ROOT_PASSWORD` | 数据库密码，共享部署前替换本地默认值 |
| `WEB_PORT` | 本机入口端口，默认 8080 |
| `APP_ORIGINS` | 允许的浏览器来源，多个来源用逗号分隔 |
| `COOKIE_SECURE` | 使用 HTTPS 时设为 `true` |
| `DATABASE_URL` | 直接开发时可指定；Compose 自动构造 MySQL 连接地址 |

Compose 直接将密码放入数据库 URL，当前配置请使用字母、数字、下划线、连字符等 URL 安全字符。修改 MySQL 初始化环境变量，不会改变已有数据卷中的密码。

部署到 HTTPS 域名时，将反向代理指向 Web，设置准确来源（含非默认端口），开启安全 Cookie。Compose 仅对内部 API 设置 `TRUST_PROXY=true`，Nginx 覆盖 X-Real-IP。信任代理请求头时，不要把 API 直接对外开放。

## 备份与恢复

以下命令在项目根目录的 **PowerShell** 中执行，通过 Docker 传递文件，避免 PowerShell 改变 SQL 编码。密码在容器内部读取。

```powershell
New-Item -ItemType Directory -Force data/backups | Out-Null
docker compose exec -T mysql sh -c 'MYSQL_PWD="$MYSQL_PASSWORD" mysqldump -u "$MYSQL_USER" --single-transaction --no-tablespaces --set-gtid-purged=OFF --result-file=/tmp/stockgod-backup.sql "$MYSQL_DATABASE"'
docker compose cp mysql:/tmp/stockgod-backup.sql data/backups/stockgod-backup.sql
```

升级前保留带日期的备份副本。先恢复到**新的核验库**，保留当前业务库：

```powershell
docker compose exec -T mysql sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -u root -e "CREATE DATABASE stockgod_restore_check CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_as_cs"'
docker compose cp data/backups/stockgod-backup.sql mysql:/tmp/stockgod-restore.sql
docker compose exec -T mysql sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -u root stockgod_restore_check < /tmp/stockgod-restore.sql'
docker compose exec -T mysql sh -c 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -u root stockgod_restore_check -e "SELECT count(*) AS players FROM players; SELECT sum(cash_delta) AS ledger_cash FROM ledger;"'
```

核验库已存在时请换一个新名称。核对表数量与应用行为后，再安排停服切换。同时保留 `content/`、`data/market/` 和部署配置。

完整数据库备份包含密码哈希和会话。个人 JSON 导出仅包含当前账号的业务记录，包括复习项和复习作答；用于查阅，不代替可恢复的完整数据库备份。

## 旧匿名记录绑定

旧版将单个匿名玩家记录为 `local`。升级保留该玩家，不会自动将记录归给第一个注册的人。

管理员确认归属后，原使用者先注册一个**尚未进行课程、交易和实验**的新账号，再运行：

```sh
docker compose exec -T api python scripts/claim-legacy.py 你的注册用户名
```

工具复用注册账号的密码哈希，撤销原会话，绑定后重新登录。目标账号已有业务活动时拒绝覆盖，该能力不通过 HTTP 开放。

`scripts/transfer-database.py` 可导出旧匿名 PostgreSQL 记录，导入全空目标库，核验逐表数量与账本合计后提交。已注册用户的部署应使用完整数据库备份。

## 复习规则

题库位于 `content/questions/reviews-v1.json`。每道原始课程题目映射一个知识点，包含两个替换案例。

答错后立即进入待复习列表。第一次复习答对后间隔 1 天，第二次后间隔 3 天，第三次后间隔 7 天，第四次答对完成本轮巩固。答错重置阶段，立即提供另一个案例。这里的一天表示经过 24 小时，与模拟行情时钟无关；页面按北京时间显示。

服务端校验账号归属、题库版本、进度修订号与到期时间。旧标签页不能提交过期题目，同一请求重试返回原结果。复习不发放经验、不解锁章节，课程仍按独立完成标准判定。

## MySQL 回归测试

测试会重建表，因此只允许专用数据库 `stockgod_tests`。启动一次性测试实例：

```powershell
docker run --rm -d --name stockgod-mysql-test -p 127.0.0.1:55433:3306 -e MYSQL_ROOT_PASSWORD=stockgod_test_root -e MYSQL_USER=stockgod -e MYSQL_PASSWORD=stockgod_test_only -e MYSQL_DATABASE=stockgod_tests mysql:8.4.6
# 等待测试库就绪后：
$env:TEST_DATABASE_URL='mysql+pymysql://stockgod:stockgod_test_only@127.0.0.1:55433/stockgod_tests?charset=utf8mb4'
.\.venv\Scripts\python.exe -m pytest tests -q
Remove-Item Env:TEST_DATABASE_URL
docker stop stockgod-mysql-test
```

## 浏览器测试

打开三个终端。API 辅助脚本默认创建全新 SQLite 文件并运行测试 Worker，不要指定为真实用户数据库。

```powershell
# 终端一，项目根目录
.\.venv\Scripts\python.exe scripts/serve-e2e.py
```

```powershell
# 终端二，项目根目录
cd frontend
$env:API_TARGET='http://127.0.0.1:8001'
node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5174
```

```powershell
# 终端三，项目根目录
cd frontend
npx.cmd playwright install chromium
$env:E2E_BASE_URL='http://127.0.0.1:5174'
npm.cmd run test:e2e
```

## 提交代码前

`.gitignore` 已排除 `.env`、运行数据、备份、依赖、构建产物与本地 `docs/` 工作文档。公开说明位于 `guides/`，README 截图位于 `.github/assets/`。参与开发时保留这些排除规则。
