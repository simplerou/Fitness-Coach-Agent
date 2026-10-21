# 青禾训练助理 · 网页端改版提示词（可直接粘贴给编码 Agent）

> 用法：整段复制「提示词正文」给 Claude Code / Cursor / WorkBuddy。
> 建议分阶段派发（见第 13 节），每阶段先让它出方案、你确认后再改代码。
> 附录 A 是真实接口清单，**提示词里已经声明"不许自己编接口"**，AI 若想加接口必须回来问你。

---

# 提示词正文（从这里开始复制）

## 0. 角色

你是一名做过数据型 SaaS Dashboard 的前端工程师，同时懂信息架构和视觉。现在要改造一个真实的 Vue 3 项目：**青禾训练助理 · 减脂塑形网页端**（`web/` 目录）。

你的任务不是"换个配色"，而是**把移动端式的单列长页面，重构为桌面优先的数据驾驶舱**。

## 1. 先读代码，再动手（强制）

改造前必须自己读这些文件，不要凭猜测写代码：

- `web/src/App.vue`、`web/src/router/index.ts`、`web/src/components/layout/TopBar.vue`、`TabBar.vue`
- `web/src/styles/tokens.css`、`main.css`、`home.css`
- `web/src/views/` 全部 7 个页面
- `web/src/api/types.ts`（数据契约的权威来源）
- `web/src/stores/`（Pinia，业务逻辑都在这里，**不要改业务逻辑**）

## 2. 现状与必须解决的问题

当前形态：`max-width:1180px` 居中容器 → 顶栏 → 横向胶囊标签导航（6 个）→ 每页顶部一大块 hero 标题区 → 面板单列纵向堆叠，页面很长。

必须解决的具体问题（逐条对照验收）：

| # | 现状 | 目标 |
|---|---|---|
| 1 | 正文字号 10–13px，密集小字 | 正文 14px、辅助 12px（不低于 11px）、数据 28–34px |
| 2 | 横向胶囊 tab 作主导航，内容靠 `display:none` 切换 | 固定左侧导航（240px）+ 路由驱动，位置感永不丢失 |
| 3 | 每页顶部大 hero 标题占掉 1/3 首屏 | 删除 hero，改为 64px 页头（标题 + 面包屑 + 操作区） |
| 4 | 单列瀑布流，一屏只有 2 张卡 | 12 栅格多栏，1440×900 首屏能看到 4 张数据卡 + 主图表 |
| 5 | 没有真正的图表库，趋势图是手搓 SVG | 引入 ECharts（按需引入），支持折线/柱/环形/日历热力图 |
| 6 | 数字孤立（"体重 62.1"） | 每个数字带上下文：目标、趋势箭头、时间窗、达成率 |
| 7 | 所有卡片同一个 `.panel` 样式 | 建立层级：数据卡 / 内容卡 / 侧栏卡三种，阴影与内距不同 |

## 3. 定位（决定了怎么排）

移动端负责"记"，**网页端负责"看和编排"**。所以：

- 概览 = 今天的状态 + 趋势，一屏看完，不滚动
- 训练/饮食 = **批量**与**编排**（表格录入、周历拖拽），键盘友好
- 报告 = 分析深度（区间对比、指标联动）
- 动作库 + AI = 查阅与问答（侧边常驻，不打断当前工作）

## 4. 技术与边界

**技术栈（不换）**：Vue 3 `<script setup>` + TypeScript + Vite + Pinia + vue-router（hash 模式，保持）。

**允许新增依赖**（仅这些）：
- `echarts` + `vue-echarts`（或直接用 echarts 的 `init` 封装，禁止全量 `import * as echarts`）
- `@vueuse/core`（可选，用于 `useElementSize` / `useMediaQuery` / 快捷键）
- `dayjs`（若已有日期工具则不加）

