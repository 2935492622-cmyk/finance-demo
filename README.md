# 简易记账 Demo

项目使用 Python 后端、Vue 前端和本地 Docker MySQL 存储收支数据。

已初始化本地 Git 仓库（分支 `main`），创建项目内 `.venv/` 并锁定 Python 依赖；Vue 3 / Vite 前端和 FastAPI 后端已实现核心及拓展功能。前端依赖安装在 `frontend/node_modules/`。尚未创建 Git 提交；P0 真实 MySQL 写入、汇总、浏览器刷新及后端重启持久化已经验证。

第二阶段规划已于 2026-11-16 获用户确认。用户已部署 MySQL 8.4.13；项目建表、专用账号及私有 `backend/.env` 已配置。第三阶段 P0 / P1 已完成，真实 API、页面编辑删除、筛选、图表、SQL 对照和持久化均经实测，用户当前无需手动填写连接配置。

## 环境要求

| 环境 | 本次实测 |
| --- | --- |
| 系统 | WSL2 Ubuntu 26.04 LTS |
| Python | 3.14.4，所有项目依赖位于 `.venv/` |
| Node.js / npm | v24.22.2 / 11.19.1，前端声明 Node >=22.12.0 |
| Docker / MySQL | Docker Engine 29.9.2、MySQL 8.4.13；建表最低要求 MySQL 8.0.16 |
| AI 开发 | 现有 VS Code Codex 插件与原生 Subagents，无需安装 Codex CLI |

## 规划文档与审阅入口

| 文档 | 审阅内容 |
| --- | --- |
| [PRD](docs/PRD.md) | 核心功能、拓展顺序、页面交互和验收标准 |
| [架构](docs/ARCHITECTURE.md) | Vue → FastAPI → SQLAlchemy → MySQL 数据流和模块职责 |
| [API 契约](docs/API_CONTRACT.md) | 统一字段、金额格式、接口、筛选和错误响应 |
| [数据库设计](docs/DB_DESIGN.md) | 表结构、索引、精度、时区和初始化边界 |
| [任务看板](docs/TASK_BOARD.md) | 三个 Agent 的任务、文件边界、依赖和交付报告 |
| [测试计划](docs/TEST_PLAN.md) | 边界用例、真实 MySQL / 页面验收和证据要求 |
| [建表 SQL](database/schema.sql) | 仅初始化 finance_demo，已在 MySQL 8.4.13 执行 |
| [初始数据库连接检查](docs/DATABASE_CONNECTION_CHECK.md) | 本地 .env 配置、专用权限和首次连通记录；当前验收以 QA 报告为准 |
| [MySQL 准备清单](docs/MYSQL_SETUP.md) | 用户部署后的建表、专用账号和本地配置步骤 |
| [前端交付报告](frontend/DELIVERY.md) | 组件、交互、实际测试结果和限制 |
| [后端交付报告](backend/DELIVERY.md) | 校验、事务、SQL 汇总和实际测试结果 |
| [QA 交付报告](docs/qa/DELIVERY.md) | 独立测试、审查、证据与受阻项 |
| [QA 实测报告](docs/qa/TEST_REPORT.md) | 每项实际命令、结果、截图和未验收内容 |
| [第三阶段补齐记录](docs/PHASE_3_PROGRESS.md) | P0 放行、P1 分派、缺陷根因与复测过程 |
| [Multi-Agent 学习导读](docs/MULTI_AGENT_WALKTHROUGH.md) | 分工、代码阅读顺序、Bug 协作与测试证据 |

上述规划版本为 0.1，已经确认；按契约实现，变更需由主 Agent 提出并再次确认。建议先看 PRD 的功能范围，再看 API 的数据结构与示例，最后查看任务看板中的第一批派发任务。

## 已实现功能

- 添加收支：金额、收入 / 支出类型、分类、记账日期、可选备注。
- 在页面展示全部收支记录。
- 自动计算总收入、总支出和结余。
- 后端提供新增、查询、统计、编辑、删除接口，数据通过 MySQL 持久化，刷新页面不会丢失。
- 编辑回填 / 取消、删除确认 / 取消、类型 / 分类 / 日期组合筛选及清空。
- ECharts 支出分类图，与当前筛选及统计卡片一致，支持空状态和窄屏。

## 项目目录与隔离规则

