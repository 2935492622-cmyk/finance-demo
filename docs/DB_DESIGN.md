# MySQL 数据库设计

版本：0.1，状态：用户已于 2026-11-16 确认。建表脚本已在用户部署的 MySQL 8.4.13 上执行；P0 真实写入、SQL 对照、精确汇总、页面刷新及后端重启持久化通过。P1 仍使用同一张表，不需要修改结构。

## 服务与数据库边界

- 由用户部署长期共享 MySQL 8，容器名 `mysql8`，Docker 命名卷保存 `/var/lib/mysql`，不得映射到项目目录。
- 使用 MySQL 8.0.16 或更新的 8.x 版本，以执行 CHECK 约束；[MySQL 官方文档](https://dev.mysql.com/doc/refman/8.0/en/create-table-check-constraints.html)说明了该版本边界。
- 本项目仅使用 `finance_demo` 数据库，不创建其他项目的库，不重建现有服务，不修改服务器全局配置。
- MySQL 会话使用 UTC、utf8mb4 和严格 SQL 模式；后端每次建立物理连接时设置会话时区并检查严格模式，不能通过关闭严格模式掩盖非法数据。
- 管理账号执行建库建表；应用专用账号只需 `finance_demo.*` 的 SELECT、INSERT、UPDATE、DELETE 权限。不把密码写入 SQL 文件。

## 表：transactions

| 字段 | MySQL 类型 | 约束 / 用途 |
| --- | --- | --- |
| `id` | INT UNSIGNED | 自增主键；JSON 数字仍在 JavaScript 安全整数范围内 |
| `amount` | DECIMAL(10,2) | NOT NULL，CHECK > 0，单笔最多 `99999999.99` |
| `type` | VARCHAR(7)，ascii_bin | NOT NULL，CHECK 为 `income` / `expense`；按大小写区分 |
| `category` | VARCHAR(50)，utf8mb4_0900_as_cs | NOT NULL，非空、无首尾空格；分类筛选和分组大小写 / 重音敏感 |
| `note` | VARCHAR(500) | NOT NULL，默认空字符串 |
| `transaction_date` | DATE | NOT NULL，用户选择的记账日期；API 拒绝非法日期和小于 1000 年的日期 |
| `created_at` | DATETIME(6) | NOT NULL，UTC 创建时间 |
| `updated_at` | DATETIME(6) | NOT NULL，UTC 更新时间 |

不存储独立的余额或统计表，每次从实际记录按条件汇总，避免新增、编辑、删除后汇总值失效。分类先存为文本，推荐分类由前端提供；本版本不建分类表、用户表或外键。

MySQL CHECK 的 TRIM 只补充拦截普通空格；所有 Unicode 首尾空白均由后端先规范化。数据库约束是最后一道保障，不能代替 API 校验，尤其是多余小数位、非法日期和字段长度；连接需检查 `STRICT_TRANS_TABLES` 或 `STRICT_ALL_TABLES`。

## 索引与查询

| 索引 | 字段 | 用途 |
| --- | --- | --- |
| PRIMARY | id | 按 ID 编辑、删除 |
| idx_transactions_date_id | transaction_date, id | 全部记录及日期范围排序 |
| idx_transactions_type_date | type, transaction_date | 类型及日期筛选 |
| idx_transactions_category_date | category, transaction_date | 分类及日期筛选 |

固定排序为 `transaction_date DESC, id DESC`，无分页截断。多条件 AND 组合由 SQLAlchemy 构造参数化查询；不拼接用户 SQL。

## 金额、统计与时间

SQLAlchemy 模型使用 `Numeric(10, 2, asdecimal=True)`，Pydantic 校验前要求金额为契约指定字符串，然后转换为 Python Decimal；序列化时固定两位小数。查询 `SUM` 的结果保持 Decimal，空结果显式转为 Decimal 零。统计总额允许超出单笔字段范围。

收入、支出分别按 type 汇总，结余为两者之差。支出分类汇总使用同一个筛选条件，再限制 type 为 expense；若筛选 type=income，支出分类汇总自然为空。

`transaction_date` 表示本地账本日期，不进行时区换算。创建 / 更新时间由后端生成 UTC 时间，存为无时区的 DATETIME(6)，响应时显式附加 UTC 并输出 `Z`；数据库默认值作为补充，依赖 UTC 会话。模型需要为编辑设置 UTC 的 updated_at，与 SQL 脚本的 ON UPDATE 行为保持一致。

## 初始化与模型一致性

[schema.sql](../database/schema.sql)只包含本库的首次创建语句、会话设置和一张表，不含 DROP、TRUNCATE、测试数据、账号密码或重置操作。

MySQL 就绪后，管理账号先检查版本、`@@sql_mode`、已有 `finance_demo` 和表结构，再执行脚本。当前示例导入命令（会交互要求密码，不需要在命令行填密码）：

```bash
docker exec -it mysql8 mysql -u root -p
```

在 VS Code 打开 `database/schema.sql`，将完整脚本粘贴到上述 MySQL 交互客户端执行；也可在已配置的数据库客户端直接执行该文件。SQL 文件保留在项目目录，无需在共享容器内复制项目文件。已有同名表时 `IF NOT EXISTS` 不会更新结构，必须 `SHOW CREATE TABLE finance_demo.transactions` 对比；不一致交由主 Agent 决策迁移，不能删表重建。ORM 不得在启动时自动 drop/create 或悄悄用 `create_all` 代替明确初始化。

后端 Agent 落实模型、连接及会话设置，主 Agent 维护 SQL 设计，双方交付时比较字段、约束、索引和默认值。只有真实 MySQL 执行后才能宣称脚本验证通过；SQLite 不作为 MySQL 兼容性或持久化验收证据。

## 数据验证与测试清理

联调需要查询对应 ID 的字段、精确金额和汇总，保存脱敏证据到测试报告。用户数据不清空，测试记录使用独立备注前缀并记录 ID，只按明确的测试 ID 清理。不得创建 `finance_demo_test` 等额外数据库；真实集成测试在用户已准备的 `finance_demo` 中进行隔离，QA 执行前说明数据影响。

删除 `finance-demo/` 只清理代码、依赖和配置，`mysql8`、命名卷及其中数据库继续保留。