**禁止**：
- 禁止引入 Element Plus / Ant Design Vue / Naive UI 等成品 UI 库（会把默认样式带回来，又变成"老套"）
- 禁止引入 Tailwind（现有样式体系是原生 CSS + CSS 变量，保持它）
- 禁止改 `backend/` 任何文件
- 禁止修改 `web/src/api/*.ts` 的函数签名与 `types.ts` 的类型结构
- 禁止修改 stores 的业务判断逻辑（可以新增 getter/computed 派生态）
- 禁止新增后端接口、禁止在前端 mock 假数据当真实功能
- 禁止 `localStorage` 存健康类敏感数据（现有代码已有此约束，必须延续）

**改动范围**：`web/src/App.vue` 的模板结构、`web/src/views/*`、`web/src/components/*` 的模板与样式、新增 `web/src/components/layout/`（侧栏/页头）与 `web/src/components/charts/`、`web/src/styles/*`。

**后端限制（必须尊重，不要幻想接口）**：
- 周计划只有 `POST /api/plan` 整周生成 + `GET /api/plan/current|history`，**没有"改某一天"的接口**。因此周历的拖拽只作用于本地草稿，必须由用户点"按此安排重新生成"后再提交，并明确提示"会覆盖本周计划"。
- 训练记录有 `POST /api/log`（简版）与 `POST /api/training/logs`（含动作明细 + 恢复），批量录入需按日期循环提交，逐条显示成功/失败。

## 5. 设计系统（先落地到 `tokens.css`，再写任何页面）

浅色底 + 单一主色 + 大留白 + 圆角。**保留品牌青绿**（`#176344`）作主色，橙 `#E0894A` 只做强调与 AI 语义色。

```css
:root {
  /* 背景层 */
  --bg: #F6F7F5;            /* 页面底 */
  --surface: #FFFFFF;       /* 一级卡片 */
  --surface-2: #FAFBFA;     /* 卡内分区 */
  --border: #E8EBE7;        /* 常规分割线 */
  --border-strong: #D9DFDA;

  /* 文字 */
  --text-1: #14211B;        /* 标题 */
  --text-2: #55635B;        /* 正文 */
  --text-3: #8A968F;        /* 辅助说明 */

  /* 品牌与语义 */
  --brand: #14664A;
  --brand-soft: #E7F1EA;    /* 浅底标签 */
  --brand-line: #C9DED2;
  --accent: #E0894A;        /* 强调 / AI */
  --accent-soft: #FBF1E7;
  --success: #3F8A5B;
  --warn: #C08A3E;
  --danger: #B44736;

  /* 圆角 / 阴影 / 间距（4px 基数） */
  --r-sm: 8px; --r-md: 12px; --r-lg: 16px; --r-xl: 20px;
  --shadow-1: 0 1px 2px rgba(20,33,27,.04);
  --shadow-2: 0 1px 2px rgba(20,33,27,.04), 0 8px 24px rgba(20,33,27,.06);
  --sp-1: 4px; --sp-2: 8px; --sp-3: 12px; --sp-4: 16px; --sp-5: 20px; --sp-6: 24px; --sp-8: 32px;

  /* 字号 */
  --fs-xs: 11px; --fs-sm: 12px; --fs-base: 14px; --fs-md: 16px;
  --fs-lg: 20px; --fs-xl: 24px; --fs-2xl: 30px; --fs-3xl: 36px;
}
```

规则：
- 字体：`Inter, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif`；**所有数字加 `font-variant-numeric: tabular-nums`**
- 数据卡的数字用 `--fs-2xl`/`--fs-3xl` + `font-weight 600`，单位用小一号的 `--text-3`
- 卡片：`background: var(--surface); border:1px solid var(--border); border-radius: var(--r-lg); box-shadow: var(--shadow-1)`；**只有可点击/浮起的卡才用 `--shadow-2`**
- 正文行高 1.6，标题行高 1.3
- 主色面积不超过页面 8%，只用于：主按钮、当前导航项、进度填充、关键折线

## 6. 布局骨架

