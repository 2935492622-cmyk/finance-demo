# frontend-developer 交付报告

日期：2026-11-16。对应任务：FE-01、FE-02、FE-03、FE-04。状态：P0 / P1 已由 QA 独立验收并经主 Agent 复核通过；移动端缺陷 QA-P0-002 已复测关闭。前端 26 项单测与构建由主 Agent 独立复跑通过。最终实测证据见 [QA P1 测试报告](../docs/qa/P1_TEST_REPORT.md)和 [P0 测试报告](../docs/qa/TEST_REPORT.md)。

## 完成内容

- 本地 Vue 3 + Vite 工程及 Axios 调用，保留 package.json / package-lock.json。
- 中文单页账本：侧栏、标题、日期、三项统计、收入 / 支出表单、全部收支明细。
- 分类自由输入与推荐值、记账日期、可选备注、服务端字段错误回显。
- 首次读取、空记录、加载、读取失败、提交中、成功及保存结果未确认状态。
- 保存成功后重新请求列表和统计；读取失败时保留上次完整快照并明确标记。
- 金额只用十进制字符串处理，默认日期基于 Asia/Shanghai。
- 本地 Playwright 驱动已按主 Agent 要求安装，未下载浏览器，供 QA 使用现有浏览器。
- P1：编辑回填 / 取消 / 保存、删除确认 / 取消、四项组合筛选及清空。
- P1：ECharts 支出分类图、原始金额语义列表、无支出状态、尺寸监听与销毁。

## 新增文件

```text
frontend/
├── .gitignore
├── index.html
├── package.json
├── package-lock.json
├── vite.config.js
├── DELIVERY.md
├── src/
│   ├── main.js
│   ├── App.vue
│   ├── api/
│   │   ├── client.js
│   │   └── transactions.js
│   ├── components/
│   │   ├── AppIcon.vue
│   │   ├── SummaryCards.vue
│   │   ├── TransactionForm.vue
│   │   ├── TransactionList.vue
│   │   ├── FilterBar.vue
│   │   ├── DeleteDialog.vue
│   │   └── ExpenseChart.vue
│   ├── composables/ledger.js
│   ├── styles/main.css
│   └── utils/
│       ├── money.js
│       ├── date.js
│       ├── validation.js
│       ├── filters.js
│       └── chart.js
└── tests/
    ├── money.test.js
    ├── ledger.test.js
    └── p1.test.js
```

保留既有 `.gitkeep`，未修改后端、数据库、根文档、契约或 Git 状态。`dist/`、`node_modules/` 为本地生成内容，已忽略，不交付为源代码。

## 实现方案与学习要点

`App.vue` 负责装配页面和响应提交；表单、明细和统计各自保持职责边界。使用 Composition API，无需为单页引入路由或全局状态库。

`ledger.js` 管理读取和保存流程。列表与 summary 使用 Promise.all 一起读取，只在两者均成功时整体替换快照；任一失败均保留上次完整数据。递增请求版本和 AbortController 配合，避免旧请求晚返回覆盖新数据。该协调逻辑有独立单测，不依赖浏览器或数据库。

`money.js` 用正则、字符串拆分和补零完成 `12` → `12.00`、`12.3` → `12.30`。不通过浮点数舍入，超出两位小数直接报错；服务器大额统计的展示也保留原始十进制精度。

保存过程中设置提交锁，阻止双击重复发送 POST。201 才确认保存并清空表单；已保存但重新读取失败时，提示“已保存，刷新失败”，避免重复记账。网络失败或 HTTP 500 / 503 均保守视为结果未确认：保留输入、锁定后续提交、要求先刷新核对。原因是服务端可能已经提交，但确认响应在链路中丢失，不能把网络异常直接等同于未写入。刷新成功也不会宣称上一笔一定保存，而是要求用户核对明细。

