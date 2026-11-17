# 收支概览布局验证

日期：2026-11-17。执行者：主 Agent，本轮未派发独立 QA 子 Agent。参考用户提供的侧栏 / 细边框 / 图表分区截图，在现有本地 Vue 项目中调整界面。沿用真实 FastAPI 和 MySQL，不拦截或模拟接口。

## 实测结果

- `cd frontend && npm test`：29 passed，0 failed；包含 3 项新的走势图测试，验证排序、同日聚合、正负数、精度、空数据与单日期。
- `cd frontend && npm run build`：通过，674 modules；原有依赖和锁文件未改变。
- `tests/browser_p1_acceptance.mjs`：全部 7 组场景通过，0 uncaught page errors。实际浏览器新增、编辑回填与取消、保存、删除取消与确认、组合筛选、快速切换、空状态、清空、刷新持久化均完成；MySQL 查询核对成功。完整结果见 [本次 P1 运行结果](browser-p1-result.json)，运行标记 `qa-p1-1a6a9743`。
- 测试新增 ID 为 148～151；151 经页面删除，其余 148～150 按 ID / 分类 / 备注匹配清理。执行前的记录 27、28、145、146、147 通过 SQL 核对未改变。
- 只读布局检查覆盖 1440、1280、1024、960、768、680、390、320px：文档宽度等于视口，三项统计金额单行；折线图和环图的实际 SVG 宽度匹配容器，未被图标样式压缩。已查看桌面和 390px 截图。
- 额外只读检查核对全部 / 仅收入 / 仅支出 / 空分类筛选下，实际 ECharts 折线日期与累计金额均匹配真实 API 记录，最后一点匹配 summary.balance；清空后图表恢复。四个侧栏入口在桌面 / 390 / 320px 可用，记账入口聚焦金额。该检查未发 POST / PUT / DELETE。结果见 [只读交互结果](redesign-interactions-result.json)。

浏览器复跑使用已有项目内 Playwright、现有 Chromium 及项目内动态库；未安装全局依赖或创建 / 停止共享 MySQL。复用用户启动的 5173 / 8000 服务。

## 真实浏览器复跑命令

项目根目录执行，前后端及 MySQL 应已运行：

```bash
FINANCE_QA_BROWSER_EXECUTABLE=/home/ava/.cache/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-linux64/chrome-headless-shell \
FINANCE_QA_BROWSER_LIBRARY_PATH="$PWD/.tools/browser-runtime/root/usr/lib/x86_64-linux-gnu" \
TMPDIR="$PWD/.tools/browser-runtime/tmp" \
node tests/browser_p1_acceptance.mjs
```

附加只读检查的本地脚本位于忽略的 `.tools/dev/redesign-review.mjs` 与 `.tools/dev/redesign-interactions.mjs`，实际命令为 `TMPDIR="$PWD/.tools/browser-runtime/tmp" node .tools/dev/<脚本名>`；它们不是应用依赖或跨环境恢复入口。

## 截图与限制

- [1440px 桌面](../../screenshots/redesign-1440.png)
- [390px 手机](../../screenshots/redesign-390.png)
- [320px 手机](../../screenshots/redesign-320.png)

截图来自测试清理后的真实账目，保留用户原有 5 条记录。走势以 0 为起点，展示当前筛选范围内按日期累计的收支差额，不提供银行连接或账户初始余额。本轮未重新运行完整的后端 193 项联合测试，也未重启用户的后端进程；页面编辑后的刷新持久化已实际复测。