```
┌──────────┬────────────────────────────────────────────────────┐
│ Sidebar  │ Topbar 64px（sticky）：页面标题·面包屑 | 日期范围 | 搜索 | 头像 │
│ 240px    ├──────────────────────────────────┬─────────────────┤
│ fixed    │ Content  padding 24~32px          │ Right rail      │
│          │ max-width 1400px, 12 栅格 gap 20  │ 340px（仅概览）  │
│ 品牌     │                                   │ AI 建议/今日上下文│
│ 导航组   │                                   │                 │
│ 二级导航 │                                   │                 │
│ 用户区   │                                   │                 │
└──────────┴──────────────────────────────────┴─────────────────┘
```

- Sidebar：`position: fixed; width: 240px; height: 100vh; overflow-y: auto`；内容区 `margin-left: 240px`
- 导航项：36px 高、`--r-sm` 圆角、左侧 3px 竖条表示选中（不要用整块填充色），图标 18px（用内联 SVG，**禁止 emoji**）
- Sidebar 底部固定：用户头像 + 名称 + 设置入口
- 内容区 `padding: 24px 32px 64px`，`max-width: 1400px`（超宽屏不被拉散）
- `≥1680px` 才启用右侧栏；`1280–1679px` 右侧栏内容降为概览页底部一行；建议在 1440 做基准调试

## 7. 信息架构（导航 5 项 + 设置）

| 导航 | 路由 | 从哪来 | 二级 |
|---|---|---|---|
| 概览 | `/today` | 现有 TodayView | — |
| 训练 | `/plan` | 现有 PlanView + LogView 合并 | 周计划 / 训练记录 |
| 饮食 | `/diet` | 现有 DietView | 今日日志 / 食物库 / 饮食计划 |
| 报告 | `/shaping` | 现有 ShapingView + ReviewView | 趋势 / 体测 / 周回顾 |
| 动作库 | `/library`（**新增路由**） | 复用已有 `ExerciseLibrary.vue` 组件 | — |
| 设置 | `/profile` | 现有 ProfileView | 从侧栏底部进入，不占主导航 |

路由调整只做"新增 `/library` + 5 个页面内部用 query/tab 切换二级"，**不要改动已有 path 名**（`/today`、`/plan`、`/log`、`/diet`、`/shaping`、`/review` 仍需可访问，可作为二级的 redirect 目标）。

## 8. 逐页规格

### 8.1 概览 `/today`（最优先，做完先给我看）

**第一行 · 4 张数据卡（等高，`grid-template-columns: repeat(4,1fr)`）**
1. 今日热量：环形进度（摄入/目标）+ 中心大数字 + 下方"蛋白质/碳水/脂肪"三条迷你条
2. 今日训练：`已完成 / 计划` + 状态标签（按 `TodayResponse.level` 上色：normal 绿 / downgrade 琥珀 / stop 红 / rest_day 灰）
3. 连续打卡：天数 + 小字"本周 X 天"，右侧 7 个点表示本周打卡位
4. 目标进度：`当前体重 → 目标体重`，剩余 kg，环形或横向进度条

**第二行 · 主图区（`2fr 1fr`）**
- 左：体重 / 围度趋势（ECharts 折线，2–3 条系列可切换；带目标基准虚线；时间范围切换 4周/8周/12周/全部；hover 十字准星 + tooltip 显示日期、数值、较上次变化）
- 右：训练日历热力图（近 3 个月，5 档色阶用 `--brand` 的透明度梯度；hover 显示当天完成度/RPE；点击跳到该日训练记录）

**第三行（`1fr 1fr`）**
- AI 建议卡：**必须结构化**——`结论标题` + `依据（数据引用）` + `预期影响` + `[采纳] [忽略]` 两个按钮。采纳/忽略调已有接口（`PUT /api/training/advice/{id}`、`PUT /api/shaping/intelligence/weak-parts/{id}`），禁止静默改计划
- 今日安排：`today_schedule` 的 session 卡（标题、时长、动作数）+ 安全筛查状态 + 快捷入口（记录训练 / 记录饮食 / 上传照片）

**右侧栏（≥1680px）**
- 今日上下文卡：今日饮食热量汇总、训练完成情况、"采纳为今日目标 →"
- AI 教练入口卡（点击打开右侧抽屉）
- 上周周报摘要卡（围度变化、完成 X/Y 天）

**硬性要求**：1440×900 视口下，不进滚动就能看到 4 张数据卡 + 主图表区。

