# Third-party notices

Direct dependencies are pinned in `frontend/package.json` and `backend/pyproject.toml`; transitive resolutions are recorded in the package lock and `backend/requirements.lock`. This notice does not assign a license to the user's application code or reference artwork.

| Component | Version | License |
| --- | --- | --- |
| React / React DOM | 19.2.0 | MIT |
| React Router DOM | 7.18.3 | MIT |
| TanStack Query | 5.90.7 | MIT |
| Tailwind CSS | 4.1.17 | MIT |
| Radix Dialog / Slot | 1.1.15 / 1.2.3 | MIT |
| class-variance-authority | 0.7.1 | Apache-2.0 |
| clsx / tailwind-merge | 2.1.1 / 3.3.1 | MIT |
| Motion | 12.23.24 | MIT |
| ECharts | 6.1.0 | Apache-2.0 |
| Lucide React | 0.552.0 | ISC |
| i18next / react-i18next | 26.4.2 / 17.0.13 | MIT |
| React Markdown | 10.1.0 | MIT |
| FastAPI | 0.121.1 | MIT |
| Pydantic | 2.12.4 | MIT |
| SQLAlchemy / Alembic | 2.0.44 / 1.17.1 | MIT |
| PyMySQL | 1.1.2 | MIT |
| pwdlib / argon2-cffi | 0.3.0 / 25.1.0 | MIT |
| cryptography | 50.0.1 | Apache-2.0 OR BSD-3-Clause |
| psycopg (legacy transfer) | 3.2.12 | LGPL-3.0-only |
| APScheduler | 3.11.1 | MIT |
| DuckDB | 1.4.1 | MIT |
| PyArrow | 22.0.0 | Apache-2.0 |
| vn.py event core | 4.2.0 | MIT, Copyright 2015-present Xiaoyou Chen |

The unchanged vn.py event module and its full upstream license are included in `backend/src/stock_god/_vendor/vnpy_event/`. Its upstream provenance and SHA-256 are recorded in `docs/技术决策与实现范围.md`. Only its event framework is vendored; no brokerage gateway is included.

The custom Button and Dialog primitives compose Radix and class-variance-authority following shadcn-style composition; no third-party admin template is used. Fonts use the user's system fonts.

Package metadata and bundled license files were inspected during implementation. Preserve applicable licenses and notices when redistributing dependencies; psycopg carries LGPL obligations. Database/server/container images have their own distributions and license notices (MySQL Community Server GPL-2.0 distribution, legacy PostgreSQL license, Nginx BSD-style license, and base-image package licenses). No market-data redistribution rights are implied by software licenses.

User-provided artwork remains user-provided content. The two-page UI concept board was generated using the built-in imagegen tool for this project and is stored locally under `docs/concepts/`.

Bundled narration under `content/narration/` was synthesized from the project’s lesson text and preset coach explanations with Windows System.Speech (Microsoft Huihui Desktop and Microsoft Zira Desktop), then encoded as MP3 with FFmpeg/libmp3lame. The manifest records voice names, text versions, durations, and file hashes. These are synthesized recordings, not human voice recordings. Windows speech engines and FFmpeg are build tools and are not redistributed in the runtime images. The application serves the generated MP3 files using standard browser audio playback.
