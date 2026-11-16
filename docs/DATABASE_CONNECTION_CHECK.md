# MySQL 连接配置检查

日期：2026-11-16（Asia/Shanghai）。本次工作是连接配置与初始化，不是完整记账业务验收。

## 检查与配置结果

- 用户已部署 `mysql8`，版本为 MySQL 8.4.13，状态 healthy。
- 端口仅映射到 `127.0.0.1:3306`，数据挂载为命名卷 `mysql8_data`，路径 `/var/lib/mysql`。
- 已有 `devuser` 可以登录，但没有 `finance_demo` 授权；管理员只读检查确认项目库、表及 `finance_demo_app` 账号均未存在。
- 按已确认的 `database/schema.sql` 初始化了 `finance_demo.transactions`，没有覆盖既有库、表或账号密码。
- 新建专用账号 `finance_demo_app`，仅授予 `finance_demo.*` 的 SELECT、INSERT、UPDATE、DELETE；没有全局管理权限。
- 为专用账号生成随机密码，仅保存到 `backend/.env`，没有显示到聊天或写入文档、命令参数、Git。
- `backend/.env` 权限为 `0600`，已验证 Git 忽略。用户当前不需要手动填写连接字段。

## 实际验证

使用专用账号直连成功，版本、权限、严格 SQL 模式与表存在检查通过。初始 `transactions` 为 0 条。

重启本项目后端重新读取 `.env` 后：

| 地址 | 结果 |
| --- | --- |
| `http://127.0.0.1:8000/api/health` | 200，database=connected |
| `http://127.0.0.1:8000/api/transactions` | 200，items=[]，total=0 |
| `http://127.0.0.1:8000/api/summary` | 200，收入 / 支出 / 结余均为 `0.00`，记录数 0 |
| `http://127.0.0.1:5173/api/health` | 200，前端代理连接正常 |

本次没有新增或删除收支记录，也未运行真实写入测试套件。此前的 39 项 MySQL 用例仍待正式执行；页面新增、SQL 对照、非零统计和刷新持久化还不能标记为通过。

共享容器、命名卷和已有 `devuser` 保留，未重启或重建 MySQL。后续修改 `.env` 必须重启本项目后端；不需要重启共享数据库。