### 8.2 训练 `/plan`

顶部：二级切换 `周计划 | 训练记录`，右侧 `本周 ◀ 10.14 - 10.20 ▶` 日期切换 + `生成/重新生成计划` 主按钮。

**周计划视图**
- 周历条带：7 列等宽，每列表头是「周一 10.14」，下面堆叠该日 session 卡（标题 / 时长 / 动作数 / 完成状态点）
- 休息日显示为浅色空态，不占满高度
- session 卡 hover 浮起（`--shadow-2`）+ 右侧出现"详情 / 替换"操作
- **拖拽换天**：只能移动本地草稿，顶部出现常驻提示条「已调整 2 天 · [按此重新生成] [撤销]」，点击生成时弹确认框说明会覆盖本周计划
- 左侧或底部：本周统计条（训练天数、总组数、完成率、平均 RPE）

**训练记录视图（表格化，键盘友好）**
- 表格列：日期 / 计划动作 / 完成度（彩色标签）/ RPE / 主要重量 / 备注 / 操作
- 行内编辑：点单元格变 input，`Enter` 提交、`Esc` 取消、`Tab` 下一个单元格
- 顶部"批量录入"：粘贴多行 / 快速填表，逐行显示提交结果（成功✓/失败✗ 带原因）
- 右侧抽屉：单次训练详情（动作明细、恢复问卷结果、进阶建议）
- 空态：说明"本周没有记录"+ 一键补记昨天

### 8.3 饮食 `/diet`

三栏（`1.1fr 1fr 0.9fr`）：

- **左：四段式日志**（早餐/午餐/晚餐/加餐），每段是独立卡：段头（名称 + 小计 kcal）+ 食物行（名称/份量/宏量 三项小字）+ `＋ 添加`。行 hover 出现"改/删"。段底部显示该餐热量占比细条
- **中：营养 Dashboard**
  - 环形：热量 摄入/目标（超目标时环形变 `--danger` 并加 1 次呼吸提示）
  - 宏量堆叠条：蛋白质/碳水/脂肪，每条显示"实际 / 目标 g"与百分比，超目标用琥珀
  - 饮水：水滴格（每 250ml 一格）+ 快捷 `+250 / +500`
  - 目标卡：显示计算依据（`diet/targets` 里的 `basis`），不要只给数字
- **右：当日 AI 调整建议**（`/api/shaping/intelligence/diet-adjustment`）：训练日/休息日差异说明 + 建议热量与三大宏量 + 理由 + `[采纳] [忽略]`

顶部操作：`食物库搜索`（打开命令面板）、`生成饮食计划`（抽屉展示 `POST /api/diet/plan` 结果，含周计划/餐次建议/替换建议）、`标记当日完成`。

### 8.4 报告 `/shaping`

二级切换 `趋势 | 体测 | 周回顾` + 右上 `周 / 月` 周期切换 + `生成报告` + `导出`（若有接口则接，没有就隐藏按钮，别做假按钮）。

- **趋势**：一张大图（体重、腰围、体脂率、骨骼肌，多系列，可勾选显隐）+ 下方 3 张指标卡（当前值 / 周期变化 / 达成率）。hover 联动：鼠标停在某天，所有卡同步高亮该天数值
- **体测**：围度网格（5 个部位小卡：当前值、较上次 Δ、测量日期、逾期提醒）+ 测量记录表格（可编辑/删除）+ 照片对比（前/侧/后三视图 + 时间轴滑动对比）
- **周回顾**：统计卡行（完成率、训练量、饮食记录天数、平均 RPE、体重变化）+ 7 天时间轴（每天一行：计划 / 实际 / 状态信号 / 饮食 / 体重，异常日高亮）+ 下周调整建议卡（保留现有 `applySuggestion` 的行为：带入计划设置而不是自动改）

### 8.5 动作库 `/library` + AI 教练