```text
finance-demo/
├── AGENTS.md                 # 项目开发规则
├── README.md                 # 环境恢复、启动和清理说明
├── .gitignore
├── .codex/                   # 项目级并发配置和三个 Agent 角色 TOML
├── .tools/                   # 本地浏览器运行库，不提交
├── .venv/                    # 本地 Python 虚拟环境，不提交
├── docs/                     # PRD、架构、API、数据库、任务和测试规划
│   └── qa/                  # QA 用例、缺陷及实测报告
├── database/
│   └── schema.sql            # 首次建表 SQL，已执行验证
├── screenshots/              # 真实桌面、窄屏、编辑及筛选截图
├── tests/                    # 独立 QA 契约、MySQL 和浏览器测试
├── backend/
│   ├── app/                  # FastAPI、模型、校验与数据库操作
│   ├── tests/                # 开发者离线测试
│   ├── .env                  # 本地真实连接配置，不提交
│   ├── .env.example          # 可提交的配置模板
│   ├── requirements.in       # 直接依赖及允许的版本范围
│   └── requirements.txt      # 实际安装版本及间接依赖，恢复环境使用
└── frontend/
    ├── src/                  # Vue 组件、Axios、状态和金额工具
    ├── tests/                # 前端逻辑测试
    ├── package.json          # 前端依赖和脚本
    ├── package-lock.json     # 依赖锁文件，必须提交
    └── node_modules/         # 本地依赖，不提交
```

除明确独立于项目的共享 MySQL 服务与 Docker 命名卷外，全部代码、依赖、配置、文档及 Agent 角色定义必须保存在本文件夹内。不得安装全局 Python 或前端项目依赖，不得修改 `~/.codex/`，不得影响其他项目。

## Python 环境恢复与启动约定

当前环境使用 Python 3.14.4；已验证以下依赖在该环境中可以导入。新环境在项目根目录创建虚拟环境，并通过该环境的 Python 安装锁定版本：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --no-cache-dir -r backend/requirements.txt
```

所有后端依赖必须列入 `backend/requirements.txt`，不得使用全局 pip 安装。`.venv/` 已加入忽略规则。

当前直接依赖如下：

| 依赖 | 用途 |
| --- | --- |
| FastAPI、Uvicorn | API 框架和开发服务器 |
| SQLAlchemy | 数据模型和数据库操作 |
| Pydantic、pydantic-settings、python-dotenv | 参数校验及 `.env` 配置读取 |
| PyMySQL（含 RSA 支持） | MySQL 8 连接及认证 |
| pytest、HTTPX | 后端和 API 测试 |

MySQL 驱动方案参考 [SQLAlchemy 官方 MySQL / PyMySQL 文档](https://docs.sqlalchemy.org/en/20/dialects/mysql.html#module-sqlalchemy.dialects.mysql.pymysql)。

如需在终端激活虚拟环境：

```bash
source .venv/bin/activate
```

激活只是切换终端默认解释器；直接使用 `.venv/bin/python` 也可以保持依赖安装隔离。开发中需要变更依赖时，先修改 `backend/requirements.in`，再安装并更新锁定清单：

```bash
.venv/bin/python -m pip install --no-cache-dir -r backend/requirements.in
.venv/bin/python -m pip freeze > backend/requirements.txt
.venv/bin/python -m pip check
```

已通过依赖一致性、虚拟环境隔离、模块导入、校验、MySQL 真实读写和 SQL 对照。离线 HTTP 测试使用 HTTPX ASGITransport，不导入此前提示弃用的 TestClient / HTTPX 组合，不靠隐藏警告通过。

后端入口为 `backend/app/main.py`。在项目根目录启动：

```bash
.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload
```

API 地址 `http://127.0.0.1:8000/api`，Swagger 地址 `http://127.0.0.1:8000/docs`。已真实启动 Uvicorn，验证 `/docs` 和 `/openapi.json` 为 200；早期数据库未就绪时验证了 503。最新连接配置完成后，health、列表和空集合统计均返回 200。修改或新建 `backend/.env` 后必须重启后端，不能假定配置会热加载。

在 AI 工具会话中保持本地预览时，也可使用项目内后台启动工具，避免把应用生命周期绑定到临时终端。日志和 PID 只保存在忽略的 `.tools/dev/`：

```bash
.venv/bin/python scripts/backend_process.py start
.venv/bin/python scripts/backend_process.py status
.venv/bin/python scripts/backend_process.py stop
```

此工具只管理自己启动并核对过 PID、启动时间、命令和工作目录的本项目后端；端口被其他进程占用时不终止对方。修改 `.env` 后先 stop 再 start。它不操作 Docker 或 MySQL。

