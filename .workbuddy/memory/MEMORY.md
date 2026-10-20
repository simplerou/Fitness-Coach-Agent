# 项目长期记忆 — fitness-coach-agent

## 启动与本地环境（实测确认）

- **PostgreSQL**：Windows 服务名 `postgresql-x64-18`。默认不随开机自启，需管理员 `net start postgresql-x64-18`；未启动时后端启动会连库失败。
- **后端解释器必须用** `D:/Anaconda/python.exe`（依赖装在这里：fastapi/uvicorn/sqlalchemy/psycopg3/langgraph 等）。裸 `python` 会解析到 managed 3.13.12，缺依赖。
- **后端启动命令**（项目根目录）：`D:/Anaconda/python.exe -m uvicorn app.main:app --reload --app-dir backend` → http://127.0.0.1:8000
- **前端开发服务器**：`cd web && npm run dev`。Vite 7 只监听 IPv6 `[::1]:5173`，**必须用 http://localhost:5173**，`127.0.0.1:5173` 会连不上。`/api` 已配置代理到 8000。
- **单端口模式**：`npm --prefix web run build` 生成 `web/dist` 后，FastAPI 以 `/static` 同源托管，只开 8000 即可。

## 架构事实（易误解）

- **2026-10-20 塑型扩展例外**：新增 `/api/shaping*` 路由实际位于 `app/api/shaping.py`，在 main.py 的 SPA 回退前挂载；实体在 `models/shaping.py`、校验在 `schemas/shaping.py`、服务在 `services/shaping_service.py`。新增 `shape_measurements` / `shape_targets` / `shape_photos` 三表，已通过现有启动流程创建。以下“全部路由在 main.py、api/models/schemas 为空”是扩展前的记录，不能再作为当前结论。

- **41 个 HTTP 路由全部在 `backend/app/main.py`**（约 1900 行），启动时 `lifespan` 调 `initialize_database()` 建表 + 幂等 ALTER 迁移。
- `app/api/`、`app/models/`、`app/schemas/`、`app/orchestration/`、`app/tasks/`、`alembic/versions/` 基本是 **0 字节占位**，未接线；`docker-compose.yml` 是空文件。改接口就去 main.py，不要以为 api/ 里有实现。
- 数据库表由 SQLAlchemy `create_all` 在运行时管理，**不是 Alembic**。
- `.env` 含真实密钥（DB 密码 / BOOHEE_API_KEY / DASHSCOPE_API_KEY），已被 `.gitignore` 忽略，不可提交或外传。

## 工具坑（archify）

- archify（v3.2.0，github.com/tt-a1i/archify）在本项目 D: 盘路径下**无法交付**：其原子发布要求目标文件 `nlink === 1`，实际报 2，最终 `finalize` 报 `finalize/receipt-publication`、`render` 报 `[output/target-hardlinked]`。
- **做法**：在 `C:/Users/24234/AppData/Local/Temp/archify-out/` 里跑 `finalize`（同参数一次通过），再把 HTML `cp` 回项目；`validate` / `check` 等只读命令在 D: 盘正常。
- 已产出：`docs/architecture/fitness-coach-agent-architecture.html`（候选 JSON 在 `.archify/architecture-fitness-coach-agent-20261020-100523/`）。