- 三栏：左侧筛选（肌群 6 类 / 器械 / 关键词），中间卡片网格（3 列，卡含名称、肌群标签、器械图标、动作示意图），右侧详情面板（固定 380px，`cues`、`common_errors` 错误-纠正两列、`regressions`/`progressions`、替代动作、示范图/视频）
- 筛选是即时联动，不做"提交查询"按钮；无结果时给"清除筛选"
- **AI 教练**：右侧滑出抽屉（宽 420px）+ 全局 `⌘/Ctrl + K` 唤起，对话样式；回答必须展示 `answer` + `safety_note`（若有，用琥珀卡突出）+ 引用来源（`knowledge_sources` 折叠区，显示标题/来源/时间/摘录）+ 相关动作卡（可点击跳详情）

### 8.6 设置 `/profile`

从侧栏底部头像区进入。分组：身体档案（年龄/性别/身高/体重/目标体重）/ 训练偏好 / 账号与头像 / 数据与隐私（保留现有"本机演示"的提示文案，不能删）。表单用"字段 + 说明 + 单位后缀"的两列布局，右侧显示"当前值"对照。

## 9. 组件契约

必须实现的通用组件（放 `web/src/components/ui/` 与 `web/src/components/charts/`），每页复用，不许每页重写：

1. `StatCard` — props: `label / value / unit / sub / trend / tone / chart?`（`trend` 为 `{delta, direction}`，必须渲染箭头 + 色彩）
2. `TrendChart` — 统一封装 ECharts 折线：`series[] / targetLine? / range / onRangeChange / height`，内置 tooltip、空态、resize 观察
3. `BarChart` — 训练量/宏量
4. `RingProgress` — 环形，`value/max/tone/label`
5. `HeatmapCalendar` — 日历热力图，`data: {date, level}[] / months`
6. `DataTable` — 列定义驱动、行内编辑、排序、批量选择、空态
7. `AdviceCard` — AI 建议统一卡（结论/依据/影响/采纳/忽略），**所有 AI 建议都走这个组件**
8. `PageHeader` — 标题 + 面包屑 + 右侧操作槽
9. `SectionCard` — 内容卡（标题 + 右侧操作 + body）
10. `Drawer` — 右侧抽屉（`Esc` 关闭、焦点陷阱、`aria-modal`）
11. `CommandPalette` — `⌘K` 搜索/跳转/动作

图表统一接 `ResizeObserver`，容器宽度变化必须自适应；图表配色只用 token 变量，禁止硬编码色值。

## 10. 交互要求

- 图表：hover 显示 tooltip、可切换时间范围、能点进明细
- 列表：hover 显示行内操作，不做"更多"二级菜单
- 表格：支持键盘全流程（Tab/Enter/Esc），焦点态可见（2px `--brand` outline）
- 全局 `⌘/Ctrl + K`：搜索动作、跳页、打开 AI
- 写操作后**局部刷新**，不要整页 reload、不要闪白
- 数字变化加 200ms 过渡；`prefers-reduced-motion` 时全部关闭
- 破坏性操作（删除测量、覆盖计划）必须二次确认，说明影响范围

## 11. 状态与降级

- 加载：骨架屏（与最终布局同尺寸），**禁止 spinner 占满全屏**
- 空态：图标 + 一句说明 + 一个主行动按钮（例："还没有测量记录 · 记录第一次"）
- 错误：卡内错误条 + "重试"，不弹全局 toast 覆盖内容
- 数据缺失：显示"未记录"而不是 0，更不能显示 "--"了事；缺失项用 `--text-3` 与虚线边框区分

## 12. 明确禁止（反模式）

- ❌ emoji 当图标（现有代码里的 `🍖` `🏋️` 之类一律换内联 SVG）
- ❌ 小于 11px 的文字（`--fs-xs` 是下限）
- ❌ 每页顶部放超大标题 + 副标题 + 长段说明
- ❌ 横向胶囊 tab 当主导航
- ❌ 卡片套卡片（最多两层：卡 → 卡内分区用 `--surface-2` 背景块，不再加边框）
- ❌ 紫色渐变、玻璃拟态、发光边框、"AI 光晕"
- ❌ 孤立数字（没有目标/趋势/时间窗的数字）
- ❌ 固定宽度的图表容器（必须流体）
- ❌ 只做一个"演示用"假数据页面