## Vue 环境恢复与启动约定

在 `frontend/` 内恢复锁定依赖并运行：

```bash
cd frontend
PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npm ci --cache .npm-cache
npm run dev
```

`package.json`、`package-lock.json` 和 scripts 均已创建。前端开发依赖包含供 QA 使用的本地 Playwright 驱动，恢复应用依赖不需要下载浏览器。浏览器测试运行库见 [本地 QA 环境](docs/LOCAL_QA.md)。

Vue、Axios、ECharts 等依赖只安装在 `frontend/node_modules/`，不使用全局安装。两个 package 文件必须保留并提交，`node_modules/` 已加入忽略规则。前端地址 `http://127.0.0.1:5173`，Vite 固定端口并把 `/api` 代理到 `http://127.0.0.1:8000`。ECharts 按需导入并作为独立异步组件加载，图表取自同一份后端 summary。

## Codex Agent 环境

开发规则见 [AGENTS.md](AGENTS.md)。项目专属 Agent 配置及角色定义统一存放于 `.codex/`，最多同时运行 3 个子 Agent。

已按 [OpenAI 官方 Subagents 文档](https://learn.chatgpt.com/docs/agent-configuration/subagents)准备 `.codex/config.toml` 和 `.codex/agents/` 中的三个角色 TOML。`agents.max_concurrent_threads_per_session = 3` 表示子线程并发上限，主线程不计入；禁止子 Agent 创建后代的规则也写入三个角色指令。不会修改 `~/.codex/`，不安装 Codex CLI 或其他多 Agent 框架。

第一阶段已验证原生子 Agent 调用，第三阶段已实际并行派发前端、后端、QA 三个角色。当前会话派发工具没有单独的自定义角色参数，主 Agent 读取角色文件并明确传入职责和边界，不声称配置已热加载。三个子 Agent 均未创建后代，角色分工和共享目录下的文件责任见任务看板。

## MySQL：长期共用服务

MySQL 使用 Docker 部署，容器名称统一为 `mysql8`。数据库数据使用 Docker 命名卷持久化；建议卷名为 `mysql8_data`，已有服务则沿用其现有命名卷。禁止将 `/var/lib/mysql` 映射到本项目目录。

服务供多个项目长期共用，本项目只创建和使用 `finance_demo` 数据库，其他项目各用独立数据库。MySQL 容器及数据卷不属于本项目的临时依赖，删除项目后必须保留。

配置前先检查现有服务与命名卷：

```bash
docker ps -a --filter name='^/mysql8$'
docker volume ls
```

若已有 `mysql8`，检查并复用，不得直接覆盖、重建或重置。仅在确认没有现有服务、预定卷没有需要保留的数据、宿主机端口可用后，才按以下示例首次创建。命令在 Bash 中运行，通过交互输入密码，密码不写入项目文件：

```bash
read -r -s -p 'MySQL root 密码: ' MYSQL_ROOT_PASSWORD
export MYSQL_ROOT_PASSWORD
docker volume create mysql8_data
docker run -d \
  --name mysql8 \
  --restart unless-stopped \
  -p 127.0.0.1:3306:3306 \
  -e MYSQL_ROOT_PASSWORD \
  -v mysql8_data:/var/lib/mysql \
  mysql:8.4
unset MYSQL_ROOT_PASSWORD
```

共享服务就绪后，可通过交互式客户端连接：

```bash
docker exec -it mysql8 mysql -u root -p
```

确认 MySQL 为 8.0.16 或更新的 8.x 版本，且已检查已有同名表结构后，在交互式客户端执行 [database/schema.sql](database/schema.sql) 的完整内容。该脚本创建 `finance_demo` 及 `transactions` 表，不含用户密码和测试记录；当前本机已完成初始化。已有同名表不会自动迁移，不能通过删表重建来处理结构差异。

为应用配置专用数据库用户，并仅授予 `finance_demo` 所需权限。实际账号与密码在本地设置，不提交真实凭据。后续项目复用同一 MySQL 服务时不得复用本项目数据库，也不得修改其他项目的数据库或账号权限。

## 数据库连接配置

当前本机 `backend/.env` 已配置并验证成功，不需要重新复制。恢复到新环境且尚无该文件时，可先复制模板，再本地编辑真实连接信息；不要覆盖已有密码：

```bash
cp -n backend/.env.example backend/.env
```

`backend/.env.example` 仅包含示例值；`backend/.env` 保存真实配置并已加入忽略规则。当前约定变量如下，后端实现必须读取这些变量或同步更新模板与文档：

| 变量 | 用途 |
| --- | --- |
| `DB_HOST` | MySQL 地址，本机开发默认 `127.0.0.1` |
| `DB_PORT` | MySQL 端口，默认 `3306` |
| `DB_NAME` | 固定为 `finance_demo` |
| `DB_USER` | 本项目专用数据库账号 |
| `DB_PASSWORD` | 本地填写的真实密码 |

不得把真实密码写入版本库、日志、README 或示例文件。新环境启动后端前，按 MySQL 准备清单完成数据库与账号配置；当前本机无需重新建库、建表或重设账号。

## 常见问题与当前限制

- **现在可以使用记账页面吗？** 当前本机配置完成，可以使用。新环境应先启动数据库、后端和前端；数据库失败会显示真实错误，不展示虚假的零统计。
- **需要重新部署 MySQL 吗？** 当前不需要，直接复用 `mysql8`。新环境才按准备清单配置，不重建已有服务。
- **刷新为什么能保留数据？** 页面每次从 API 读取 MySQL 中的记录，不依赖浏览器本地缓存；浏览器刷新及后端重启均已实际验证。
- **端口被占用怎么办？** 先检查占用进程，不终止其他项目服务；如需调整端口，由主 Agent 同步代理及运行文档。
- **数据库连接失败怎么办？** 本地检查容器状态、端口、.env 和数据库账号权限；不要把密码贴进聊天或日志，也不要删除容器或命名卷来修复连接。
- **修改 .env 后仍连不上？** 重启本项目后端进程，以重新读取配置和创建 Engine；不需要重启共享 MySQL。
- **保存显示结果未确认怎么办？** 页面会阻止重复提交；先恢复连接并刷新核对明细，确认上一笔是否已存在，再决定是否补记。

## 测试与真实验收

项目根目录：

```bash
FINANCE_QA_INTEGRATION=1 .venv/bin/python -m pytest backend/tests tests -q -rs
.venv/bin/python -m pip check
```

主 Agent 最终联合复跑 **193 passed，0 skipped**，依赖一致性通过。包括 106 项后端开发者测试、24 项独立校验 / 故障路径、39 项 P0 真实 MySQL 和 24 项 P1 真实 MySQL。独立 QA 联合结果为 87 passed；同一批用例不重复累加。省略 `FINANCE_QA_INTEGRATION=1` 时真实数据库用例默认跳过。

在 `frontend/` 内：

```bash
npm test
npm run build
```

前端逻辑测试 **26 / 26 通过**，构建通过。真实浏览器实际操作新增、编辑、取消、删除、组合及快速筛选、清空与空图表，核对 SQL、统计和真实 ECharts 图形 / 图例；390px、320px 无页面横向溢出且金额单行。测试没有拦截伪造数据库响应。P0 还实际验证了浏览器刷新和后端重启持久化。

最终真实截图：[桌面](screenshots/p1-final-desktop.png)、[390px 手机](screenshots/p1-final-mobile390.png)、[320px 手机](screenshots/p1-final-mobile320.png)、[筛选](screenshots/p1-filtered.png)、[编辑](screenshots/p1-editing.png)。旧的 `database-unavailable` 图片仅为历史错误状态证据。

当前保留两笔由页面实际写入的演示记录：收入 `1000.00`、支出 `125.50`，结余 `874.50`，备注有 `qa-demo-` 标记，可在页面编辑或删除。其余测试记录按明确 ID 清理，不清空用户表。独立测试命令和数据边界见 [tests/README.md](tests/README.md)。

测试期间两次观察到临时会话中的后端收到 SIGTERM 退出，来源未确认，MySQL 和记录不受影响。恢复后完整页面复跑通过；最终改为项目内脱离临时会话的后台启动方式，并验证启停、重复启动保护与健康接口。

## 项目清理

项目结束后，仅删除 `finance-demo/` 文件夹，即可移除项目代码、Python 虚拟环境、Node 依赖、项目 Agent 配置和文档。

删除前先停止正在使用的本项目前后端进程：后台启动的后端用上述 stop，前台进程在自己的终端按 Ctrl+C；不停止共享 MySQL。

`mysql8` 容器、Docker 命名卷以及其中的数据库和收支数据继续保留。项目清理不得停止、删除、重置共享数据库服务，也不得删除其数据卷。禁止将 `docker rm mysql8`、`docker volume rm`、`docker compose down -v` 或 Docker prune 操作纳入项目清理流程。