Vue、Vite、Axios 的使用分别参考 [Vue 官方快速入门](https://vuejs.org/guide/quick-start.html)、[Vite 官方指南](https://vite.dev/guide/)和 [Axios 取消请求文档](https://axios-http.com/docs/cancellation)。前端遵循 [Sites local-only 技能](/home/ava/.codex/plugins/cache/openai-curated-remote/sites/1.1.6/skills/sites/SKILL.md)，使用已有目录并跳过注册、托管和发布。

## 环境与启动

实测环境：Node.js v24.22.2、npm 11.19.1。已安装 Vue 3.5.45、Axios 1.21.1、Vite 8.3.8、@vitejs/plugin-vue 6.0.11、Playwright 1.65.1、ECharts 6.1.0，实际版本见锁文件。

在 `frontend/` 中恢复及启动：

```bash
npm ci --cache .npm-cache
npm run dev
```

前端固定 `http://127.0.0.1:5173`，端口占用时直接报告；`/api` 代理到 `http://127.0.0.1:8000`。实际 FastAPI 服务和 MySQL 就绪后才能完成收支功能的真实联调。前端不接触数据库账号或密码。

本次由 Sites 本地安装 helper 安装初始依赖，随后按主 Agent 指示本地添加 Playwright。所有依赖位于 frontend/node_modules；初始 npm 缓存也在 node_modules 内，后续缓存位于 frontend/.npm-cache。没有全局安装或创建后代 Agent。

## 测试命令与实际结果

```bash
cd frontend
npm test
npm run build
npm ls --depth=0
```

- `npm test`：26 / 26 通过，0 失败、0 跳过。覆盖金额与日期边界、Unicode 长度、超安全整数金额展示、完整快照、旧响应防护、重复提交、保存与刷新失败区分、结果未确认锁定及 500 / 503 保护；P1 增加筛选、取消、全量 PUT 字段、DELETE 空体与图表精度测试。
- `npm run build`：通过，Vite 8.3.8，672 模块。生成 index.html、约 20.6kB CSS、约 156.1kB 主 JS 及约 434.9kB 异步图表 JS；图表按需导入并分块。
- 依赖安装时 npm audit：0 vulnerabilities。
- `npm ls --depth=0`：直接依赖完整，无缺失报告。

上述状态测试使用受控异步结果检查前端逻辑，属于单元测试，不是 MySQL 或端到端验收证据。

## 验收归属与限制

- P1 已按正式派发完成；QA 已独立通过真实写入、编辑、删除、组合筛选、图表和 SQL 核对，浏览器 7 组场景完整复跑通过，独立测试为 87 passed、0 skipped。该结论来自 QA 执行及主 Agent 复核，不是开发者只读自查结论。
- 首次交付时尚未执行浏览器测试、API 实际写入、SQL 核对、刷新持久化或截图；这些后来由主 Agent / QA 推进。本 Agent 只完成下面列出的只读布局检查，没有发 POST、修改账目或另开 5173。
- P0 最终验收状态以 QA 的独立报告及主 Agent 复核为准，本模块报告不代替真实数据库证据。
- 生产构建仅验证前端资源可生成，不代表无需后端即可记录数据。

## QA-P0-002：移动端金额与备注可读性修复

已实际查看 QA 提供的 `screenshots/p0-mobile-success.png` 和 `screenshots/p0-mobile-after-restart.png`。390px 下三列统计卡可用宽度过窄，加上金额的 `overflow-wrap:anywhere`，使 `1,000.00` 最后一位单独换行。记录表没有最小宽度，自动布局继续压缩文本列，导致长备注接近逐字竖排。

仅修改 `src/styles/main.css`：

- 680px 以下统计卡改为全宽单列，金额增大到 24～26px，并固定不换行。极端长金额在金额区域内滚动，完整十进制文本保留，不截断精度。
- 表格最小宽度为 620px，分类 / 备注列至少 220px、文本区域至少 140px。横向滚动限定于 `.table-scroll`，页面本身不横向溢出。
- 保留桌面三列统计布局，不新增功能、依赖或业务逻辑。

实际复测：`npm test` 仍为 15 / 15 通过；`npm run build` 成功，79 模块，约 236ms。随后使用项目内 Playwright、已有浏览器与项目内运行库，对主 Agent 已启动的真实页面进行只读检查，无请求拦截、无新增记录、0 次 POST：

| 视口 | 文档宽度 | 金额高度 / 单行行高 | 表格宽度 / 滚动容器宽度 | 备注宽度 |
| --- | --- | --- | --- | --- |
| 390px | 390px | 34px / 33.8px | 620px / 348px | 约 142～147px |
| 320px | 320px | 31px / 31.2px | 620px / 292px | 约 142～147px |
| 1440px | 1440px | 45px / 44.9px | 约 700px / 700px | 约 142～147px |

三种视口的金额均为单行，文档未横向溢出。开发者已实际查看修复后本地临时截图；正式截图和缺陷关闭由 QA 独立复测后记录。

## FE-03 / FE-04：P1 实现与交付

主 Agent 确认 P0 真实 MySQL 与页面持久化通过、QA-P0-002 关闭后，正式派发本轮 P1。本轮没有改动演示记录 27 / 28。

### 核心逻辑

- `FilterBar.vue` 收集类型、精确分类、起止日期；前端先验证范围和空字段，再由同一份条件驱动列表与 summary。快照连同筛选条件整体提交，图表读取相同 summary，不另算账目。
- `TransactionForm.vue` 根据编辑记录回填五个字段。类型改变时清空分类仅发生在用户明确点击类型按钮时，程序回填收入记录不会意外抹掉分类。取消只清理本地编辑状态，不发请求。
- `transactions.js` 增加契约规定的 PUT / DELETE；写入字段始终白名单化为 amount、type、category、note、transaction_date，不把 ID 或系统时间发回。DELETE 204 直接确认成功，不解析 JSON。
- `ledger.js` 将重复提交锁、完整快照及结果不确定保护扩展到修改和删除。删除通过原生 dialog 确认，取消不发 DELETE；删除后重新读取。保存后是否被筛选隐藏，以成功刷新的数据库列表中是否含返回 ID 判定，不复制数据库分类排序语义。保存成功但读取失败仍有单独提示。
- `ExpenseChart.vue` 只注册饼图、Tooltip 和 SVGRenderer；组件异步加载。ResizeObserver 处理宽度变化，销毁时断开监听并 dispose。金额仅在图形几何值中转换 Number；图例、合计和 Tooltip 使用原始十进制文本。Tooltip 采用 richText，分类在 Vue 图例中按文本输出，不使用 v-html。

实现参考 [ECharts 官方按需导入](https://echarts.apache.org/handbook/en/basics/import/)与[容器尺寸 / 资源释放文档](https://echarts.apache.org/handbook/en/concepts/chart-size/)。

### 本轮实际验证

- `npm test`：26 / 26；包含编辑和删除取消零请求、PUT 五字段、筛选一致性、依据服务端列表判断隐藏、PUT / DELETE 未确认锁及 204 空体处理。
- `npm run build`：成功，672 模块。ECharts 安装仍为本地依赖，npm audit 为 0 vulnerabilities。
- 对主 Agent 现有服务做只读浏览器检查：收入 27 编辑回填金额及“工资”分类后取消；支出 28 打开删除框后取消；四条件收入筛选及清空；仅收入时“暂无支出”；恢复后真实环图和金额列表可见。全程 0 POST / PUT / DELETE。
- 1440 / 390 / 320px 文档宽度分别等于视口宽度，三项金额单行；图表 SVG 和路径有实际可见尺寸。已实际查看桌面和移动端截图。

检查截图时发现原有全局 `svg { width:20px; height:20px }` 图标规则缩小了图表 SVG，导致容器和 DOM 存在但环图不可见。已用 `.expense-chart svg` 的局部尺寸规则修复，并补充真实 SVG / path 几何断言验证，避免只以 DOM 存在宣称图表正常。

### QA 选择器

| 功能 | 入口 |
| --- | --- |
| 筛选 | `#filter-type`、`#filter-category`、`#filter-start`、`#filter-end`；应用筛选 / 清空筛选 |
| 编辑 | 按钮可访问名称 `编辑第 {id} 笔记录`；表单沿用 `#amount` / `#category` / `#transaction-date` / `#note` |
| 编辑保存 / 取消 | 保存修改 / 取消编辑 |
| 删除 | 按钮可访问名称 `删除第 {id} 笔记录`；原生 dialog 标题“删除这笔记录？”；取消 / 确认删除 |
| 图表 | `.expense-chart`，role=img；`.chart-legend` 的 aria-label 为“支出分类金额”；`.chart-total` 为合计 |

页面现在有两个 form，记账表单应使用 `.entry-panel form` 定位，不能继续使用未限定的 `form`。本节的开发者检查均为只读；之后的正式写入验收、清理和最终截图由 QA 独立执行，见上方报告链接。最终截图包括 [桌面页面](../screenshots/p1-final-desktop.png)和 [390px 页面](../screenshots/p1-final-mobile390.png)，主 Agent 已实际查看；临时测试数据清理后仅保留演示记录 27 / 28。
