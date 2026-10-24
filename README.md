# 个性化健身运动规划智能体

面向个人训练与日常记录的本机 Web 应用。用户可以管理训练计划、记录饮食与身体变化，并在明确授权后使用 AI 教练获得基于项目知识库和个人业务摘要的答复。

## 功能概览

### 训练与日常状态
- 今日页面展示当天训练安排或休息日，并提供当日安全确认；报告不适或无法判断时暂停当天训练建议。该确认不会阻挡查看其他日期的计划和记录。
- 按训练目标、经验、每周训练日、可用器械和时长生成周计划，保存当前计划并回看历史周计划。
- 记录训练完成情况、动作、主观强度等信息；周回顾按日对照计划和实际记录，并提供由用户决定是否采纳的调整参考。
- 动作库支持按动作信息检索。

### 饮食与身体变化
- 按日期记录餐食、分量、进食时间和营养值，并累计饮水。
- 根据身体档案、饮食偏好、健康约束和已完成的饮食记录进行营养分析与饮食规划；规划结果保存为可回看的历史快照。营养信息受实际录入资料影响，不会把缺失值默认为零。
- 记录体重、围度、体脂率、骨骼肌等实测数据，查看趋势、复测提醒、目标进度和身体照片时间线。
- 支持周回顾和阶段报告。没有记录的数据会明确标记，不从缺失值推断结果。

### AI 教练与知识库
- AI 教练使用 LangGraph ReAct 流程，按需读取当前账号的训练、恢复、饮食和身体变化摘要，并可查询动作知识。
- 本地知识检索使用中文 BM25；配置并授权云端检索时，可使用 Chroma 向量检索并通过 RRF 融合。
- CRAG 在本地混合检索之后评估资料相关度。资料不足、用户本轮已授权且配置 Tavily 时，才进行联网补充；联网结果不会自动加入知识库。
- 教练可准备饮食目标或下周训练调整草案。用户确认后才会保存变更。
- 管理员专属的「RAG 知识库」模块支持查看文档、上传 TXT、Markdown、文本 PDF 和 DOCX、预览正文及下载原文件。上传资料立即用于本地检索；生成云端语义索引需要单独勾选同意。单文件最大 10 MiB。
- 管理中心还支持管理员搜索用户并查看其业务资料和记录。普通用户没有这些管理入口，后端也会校验管理员身份。

## 技术栈

- 前端：Vue 3、TypeScript、Vite、Pinia、Vue Router、ECharts
- 后端：Python、FastAPI、SQLAlchemy、Pydantic
- 数据库：PostgreSQL
- 智能体与检索：LangGraph、DashScope / 通义千问、BM25、Chroma、Tavily（可选）

## 本机配置

需要安装 Python 3.11+、Node.js（建议 20+）、npm 和 PostgreSQL。项目默认从根目录的 `.env` 读取数据库和模型配置。

1. 启动 PostgreSQL，并创建本项目使用的数据库和账号。
2. 在项目根目录复制模板并填写自己的连接信息：

   macOS / Linux：

   ```bash
   cp .env.example .env
   ```

   Windows PowerShell：

   ```powershell
   Copy-Item .env.example .env
   ```

3. 编辑 `.env` 中的 `DATABASE_URL`。按需填写 `DASHSCOPE_API_KEY`、`BOOHEE_API_KEY` 和 `TAVILY_API_KEY`。Tavily 用于 CRAG 联网补充，是可选项。模型和 Tavily 密钥仅放在后端环境变量中，不要提交到 Git。

## 安装与启动

在项目根目录执行：

```bash
# 激活你用于本项目的 Python 环境后安装后端依赖
python -m pip install -r backend/requirements.txt

# 安装前端依赖并构建
npm --prefix web install
npm --prefix web run build

# 启动后端
python -m uvicorn app.main:app --reload --app-dir backend
```

浏览器访问 <http://127.0.0.1:8000>。后端启动时会创建缺失的应用数据表，并兼容执行部分旧表结构升级；首次迁移前建议备份数据库。

开发前端时，另开终端在项目根目录运行：

```bash
npm --prefix web run dev
```

打开 Vite 输出的开发地址。Vite 会将 `/api` 请求代理到本机 FastAPI 服务。

## 管理员

普通注册账号默认是普通用户。管理员账号通过后端脚本在本机创建或授权，不要通过修改前端代码授予权限：

```bash
# 创建管理员，执行时会安全地提示设置密码
python backend/scripts/manage_admin.py create <用户名>

# 管理已有账号权限
python backend/scripts/manage_admin.py grant <用户名>
python backend/scripts/manage_admin.py revoke <用户名>
```

## 测试

在项目根目录执行：

```bash
python -m unittest discover -s backend/tests -v
npm --prefix web test
npm --prefix web run build
```

测试中的后端 API 使用独立测试数据库；涉及云端服务的测试使用模拟对象。

## 隐私与使用边界

这是本机演示项目，不是医疗产品，也不适合直接公开部署。账号业务数据保存在 PostgreSQL；密码使用 PBKDF2 散列，会话使用签名 Cookie。健康资料当前没有应用层加密。管理员可以查看用户业务资料；上传的知识文档是共享资料，可能用于所有用户的教练答复。

AI 请求受页面授权和功能设置约束。授权后，相关问题和检索资料可能发送至已配置的模型服务；CRAG 的 Tavily 查询只使用本轮问题文本，不包含教练工具读取到的个人业务记录。不要向云端服务发送真实敏感信息，也不要把训练或营养建议当作医疗诊断或个体化处方。

项目设计、测试手册及开发记录维护在工作区的「项目文档」目录中。
