# 后端模块交付报告

日期：2026-11-16。范围：BE-01、BE-02 和 BE-03。P0 / P1 已由 QA 和主 Agent 完成真实 MySQL、浏览器与 SQL 交叉验收，包括新增、编辑、删除、筛选、图表及刷新 / P0 后端重启持久化。执行归属与证据见 [QA 总报告](../docs/qa/TEST_REPORT.md)和 [P1 报告](../docs/qa/P1_TEST_REPORT.md)。

## 完成内容

- FastAPI 入口 `app.main:app`，同步路由及请求级 SQLAlchemy Session。
- Pydantic 严格金额、类型、分类、备注和日期校验；拒绝未知请求体 / 查询字段。
- MySQL / PyMySQL 引擎、分立配置的安全 URL 构造、UTC 会话、严格 SQL 模式检查、连接探活和有界连接超时。
- 与 `database/schema.sql` 对齐的 ORM 类型、约束、索引和时间默认值；没有自动建库建表逻辑。
- POST `/api/transactions`、GET `/api/transactions`、GET `/api/summary`、GET `/api/health`。
- PUT `/api/transactions/{id}` 全量编辑、DELETE `/api/transactions/{id}` 物理删除；存在性检查与写入在同一事务中完成。
- 列表与统计共用类型、分类、日期筛选；列表无默认截断；Decimal 统计包含支出分类汇总。
- 契约规定的中文、脱敏 422 / 503 / 500 错误格式；写入异常回滚、会话关闭，以及连接中断时的清理保护。
- 106 项独立于真实数据库的校验、HTTP 层、SQL 编译和故障注入单元测试，包含 40 项本轮 P1 用例。

P1 PUT / DELETE 已实现，本轮未并行写入真实数据库，也没有改动演示记录 27 / 28。未改动 API 契约、前端、数据库 SQL、全局配置或根文档；未创建子 Agent、共享容器、数据库或真实凭据。

## 交付文件

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── crud.py
│   ├── exceptions.py
│   └── routers/
│       ├── __init__.py
│       ├── transactions.py
│       └── health.py
├── tests/
│   ├── conftest.py
│   ├── test_validation.py
│   ├── test_http_contract.py
│   ├── test_database_and_queries.py
│   └── test_edit_delete.py
└── DELIVERY.md
```

P1 本轮仅修改 `app/schemas.py`、`app/crud.py`、`app/routers/transactions.py`、本报告，并新增 `tests/test_edit_delete.py`。沿用已有 `requirements.in`、`requirements.txt`、`.env.example`，没有新增、升级依赖；用户现已配置的真实 `.env` 未被输出或覆盖。

## 实现方案和应理解的知识点

`schemas.py` 是 API 边界。金额必须先是匹配约定格式的字符串，然后转 Decimal，避免 JSON 浮点数进入计算；写入最大值由格式限制为八位整数和两位小数。响应另外使用固定两位小数序列化，统计模型不复用单笔上限。日期先检查 `YYYY-MM-DD` 文本和日历有效性，再校验 MySQL DATE 范围。

`models.py` 是持久化结构，`Numeric(10,2,asdecimal=True)` 将 Python Decimal 与数据库精确小数连接。数据库 CHECK 是最后一道防线，不能代替 API 校验。新建记录显式共享一个 UTC 时间，保证 created_at 与 updated_at 相同；响应把 UTC DATETIME 显式标为六位微秒的 `Z` 时间。

`crud.py` 只处理数据库操作。新增先 add、再 commit，提交失败不会返回成功；使用 `expire_on_commit=False` 保留已提交数据，避免提交后再查询失败导致成功状态不确定。`filter_conditions` 被列表和两种统计查询共用。收入、支出和分类汇总在 SQL 中计算，Python 层仍为 Decimal，空结果转 `0.00`。

P1 路径 ID 在 Pydantic 常规 int 转换前检查 ASCII 十进制数字，再校验 `1`～`4294967295`；因此 `1.0`、`1e0`、`+1`、负数、Unicode 数字和空白都返回 `path.id` 的 422，不会被宽松转换为已有记录 ID。未额外限制前导零，契约未要求 ID 文本规范化。

编辑和删除先用 `Session.get(..., with_for_update=True)` 锁定目标记录；不存在返回统一 404，存在才修改或删除，commit 成功后才返回 200 / 204。PUT 与 POST 使用同一个 TransactionWrite，`model_dump()` 包含默认空 note，因此省略 note 会清空备注；只写五个可写字段，保留 id 和 created_at。DELETE 使用显式 Response，204 没有 JSON、Content-Type 或响应体，重复删除为 404。

更新时间选择旧值和当前 UTC 的较大值。自查发现“时钟回拨时将同一旧值赋回”的细节：ORM 可能认为该字段没变，从而应用模型的 onupdate 默认时间，仍使时间倒退。现用 `flag_modified` 显式要求 chosen updated_at 参与 UPDATE，并用 clean-loaded ORM 状态测试覆盖此根因；不会改动接口或数据库结构。

`database.py` 每个请求提供独立 Session，异常后 rollback，最终 close。自查发现连接已经断开时 rollback / close 也可能再次失败，现已保护清理流程，避免第二个数据库异常遮蔽原本的脱敏 503。无效的本地数据库配置也转换为脱敏 503，不把 Pydantic 的配置值返回给前端。连接时只修改本会话时区，不改共享服务器全局设置。

`exceptions.py` 将校验错误定位到 `body.amount`、`query.start_date` 等契约字段，只选取安全字段路径和固定中文消息，不回传原始输入、SQL、驱动消息或密码。未知异常返回固定 500 文案。

测试使用 [HTTPX 官方 ASGITransport](https://www.python-httpx.org/advanced/transports/#asgi-transport)，不导入当前已提示弃用的 Starlette TestClient / HTTPX 组合，也不隐藏警告。共享查询模型使用 [FastAPI Query Parameter Models](https://fastapi.tiangolo.com/tutorial/query-param-models/)，OpenAPI 中可见四个筛选参数。连接事件参考 [SQLAlchemy 官方事件文档](https://docs.sqlalchemy.org/en/21/core/events.html#sqlalchemy.events.PoolEvents.connect)。

## 启动方法

在项目根目录恢复依赖：

```bash
.venv/bin/python -m pip install -r backend/requirements.txt
```

用户已部署 MySQL 并配置专用账号。下列命令仅供新环境首次准备；已有 `.env` 时保留本地真实连接信息：

```bash
if [ ! -f backend/.env ]; then cp backend/.env.example backend/.env; fi
```

编辑真实连接信息，不提交 `.env`。启动：

```bash
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

