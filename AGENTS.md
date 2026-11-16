# 项目开发规则

## 适用范围与交付目标

本文件适用于 `finance-demo/` 目录及其所有子目录。开发、运行、维护和清理操作必须遵守以下规则。

本项目是简易记账 Demo：使用 Vue 3 + Vite、FastAPI、SQLAlchemy、Pydantic、Axios 和 MySQL，支持添加金额、收入 / 支出类型、分类、记账日期和备注，展示全部记录，自动计算总收入、总支出和结余。后端提供数据库新增和查询接口，刷新页面后数据仍然保留。编辑、删除、分类 / 日期筛选和 ECharts 简单图表为后续拓展。

## 目录隔离

- 所有项目代码、依赖、配置、文档和 Agent 角色定义均保存在 `finance-demo/` 内。
- 禁止修改用户级全局 Codex 配置或 `~/.codex/` 中的现有文件。
- 禁止安装全局 Python、Vue、Axios、ECharts 等项目依赖，也不得影响其他项目的环境和 Agent 设置。
- Docker 提供的长期共用 MySQL 服务和命名卷是目录隔离的明确例外，不能作为本项目临时依赖管理。

## Python 后端

- 在项目根目录的 `.venv/` 创建虚拟环境，所有 Python 项目依赖只安装到该环境。
- 使用 `.venv/bin/python -m pip` 安装依赖，避免误用系统 Python 或全局 pip。
- 后端依赖清单保存于 `backend/requirements.txt`，新增或变更依赖时同步维护。
- 在 `README.md` 中维护可执行的环境恢复和启动说明；实现后必须记录真实入口和所需配置。
- `.venv/` 必须加入 `.gitignore`。

## Vue 前端

- 前端项目保存在 `frontend/`，依赖安装到 `frontend/node_modules/`。
- `frontend/package.json` 和 `frontend/package-lock.json` 必须保留并纳入版本管理。
- 禁止全局安装 Vue、Axios、ECharts 等项目依赖。通过项目 npm scripts 执行工具。
- 已有锁文件时使用 `npm ci` 恢复环境；变更依赖后同步更新锁文件。
- `node_modules/` 必须加入 `.gitignore`。

## Codex Agent

- 优先采用项目级配置，项目专属配置及角色定义保存在 `finance-demo/.codex/`。
- 配置必须采用当前 Codex 插件实际支持的格式，创建前确认支持情况；不得猜测配置键或以不受支持的文件冒充生效配置。
- 本文件承载项目开发规则；不得通过修改 `~/.codex/` 实现项目设置。
- 最多同时运行 3 个子 Agent；该上限不代表自动授权启动子 Agent。
- 主 Agent 不占上述 3 个子 Agent 额度，所有后代均计入；禁止子 Agent 创建、委派或启动任何后代 Agent。所有任务由主 Agent 统一分配，不另外设项目经理子 Agent。
- 第二阶段由主 Agent 生成规划；用户确认前不得进入并行业务开发。先完成并验证 P0，再由主 Agent 安排 P1。
- 角色定义保存在 `.codex/agents/`；原生派发时须明确传入角色指令，不能假定文件已被当前会话热加载。
- `frontend-developer` 只修改 `frontend/**`；`backend-developer` 只修改 `backend/**`；`qa-reviewer` 只修改 `tests/**`、`docs/qa/**` 和 `screenshots/**`，默认不改业务代码。
- 主 Agent 维护根文档、`.codex/`、六份规划文档及 `database/schema.sql`，统一处理模块冲突。子 Agent 不自行提交、重置或切换 Git。
- 开发前必须阅读 `docs/API_CONTRACT.md` 及角色相关规划。已确认的路径、字段、数据类型和行为不得擅改；变更由主 Agent 提出并经用户确认后同步文档、实现与测试。
- 每个角色必须提供完成内容、文件、方案、启动方式、测试命令、实测结果和遗留问题；缺陷由 QA 报告、主 Agent 分派、对应开发角色修复、QA 复测。
- 如当前插件无法提供所需项目级能力，在项目文档中说明限制，不得回退到修改全局配置。

## MySQL 服务与数据

- 使用 Docker 部署长期共用的 MySQL 8 服务，通用容器名称固定为 `mysql8`。
- 使用 Docker 命名卷持久化 `/var/lib/mysql`；不得将 MySQL 数据目录放入 `finance-demo/`，也不得使用项目内数据目录的 bind mount。
- 优先复用现有 `mysql8`。创建服务前检查容器和卷是否已存在，不得擅自替换、重建或重置已有服务。
- 本项目只创建和使用独立数据库 `finance_demo`。其他项目可复用服务，但必须使用各自独立的数据库。
- 应用优先使用仅具有 `finance_demo` 所需权限的专用用户，不使用 root 作为日常应用账号。
- 数据库连接配置通过 `backend/.env` 管理。提供 `backend/.env.example`，其中只允许示例值或占位符。
- 真实密码、连接凭据和真实 `.env` 文件不得提交到版本库，也不得写入日志或文档。
- 涉及现有数据的删除、重置、数据库迁移等操作，必须明确其影响并遵守用户已授权范围。

## 清理边界

- 项目结束后，删除整个 `finance-demo/` 即可清理代码、`.venv/`、Node 依赖、项目 Agent 配置及文档。
- 删除项目目录不会清理数据库中的记录；这些数据随共享 MySQL 服务保留。
- 项目清理脚本、任务和文档不得删除 `mysql8` 容器或其 Docker 数据卷。
- 禁止在项目清理中使用 `docker rm mysql8`、`docker volume rm`、`docker compose down -v`、Docker prune 等可能移除共享服务或持久数据的操作。
- 不得为清理本项目而停止、重置共享 MySQL 服务，或修改其他项目的数据库和权限。

## 文档维护与验证

- 代码实现后，README 必须与实际依赖、启动命令、环境变量、数据库初始化方式和接口保持一致。
- 不得把尚未执行的安装、启动和测试描述为已成功完成。
- 数据库部署由用户负责，第三阶段开始前提醒用户；不得擅自创建 MySQL 服务。真实连接、接口和持久化验收必须在 MySQL 就绪后进行。
- 不能用模拟响应、SQLite 或静态截图替代真实浏览器新增、MySQL 查询、统计及刷新持久化验证。不清空用户数据，只按明确的测试记录 ID 清理。
- 每阶段开始解释目标、任务拆分和依赖；模块交付解释结构与核心逻辑，修复问题说明根因，阶段结束如实汇报。
