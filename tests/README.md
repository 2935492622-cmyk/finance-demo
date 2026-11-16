# 独立 QA 测试

此目录由 qa-reviewer 维护，与 `backend/tests/` 的开发者单测分开。

默认执行独立校验 / 连接失败检查，并跳过成功写入的真实集成用例；不会修改数据库：

```bash
.venv/bin/python -m pytest tests -q -rs
```

MySQL、表结构、应用账号、`backend/.env` 和本地 FastAPI 均准备后，明确启用真实测试：

```bash
FINANCE_QA_INTEGRATION=1 .venv/bin/python -m pytest tests/test_mysql_api.py -q -rs
```

可选 `FINANCE_QA_API_URL` 指向本地 API 根地址，默认 `http://127.0.0.1:8000/api/`。禁止嵌入凭据或指向非本机服务。MySQL 凭据只从本项目 `backend/.env` 读取，数据库名必须为 `finance_demo`。

真实用例通过 HTTP 新增带随机分类 / 备注标记的测试记录，并直接查询 MySQL 核对。每个测试结束时仅按自己收到的 ID、预期分类、预期备注三重条件删除自己的记录，不清空用户表，不创建数据库，不控制容器。不并发运行这些验收用例；HTTP 超时或进程中断可能使记录未被登记，此时按唯一 `qa-` 标记人工核对并由主 Agent 决策清理，不能批量删除所有 qa 数据。

`test_mysql_api.py`覆盖P0 API、SQL、金额 / 日期 / 类型 / 文本边界、聚合和后端共享筛选。HTTP客户端重连不等于浏览器刷新或后端重启测试；浏览器操作、截图与重启持久化需单独执行并记录。P1编辑、删除和页面筛选/图表另由下述用例验证。

P1已补充 `test_p1_mysql_api.py`，后端加载相应路由后，启用 `FINANCE_QA_INTEGRATION=1` 运行整个 `tests/` 可同时执行P0/P1。当前实测为87 passed（24离线+39P0真实API+24P1真实API），不能将未启用时的skipped算通过。

`test_contract_without_db.py` 使用真实 FastAPI ASGI 应用和一个未监听的本机 TCP 端口，检查 422 与真实连接拒绝后的 503；不使用 SQLite 或伪造成功响应，也不代表 MySQL 写入验收通过。

## 数据库未就绪时的真实浏览器冒烟

前后端由主 Agent 启动后，复用已有浏览器及项目内运行库执行；该脚本不启动服务、不下载安装、不拦截请求：

```bash
FINANCE_QA_BROWSER_EXECUTABLE=/home/ava/.cache/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-linux64/chrome-headless-shell \
FINANCE_QA_BROWSER_LIBRARY_PATH="$PWD/.tools/browser-runtime/root/usr/lib/x86_64-linux-gnu" \
TMPDIR="$PWD/.tools/browser-runtime/tmp" \
node tests/browser_p0_smoke.mjs
```

`TMPDIR` 需事先存在。`FINANCE_QA_FRONTEND_URL` 可选，默认 `http://127.0.0.1:5173`。该脚本要求 health 返回真实 503；如果 MySQL 已可用会停止，避免把失败状态测试变成未经登记的成功新增。结果写入 `docs/qa/browser-p0-result.json`，桌面和移动截图明确命名为 `database-unavailable`，不能用来宣称成功记账或持久化。

## 数据库就绪后的页面成功与重启持久化

使用相同浏览器环境变量运行 `node tests/browser_p0_success.mjs`，会真正通过页面创建两笔演示记录并暂保留。初始基线、明确ID及唯一备注保存于被忽略的 `tests/.p0-demo-state.json`，无密码。凭据由Python桥接脚本直接从backend/.env读取，只查询这两个ID，并输出脱敏字段和全库聚合。

主Agent重启本项目后端后运行 `node tests/browser_p0_success.mjs --verify-after-restart`：只读复查页面、API和SQL，不重复新增。状态文件已存在时禁止再次运行新增入口；如需新的演示运行，先由主Agent核对原两笔的保留或清理安排，不擅自删除状态重跑。

输出 `docs/qa/browser-p0-success-result.json` 和成功/重启后截图。移动检查同时要求文档无横向溢出、统计金额单行、演示备注不被压成纵向碎行。

## P1真实页面验收

前后端P1稳定且health200后，使用相同浏览器环境变量运行 `node tests/browser_p1_acceptance.mjs`。会页面新增4条唯一标记记录，测试编辑/删除取消与确认、筛选/空态/快速请求、真实ECharts实例及SVG/path尺寸、390/320px布局，并在finally按明确ID+最新分类/备注清理自己的记录。

初始保护基线来自该次真实列表快照，不固定用户ID或数量。`tests/.p1-demo-state.json` 保存无密码运行状态并忽略Git；若上次未完成清理，工具拒绝直接覆盖状态重跑，应先由主Agent核对已登记ID。该脚本不会修改基线记录、建库或控制容器。完整命令和实际证据见 `docs/qa/P1_TEST_REPORT.md`。