API 为 `http://127.0.0.1:8000/api`，Swagger 为 `http://127.0.0.1:8000/docs`。正式 8000 进程由主 Agent 统一启动和验证，本子 Agent 未另启服务占用该端口。

没有 `.env` 时应用可以导入和启动，使用本机地址、项目专用用户名及空密码作为默认值，不会创建账号或凭据；数据库不可用时请求返回 503。**新建或修改 `.env` 后须重启后端进程**，配置与 Engine 是进程级缓存，不依赖 `.env` 热加载。

## 实际测试和结果

```bash
.venv/bin/python -m pytest backend/tests -q
.venv/bin/python -m pip check
```

本轮回归结果：**106 passed in 0.65s**。P0 初版的 pip check 输出 `No broken requirements found.`，之后未变更依赖；本轮没有新增依赖。

测试覆盖严格金额、类型、日期、Unicode 长度、必填 / 多余字段，固定响应金额和 UTC 时间，未知查询 / 日期颠倒错误位置，破损 JSON，数据库 / 未预期异常的 503 / 500 脱敏，回滚与关闭（包括清理再次失败），模型类型 / 约束 / 索引的 MySQL 编译，参数化共享筛选、排序无截断及 Decimal 精确汇总、空集合和大额响应。

P1 新增覆盖非法 ID / 上下界 ID、全量编辑和省略 note 清空、只读字段保留、非法编辑不触碰原记录、时间回拨和 ORM 默认值陷阱、目标不存在和重复删除、204 空体、提交失败的 503 / rollback / close，以及 OpenAPI 路径约束。首轮发现 OpenAPI 将后置约束生成 `ge/le` 而非标准 `minimum/maximum`，已调整 Annotated 验证器顺序并通过回归。

实现期间还通过临时 HTTPX 内存请求实测 `/openapi.json` 为 200，缺数据库时 `/api/health` 为 503，非法查询和金额为 422。该检查未启动网络服务器，也没有成功数据库写入。SQLAlchemy 模型编译和受控 Session 替身测试只验证代码行为，**不算真实 MySQL、持久化或端到端通过**。

后续真实验收由 QA / 主 Agent 执行并通报：QA 独立套件 **87 passed，0 skipped**，包含 39 项 P0 真实 MySQL、24 项 P1 真实 MySQL 和 24 项校验 / 故障路径。浏览器新增收入 ID 27、支出 ID 28 后通过 SQL、列表、summary 复核，刷新及 P0 后端重启后仍一致；P1 页面编辑、删除、筛选和 ECharts 同样通过真实 SQL 交叉验证。证据见 [QA 总报告](../docs/qa/TEST_REPORT.md)、[P1 验收报告](../docs/qa/P1_TEST_REPORT.md)及其截图和原始结果链接。

主 Agent 另行联合复跑结果为 **193 passed in 5.23s，0 skipped**，并确认 pip check 通过。以上真实数据库、浏览器和联合复跑结果归属 QA / 主 Agent，本子 Agent 没有亲自执行这些真实数据库验收；本子 Agent 的执行结果仍是上文 **106 项离线单测 / ASGI 检查**，不能重复计算或混同。

## 验收结论与维护边界

- 后端 P0 / P1 和真实页面联调已经独立验收，无待关闭的后端业务缺陷；本次仅同步交付文档，未改业务代码、依赖或重新运行测试。
- 数据库已有数据时继续按基线和测试 ID 隔离，不清空用户表，不修改保留的演示记录 27 / 28。
- 后续若发现缺陷，由主 Agent 分派本模块修复；不自行改契约或跨目录修改。
- 无论移除项目还是运行测试，都不停止、重建或删除共享 `mysql8` 和命名卷。