## 13. 交付顺序（每阶段结束都要 `npm run build` 通过并自检）

| 阶段 | 内容 | 完成标准 |
|---|---|---|
| P0 | `tokens.css` 重写 + 布局骨架（Sidebar / Topbar / App.vue / 路由 5 项 + `/library` 占位） | 所有旧页面在新骨架里能正常显示，不报错 |
| P1 | 通用组件（StatCard / RingProgress / TrendChart / SectionCard / Drawer）+ 概览页 | 1440×900 首屏信息完整、有真实数据、无横向滚动 |
| P2 | 训练页（周历 + 表格） | 拖拽只改草稿、表格键盘可录入 |
| P3 | 饮食页（四段日志 + 营养 Dashboard） | 加餐/改餐/饮水全链路可用 |
| P4 | 报告页（趋势/体测/周回顾） | 图表联动、周期切换正确 |
| P5 | 动作库 + AI 抽屉 | 筛选即时、引用来源可见 |
| P6 | 响应式与打磨 | 1280/1440/1680/1920 四档无破版；`prefers-reduced-motion` 生效 |

**每阶段先给我「改动文件清单 + 关键决策（栅格/图表方案/组件 API）」，我确认后再改代码。**

## 14. 验收清单（逐条自查，不要口头保证）

- [ ] `npm run build`（含 `vue-tsc --noEmit`）零错误
- [ ] `npm run dev` 后 7 个路由都能打开；`/library` 能打开
- [ ] 概览首屏：4 张数据卡 + 主图，1440×900 不滚动
- [ ] 全站最小字号 ≥ 11px，正文 ≥ 14px
- [ ] 所有数字带 `tabular-nums`，且有目标/趋势上下文
- [ ] 图表窗口 resize 自适应，切换路由不残留旧实例（`onBeforeUnmount` 里 `dispose`）
- [ ] 空态/加载/错误三态在每个数据区块都存在
- [ ] 键盘可达：Tab 顺序合理，焦点框可见，抽屉 `Esc` 可关
- [ ] 无新增后端依赖、无改 `backend/`、无改 `api/*.ts` 签名
- [ ] 移动端 / 窄屏（<1024）降级为：侧栏收起为图标条或顶部抽屉，多栏变单列，表格变卡片列表

## 15. 响应式降级

| 断点 | 布局 |
|---|---|
| ≥1680 | 侧栏 240 + 内容 + 右栏 340 |
| 1440–1679 | 侧栏 240 + 内容（12 栅格） |
| 1024–1439 | 侧栏 200 收窄，导航仅图标+tooltip |
| 768–1023 | 侧栏折叠为顶部抽屉，多栏 → 2 栏 → 1 栏 |
| <768 | 底部 tab（复用现有 TabBar 形态），表格改卡片列表 |

---

# 附录 A · 真实接口（禁止编造，只能从这里选）

**认证**：`POST /api/auth/register`｜`POST /api/auth/login`｜`GET /api/auth/me`｜`POST /api/auth/logout`

**今日与状态**：`GET /api/today`｜`POST /api/safety-check`｜`POST /api/daily-signal`

**档案与体重**：`GET /api/body-profile`｜`PUT /api/body-profile`｜`POST /api/body-weight`｜`PUT /api/body-profile/target-weight`｜`DELETE /api/body-profile`

**周计划**：`GET /api/plan/preferences`｜`POST /api/plan`（整周生成，唯一写入口）｜`GET /api/plan/current`｜`GET /api/plan/history`｜`GET /api/plan/session?date=`

**训练记录与智能**：`POST /api/log`｜`GET /api/logs`｜`GET /api/review/week?date=`｜`GET /api/training/exercises`｜`GET /api/training/exercises/{id}`｜`POST /api/training/logs`｜`GET /api/training/logs`｜`PUT /api/training/advice/{id}`｜`DELETE /api/training/advice/{id}/decision`｜`GET /api/training/recovery/summary`｜`POST /api/training/adjustments/preview`｜`PUT /api/training/adjustments/{id}`

