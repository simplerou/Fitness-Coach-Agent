# fitness-coach-agent

个性化健身运动规划智能体。当前实现 **V1.1.0 本机可运行基础版**，使用浏览器原生 HTML/CSS/JavaScript、FastAPI 和本机 PostgreSQL。

## V1.1 功能

- 今日安全筛查；未完成或命中症状时不生成训练建议，并设置会话内安全暂停
- 手动记录主观状态、睡眠和静息心率；状态较差时给出保守的降负荷提示
- 按目标与每周训练天数生成基础计划模板
- 训练状态与训练日志保存在 PostgreSQL，服务重启后仍可查看
- 安全暂停状态和周计划仍保存在服务进程内存中；服务重启后需重新筛查并生成计划
- 页面由 FastAPI 同源托管，无需 Node、npm 或 Docker

## 准备 PostgreSQL

1. 启动本机 PostgreSQL 服务，并连接移动硬盘（若 PostgreSQL 数据目录位于移动硬盘）。
2. 在项目目录复制环境模板：

   ```powershell
   Copy-Item .env.example .env
   ```

3. 编辑 `.env`，填写创建的 `fitness_app` 密码：

   ```text
   DATABASE_URL=postgresql+psycopg://fitness_app:你的密码@127.0.0.1:5432/fitness_coach
   ```

   密码若含 `@`、`/`、`:`、`#` 等字符，需要进行 URL 编码。`.env` 已加入 Git 忽略列表，切勿提交真实密码。

4. 首次启动时，应用会自动创建 `daily_signals` 和 `training_logs` 表。

## 安装与运行

在项目根目录执行：

```powershell
python -m pip install -r backend/requirements.txt
python -m uvicorn app.main:app --reload --app-dir backend
```

浏览器打开 <http://127.0.0.1:8000>。PostgreSQL 服务必须保持运行；若数据目录在移动硬盘上，运行期间不要拔出硬盘。

## V1.1 边界

这是单用户本机流程演示，不是可供真实用户使用的健康产品。每日状态和训练日志写入本机 PostgreSQL；安全筛查暂停状态和计划仍是会话内数据。尚无账号、权限隔离、迁移工具、正式部署和专业审阅。请勿输入真实健康信息，也不要把演示计划当作医疗或个体化处方。

## 版本路线

- **V1.0.0**：本机可运行的 Web + FastAPI 最小闭环，数据暂存内存。
- **V1.1.0**：接入本机 PostgreSQL，持久化每日状态和训练日志。
- **后续 V1.x**：历史趋势、周回顾、校验和错误提示完善。
- **V2**：评估账号、数据授权与删除、数据库迁移管理及正式部署。
- **后续**：依据用户反馈评估小程序与健康数据接入。

实现问题和解决经过记在同级文件 `../问题与解决方案.md`；迭代计划见 `docs/roadmap.md`。
