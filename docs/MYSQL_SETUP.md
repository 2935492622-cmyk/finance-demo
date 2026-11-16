# 用户部署 MySQL 后的准备清单

当前项目不会自行部署共享服务。由用户准备 `mysql8`（MySQL 8.0.16+ 的 8.x 版本）、Docker 命名卷和本机可达端口；首次创建的容器示例见根 README。已有容器、卷及其他项目数据库全部保留。

## 1. 检查服务并初始化本库

```bash
docker ps -a --filter name='^/mysql8$'
docker exec -it mysql8 mysql -u root -p
```

在 MySQL 交互会话中检查版本和严格模式：

```sql
SELECT VERSION(), @@SESSION.sql_mode;
SHOW DATABASES LIKE 'finance_demo';
```

严格模式应包含 `STRICT_TRANS_TABLES` 或 `STRICT_ALL_TABLES`。若已有数据库及表，先查看原结构，不删表、不清数据。确认后在会话中执行项目 `database/schema.sql` 的完整内容；该文件只有本库的初始化语句，不会更新已有同名表的结构。

## 2. 为应用准备专用账号

以下 SQL 仅为首次创建账号的模板；将密码占位符替换为本地设置的实际密码。若账号已存在，先核对归属与权限，不直接覆盖密码或修改其他项目账号。

```sql
CREATE USER 'finance_demo_app'@'%' IDENTIFIED BY '<在本地设置的密码>';
GRANT SELECT, INSERT, UPDATE, DELETE ON finance_demo.* TO 'finance_demo_app'@'%';
SHOW CREATE TABLE finance_demo.transactions;
```

应用不需要 root 或建库 / 删表权限。数据库端口保持本机访问范围；容器网络中的账号匹配需与实际连接来源一致。

## 3. 填写本地配置

若尚无真实配置，在项目根目录复制一次模板；已有 `.env` 不重复覆盖：

```bash
cp -n backend/.env.example backend/.env
```

在 VS Code 打开 `backend/.env`，填入本机实际端口、账号、密码；`DB_NAME` 固定 `finance_demo`。这个文件已被 Git 忽略。密码不必发送到聊天，连接验证也不会打印密码。

## 4. 通知主 Agent 继续真实验证

准备好后回复“数据库已就绪，已填写 backend/.env”即可。主 Agent 将先只读检查连接、表结构和现有数据基线，再协调 QA 创建带唯一标记的少量测试记录，完成页面新增、SQL 查询、统计与刷新验证。

部署完成不等于测试通过；真实执行结果会单独写入 QA 报告。清理项目时不删除 `mysql8` 或命名卷，也不停止共享数据库服务。
