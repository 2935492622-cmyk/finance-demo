# 个人记账Demo独立QA执行报告

日期：2026-11-16（Asia/Shanghai）。当前结论：**P0/P1独立验收通过，无未关闭业务缺陷。87项独立测试全部通过，真实页面新增、编辑、删除、筛选、ECharts及SQL交叉验证完成；刷新及P0后端重启持久化通过。最终由主Agent联合回归复核。**

## 最新P1结果与最终截图

完整记录见 [P1_TEST_REPORT.md](P1_TEST_REPORT.md)。实际联合命令 `FINANCE_QA_INTEGRATION=1 .venv/bin/python -m pytest tests -q -rs`：**87 passed in 4.80s，0 skipped**（24离线/故障路径+39项P0真实API+24项P1真实API）。

真实P1页面7组检查通过，含编辑取消/保存、删除取消/确认、组合/空/快速筛选、ECharts真实实例和SVG绘图尺寸、390/320px resize及SQL对照。QA工具动态基线修正后完整复跑通过，临时测试记录已按自己ID与最新字段清理，原演示27/28未变。原始证据：[browser-p1-result.json](browser-p1-result.json)。

最终交付截图：[桌面](../../screenshots/p1-final-desktop.png)、[390px移动端](../../screenshots/p1-final-mobile390.png)、[320px移动端](../../screenshots/p1-final-mobile320.png)。这些是清理测试数据后的真实账本，收入1000.00、支出125.50、结余874.50、2笔。浏览器真实新增和P0后端重启的证据继续保留在下文。

以下P0与最初无数据库阶段记录按当时实际结果保留，历史“未执行”或“受阻”不作为当前状态。

## MySQL就绪后的实际结果

- 真实MySQL版本8.4.13，数据库finance_demo，应用通过本地.env读取专用账号，不输出密码。
- 执行 `FINANCE_QA_INTEGRATION=1 .venv/bin/python -m pytest tests/test_mysql_api.py -q -rs`：首轮因QA夹具tuple/list问题27 failed、12 passed；仅修正夹具后 **39 passed in 2.07s**。此前39 skipped是环境未就绪阶段的真实历史，不再作为当前结果。
- 联合执行 `FINANCE_QA_INTEGRATION=1 .venv/bin/python -m pytest tests -q -rs`：**63 passed in 2.94s，0 skipped**（24项独立离线/失败路径与39项真实MySQL）。用例只清理自己ID，演示27/28仍保留。
- 浏览器通过真实表单新增收入1000.00/工资和支出125.50/餐饮，日期2026-11-15；两次实际页面点击产生两次201，没有用HTTP新增代替页面，也没有拦截伪造。
- 两笔ID27/28，唯一备注前缀 `qa-demo-a91b49f0-4bc`。初始基线为0；当前总收入1000.00、总支出125.50、结余874.50、2笔。SQL按明确ID核对所有字段和Decimal金额，与API及页面一致。
- 刷新浏览器后仍一致；主Agent仅重启本项目8000后端（旧PID260521、新PID282329），QA只读复查页面/API/SQL，再次通过，没有重复新增或操作共享MySQL。
- 脱敏原始证据：[browser-p0-success-result.json](browser-p0-success-result.json)。初版成功截图：[桌面](../../screenshots/p0-desktop-success.png)、[390px缺陷证据](../../screenshots/p0-mobile-success.png)；**最终修复并重启后截图：[桌面](../../screenshots/p0-desktop-after-restart.png)、[390px](../../screenshots/p0-mobile-after-restart.png)**。初版移动截图保留缺陷发现过程，最终交付使用修复后截图。
- 两笔演示数据按主Agent指示暂保留供用户查看；其他自动化用例只清理自己的明确ID。不清空用户数据。

完整成功路径命令与历史失败路径使用相同浏览器环境变量，入口为 `node tests/browser_p0_success.mjs`；新增完成后再次运行必须使用 `--verify-after-restart`，避免重复记账。

## 移动缺陷修复与P0放行

QA实际查看成功截图发现390px金额断行和备注碎行，提交QA-P0-002 → 主Agent分派原前端Agent → 前端限定CSS修复 → QA增加真实文本行数回归并只读复测 → 关闭。

最终复测命令为 `node tests/browser_p0_success.mjs --verify-after-restart`（带下方相同浏览器环境变量），2026-11-16 11:18:44（Asia/Shanghai）通过。三个统计金额行数为 `[1,1,1]`，两条演示备注各约1行，表格宽620px、视口390px，滚动限定于表格容器，文档无横向溢出。已实际查看最终移动截图，金额完整、列表可读。

本次复测没有POST或数据修改。页面、API、SQL Decimal及两个已知ID再次一致，后端重启验证标记为true。P0所需页面收入/支出、全部列表、精确三项统计、MySQL实存和刷新持久化都有真实证据，当前无未关闭的P0业务缺陷。P1编辑、删除、筛选UI与图表由主Agent另行安排，QA没有自行进入。

## 初始无数据库阶段的历史执行记录

以下保留数据库未部署时的实际过程；初始环境阻碍现已解除，最新结果以上节为准。

## 实际执行结果

