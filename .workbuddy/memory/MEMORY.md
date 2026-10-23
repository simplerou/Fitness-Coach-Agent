# 项目长期记忆 — fitness-coach-agent

## 启动与本地环境（实测确认）

- **PostgreSQL**：Windows 服务名 `postgresql-x64-18`。默认不随开机自启，需管理员 `net start postgresql-x64-18`；未启动时后端启动会连库失败。
- **后端解释器必须用** `D:/Anaconda/envs/agent_env/python.exe`（2026-10-21 实测：base Anaconda 只有 fastapi/uvicorn/sqlalchemy/psycopg，**缺 langgraph / langchain-openai / chromadb / jieba**；`envs/agent_env` 八个包齐全）。裸 `python` 会解析到 managed 3.13.12，同样缺依赖。
- **后端启动命令**（项目根目录）：`D:/Anaconda/envs/agent_env/python.exe -m uvicorn app.main:app --reload --app-dir backend` → http://127.0.0.1:8000
- **前端开发服务器**：`cd web && npm run dev`。Vite 7 只监听 IPv6 `[::1]:5173`，**必须用 http://localhost:5173**，`127.0.0.1:5173` 会连不上。`/api` 已配置代理到 8000。
- **单端口模式**：`npm --prefix web run build` 生成 `web/dist` 后，FastAPI 以 `/static` 同源托管，只开 8000 即可。

## 架构事实（易误解）

## 架构事实（2026-10-21 下午重构后，以此为准）

- **已拆分完毕**：`app/main.py` 只剩 124 行装配代码（中间件 + `/`、`/api/health`、SPA fallback 三个基础路由 + 13 次 `include_router`）。**60 个业务接口都在 `app/api/` 的 13 个模块里**（auth 4 / safety 1 / daily_signal 1 / plan 4 / profile 5 / today 1 / diet 11 / diet_plan 2 / log 3 / review 1 / shaping 8 / shaping_intelligence 10 / training_intelligence 9）。
- **模块实现度**：models 10 个模块（新增 `base.py`、`diet.py`）、schemas 10 个（新增 `auth.py`、`diet.py`）、services 18 个（新增 `diet_targets.py`、`diet_plan_analysis.py`、`training_plan_agent.py`）——**全部有实现，已无 0 字节占位**。
- **已删除的清空项**：`app/decision`、`app/orchestration`、`app/tasks`、`app/tools`（目录只剩 `__pycache__`）、`core/config.py`、`core/logging_conf.py`、`backend/Dockerfile`、`backend/alembic.ini`、`alembic/env.py`、`alembic/script.py.mako`、`evals/cases.yaml`、`evals/run_evals.py`。`docker-compose.yml` 仍是 0 字节，`backend/alembic/versions/` 仍是空目录。
- **数据与检索**：表由 `initialize_database()` 运行时 create_all + 幂等 ALTER 管理（**不是 Alembic**）；`backend/migrations/` 放 3 个手写 SQL；`backend/scripts/` 是种子与索引脚本；`backend/.chroma/` 是 Chroma 持久化目录，`services/exercise_knowledge.py` = jieba BM25 + Chroma + RRF 混合检索。
- **外部依赖**：饮食 Agent、塑形 Agent、周训练安排 Agent 都走通义千问（LangGraph 工作流）；`boohee_food_service.py` 走薄荷开放 API。
- **前端**：`web/src` 下 8 个 views、14 个 components 业务域目录（77 个组件）、11 个 api 模块 + `api/types/` 7 个类型文件、11 个 stores、15 个 styles（含 6 个 `legacy-*.css`，由 `main.css` @import）；`web/dist` 由 FastAPI 以 `/static` 托管。
- `.env` 含真实密钥（DB 密码 / BOOHEE_API_KEY / DASHSCOPE_API_KEY），已被 `.gitignore` 忽略，不可提交或外传。

## 工具坑（archify）

- archify（v3.2.0，github.com/tt-a1i/archify）在本项目 D: 盘路径下**无法交付**：其原子发布要求目标文件 `nlink === 1`，实际报 2，最终 `finalize` 报 `finalize/receipt-publication`、`render` 报 `[output/target-hardlinked]`。
- **做法**：在 `C:/Users/24234/AppData/Local/Temp/archify-out/` 里跑 `finalize`（同参数一次通过），再把 HTML `cp` 回项目；`validate` / `check` 等只读命令在 D: 盘正常。
- 已产出：`docs/architecture/fitness-coach-agent-architecture.html`（运行架构，候选在 `.archify/architecture-fitness-coach-agent-20261020-100523/`）、`docs/architecture/project-folder-map.html`（目录结构树，候选在 `.archify/tree-project-map-20261021-085800/`）。
- tree 类型布局实测：仓库树用 `direction: "right"` 在 1440 宽下高 1909px，又高又窄；改 `"down"` 会把连续叶子收成缩进列表，高度降到 1012px，更好读。