**饮食**：`GET /api/diet?date=`｜`POST /api/diet/meal`｜`PUT /api/diet/meal/{id}`｜`DELETE /api/diet/meal/{id}`｜`POST /api/diet/water`｜`GET /api/diet/targets`｜`GET|PUT /api/diet/profile`｜`PUT /api/diet/day-review`｜`GET /api/diet/foods/search`｜`GET /api/diet/foods/detail`｜`POST /api/diet/plan`｜`GET /api/diet/plan/history`

**塑型**：`GET /api/shaping`（聚合：measurements / weight_history / reminders / targets / photos）｜`PUT|DELETE /api/shaping/measurement[/{date}]`｜`PUT|DELETE /api/shaping/target[/{metric}]`｜`PUT /api/shaping/photo`｜`GET /api/shaping/photo/{id}/image`｜`DELETE /api/shaping/photo/{id}`

**塑形智能**：`GET|PUT /api/shaping/intelligence/preferences`｜`POST /api/shaping/intelligence/weak-parts/analyze`｜`PUT /api/shaping/intelligence/weak-parts/{id}`｜`DELETE /api/shaping/intelligence/weak-parts/{id}/decision`｜`POST /api/shaping/intelligence/qa`｜`GET /api/shaping/intelligence/diet-adjustment`｜`PUT /api/shaping/intelligence/diet-adjustment/{date}`｜`GET /api/shaping/intelligence/reports/auto`｜`GET /api/shaping/intelligence/reports`

**数据形状**：以 `web/src/api/types.ts` 为准（`ShapeDashboard`、`WeeklyReviewResponse`、`DietTargetsResponse`、`ReviewSummary`、`TodayResponse`、`WeekPlan`、`PlanSessionItem`、`CoachAnswerResponse` 等）。

---

# 附录 B · 现有可复用资产（别重写）

- `ExerciseLibrary.vue` / `ExerciseDetailDialog.vue` → 动作库页主体
- `CoachQaPanel.vue` → AI 教练抽屉内容
- `MeasurementDialog.vue` / `CircumferencePanel.vue` / `CompositionPanel.vue` / `PhotoCompare.vue` → 报告页体测
- `ShapeReportsPanel.vue` / `WeakPartPanel.vue` → 报告页周/月报
- `ProgressionAdviceCard.vue` / `PlanAdjustmentPreview.vue` → 建议卡样式基础（但需按 `AdviceCard` 契约统一）
- `DietMealDialog.vue` / `DietPlanner.vue` / `DietPlanResult.vue` → 饮食页
- `ProgressTrendChart.vue` → 仅作逻辑参考，**替换为 ECharts 版本**
- stores 里已有的加载/错误/缓存状态，全部复用，不要在组件里另起 fetch

---

# 附录 C · 视觉参考

参考 Keep 网页版 / MyFitnessPal Dashboard 的结构感，但**不要抄它们的配色和 2019 年的表格审美**。目标是：
- 信息密度像专业工具（Linear、Vercel Dashboard 那种克制感）
- 数据表达像报告（数字大、单位小、趋势明确）
- 主色只用一处（当前导航 + 关键折线 + 主按钮），其余靠灰阶层级拉开

---

# 提示词正文结束

---

## 使用备注（给你自己看，不要粘给 AI）

1. **P0 + P1 就足够看出效果**，先只派这两阶段，看完再决定后面要不要按这个规格做。
2. 如果 AI 开始"顺手优化后端"或"新增接口"，立刻叫停——第 4 节写了禁令，它违反了。
3. 拖拽排期是个坑：后端只支持整周重新生成，所以它只能是"草稿 → 确认 → 重新生成"，不要期待像 Notion 那样实时生效。
4. 图表库建议：`npm i echarts` 后按需注册（`LineChart/BarChart/PieChart/CalendarChart` + `GridComponent/TooltipComponent/DataZoomComponent`），体积可控在 150KB 内。
5. 若某阶段 AI 交出来的东西"还是很像原来"，把第 2 节的表格和第 12 节的反模式清单单独再甩它一次——这两节是最有效的纠偏。