| 项目 | 实际命令 | 实测结果 | 能证明什么 |
| --- | --- | --- | --- |
| 独立校验 / 真实连接拒绝 | `.venv/bin/python -m pytest tests/test_contract_without_db.py -q -rs` | 24 passed，首次 1.17s | 实际 FastAPI ASGI 校验和真实本机 TCP 拒绝连接后的 503，非成功数据库测试 |
| 独立套件默认执行 | `.venv/bin/python -m pytest tests -q -rs` | 24 passed、39 skipped，0.79s | 非 DB 检查通过；真实集成未启用，不能把 skipped 算通过 |
| 明确尝试真实 MySQL 验收 | `FINANCE_QA_INTEGRATION=1 .venv/bin/python -m pytest tests/test_mysql_api.py -q -rs` | 39 skipped，0.02s；原因 backend/.env 不存在 | 确认真实集成受阻；没有实际成功连接或写入 |
| 前端错误函数独立检查 | `node tests/client_error_unit.mjs` | PASS，退出0 | 实际函数把 POST 500 / 503 / 网络失败标记结果未确认，保留422字段错误，GET错误不误当写入 |
| 真实浏览器失败路径 | 见下方完整命令 | 6组检查通过，退出0 | 页面、代理和真实后端503行为；不含伪造201或MySQL写入 |

独立 ASGI 校验覆盖金额零 / 负数 / 数字 / bool / 超小数位 / 前导零、非法类型、Unicode分类长度和空白、备注 null / 超长、非法日期及年份、只读字段、共享查询验证、日期颠倒位置、未知参数、破损 JSON、安全 503。故障测试使用已绑定但未监听的本机端口，不停止或改动任何共享服务。

本报告不将开发者模块报告中的 66 项后端单测和 15 项前端单测重复计为 QA 独立执行；主 Agent 可在最终报告中分别汇总自己的复跑结果。

## 真实浏览器证据

浏览器：现有 Chrome headless shell；驱动：`frontend/node_modules/playwright`；运行库：主 Agent 在项目内准备的 `.tools/browser-runtime`。前端5173和后端8000均由主 Agent 管理，QA 未另启同端口服务。

```bash
FINANCE_QA_BROWSER_EXECUTABLE=/home/ava/.cache/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-linux64/chrome-headless-shell \
FINANCE_QA_BROWSER_LIBRARY_PATH="$PWD/.tools/browser-runtime/root/usr/lib/x86_64-linux-gnu" \
TMPDIR="$PWD/.tools/browser-runtime/tmp" \
node tests/browser_p0_smoke.mjs
```

最终成功运行时间：2026-11-16 10:19:34～10:19:35（Asia/Shanghai）。原始结果：[browser-p0-result.json](browser-p0-result.json)。本次没有拦截 HTTP 请求或伪造数据库响应。

1. 前端200，真实 health503，页面清楚提示数据库不可用；统计显示未知值，没有伪造0余额或成功空账本。
2. 输入 `12.345` 后本地可见错误，无 POST。
3. 输入 `12.3` 发送 `12.30`；同一事件轮两次提交仅1个真实 POST，响应503。
4. 503后保留金额、分类和备注；显示保存结果未确认，锁定表单；刷新仍503时保持锁定，不重发 POST。
5. 390px窄屏没有文档横向溢出，表单和提示仍可见。
6. 没有未捕获页面 JavaScript 异常。

已生成并实际查看截图，中文可读、桌面分栏和窄屏堆叠正常：

- [桌面数据库不可用截图](../../screenshots/p0-desktop-database-unavailable.png)
- [移动端数据库不可用截图](../../screenshots/p0-mobile-database-unavailable.png)

截图展示的是实际失败状态，**不是成功记账、MySQL 记录或刷新持久化验收截图**。首轮浏览器运行因 QA 对 fieldset 的 Playwright 判断方式不适用而失败，修正为实际 input 禁用与原生 disabled 属性后完整复跑通过，详情见缺陷记录。

## 代码审查与缺陷复测

已独立阅读 schemas、models、database、crud、routers、exceptions，以及前端表单、金额 / 日期工具、Axios 错误、快照与提交协调逻辑。未发现需要擅改契约的字段差异；模型字段、精度、分类排序规则、CHECK和索引与 SQL 设计方向一致。此结论为静态审查，不替代 MySQL 实际执行。

主 Agent 发现并分派的 POST 5xx 不确定结果风险，已由前端修复。QA 完成独立错误函数与真实503页面复测，见 [BUG_REPORT.md](BUG_REPORT.md)。当前没有由 QA 独立执行发现且未关闭的 P0 业务缺陷，但这不等于核心业务验收通过。

## 初始阶段受阻与未执行（历史）

- 用户尚未准备 `mysql8` / 本地连接配置，本轮没有成功 MySQL 新增、查询、统计、字段 SQL 对照或持久化验证。
- 真实集成套件39项仍受阻；覆盖正常写入、金额上下限、SQL精度、文本边界、汇总、共享筛选和重新建立HTTP连接。
- 页面新增收入和支出、对应记录 SQL 查询、真实统计、浏览器刷新、后端重启后持久化仍未执行；HTTP客户端重连也尚未执行，不作为替代证据。
- P1 编辑、删除、筛选UI和图表尚未安排，不计为本轮已完成或已通过。
- 当前截图可用于展示 P0 页面及错误处理，最终交付仍需补充数据库可用时的真实运行截图。

数据库就绪后：重启后端加载 `.env` → 主 Agent 确认实际表结构 → QA 在唯一分类和明确ID下运行真实套件 → 执行页面收入 / 支出与SQL交叉验证 → 复测并更新本报告。不得清空用户数据或重启 / 删除共享MySQL。
