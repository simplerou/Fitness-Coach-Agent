# API 契约占位

规划接口（以项目规划书第 10.3 节为基线）：

- `GET /api/today`
- `POST /api/plan`
- `POST /api/log`
- `POST /api/safety-check`
- `POST /api/safety-resolution`
- `POST /api/daily-signal`
- `POST /api/coach-note`
- 用户建档、授权/撤回与健康数据删除接口（按第 9.7、11.3 节落实）

`reasons[]` 应为结构化原因；症状安全门禁不能依赖 LLM，自由文本只可作补充输入。
