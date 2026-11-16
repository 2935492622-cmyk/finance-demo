# QA 详细用例与执行边界

基线：API_CONTRACT 0.1，2026-11-16已确认。P0/P1已完成真实独立验收，实际结果见TEST_REPORT和P1_TEST_REPORT；本文件保留最初P0用例基线。

## P0 自动化映射

| 契约 / 计划项 | 可执行用例 | 证据来源 |
| --- | --- | --- |
| API-01、SUM-01、API-10、持久化基础 | `test_create_sql_summary_and_reconnect` | 真实 HTTP 响应、直接 SQL、重新建立 HTTP 客户端 |
| API-02 | `test_valid_amount_boundaries` | API 金额字符串与 MySQL Decimal 对比 |
| API-03 / 04 | `test_invalid_amount_does_not_write` | 422 字段定位及唯一测试分类内 SQL 空集合 |
| API-05 | `test_invalid_type_does_not_write` | 422 与无写入 |
| API-06 / 07 | `test_unicode_lengths_trim_and_optional_note` | Unicode 长度、首尾空白、备注省略、SQL 对照 |
| API-08 | `test_unknown_missing_readonly_and_broken_json` | 必填、未知只读字段及非法 JSON 的统一错误 |
| API-09 | `test_invalid_date_does_not_write` | 无效日历日期、年份下限、时间戳拒绝 |
| SUM-02 | `test_empty_summary` | 独立随机分类，无需清用户数据 |
| SUM-03 / 04 | Decimal、负结余、超单笔上限聚合用例 | 真实 summary 字符串与精确预期 |
| FILTER-01 / 02 | 组合条件、类型、日期含边界、未知参数用例 | 同参数 list 与 summary 对照 |

全部真实集成测试需要明确设置 `FINANCE_QA_INTEGRATION=1`，且只允许 `finance_demo`。详细命令见 `tests/README.md`。

## 仍需独立手工 / 浏览器验证

1. 实际页面新增收入 `1000.00` 和支出 `125.50`，捕获返回 ID，SQL 对照，统计相对基线正确。
2. 刷新页面以及重启本项目后端后记录与统计仍存在；不能把 HTTP 客户端重连当作此项证据。
3. 用户输入 `12`、`12.3` 正确补零，超过两位小数拒绝；输入错误在页面可见。
4. 连续点击只提交一次；提交失败保留表单；网络结果不确定不自动重试。
5. 数据库503显示失败，不显示保存成功；保存成功但重查失败时区分两类结果。
6. 桌面与窄屏布局、键盘可达性、类型文字标识、加载和空态。
7. 列表与卡片刷新协调，过期响应不能覆盖新状态。

## P1用例（已由主Agent后续安排并完成）

编辑全量替换、备注省略清空、created_at保留、updated_at不倒退、取消编辑；删除取消不发请求、确认删除204空体、重复删除404；非法/不存在ID；筛选UI清空/组合/快速切换；分类大小写和引号文本；图表分类金额与总支出一致。详见P1_TEST_CASES和P1_TEST_REPORT；不以原先P1未开始时的状态作为当前结果。

## SQL 证据模板

仅查询已知测试 ID，实际执行时使用参数化查询；不要把占位符直接粘贴为 SQL 数字。

```sql
SELECT id, amount, type, category, note, transaction_date, created_at, updated_at
FROM finance_demo.transactions
WHERE id IN (<本轮收入ID>, <本轮支出ID>)
ORDER BY id;
```

报告记录运行标记、两条 ID、预期和实际金额、SQL 返回值、API 状态、页面截图相对路径。记录统计基线与增量，不输出其他用户完整备注或凭据。不保存真实 `.env` 或含密码命令。

## 环境观察

2026-11-16 初始检查：`mysql8`、`backend/.env` 和 3306/8000/5173 监听缺失。缓存浏览器二进制存在但缺少 libnspr4 / libnss3 / libnssutil3 / libsmime3 / libasound 运行库，`--version` 退出127；未安装或改动任何全局依赖。后续环境变化需重新记录。

2026-11-16 后续：主 Agent 已启动前后端，并在项目内准备浏览器运行库；QA 实际浏览器503冒烟通过。MySQL和.env仍未就绪，详见 TEST_REPORT；初始浏览器环境阻碍已解除。

2026-11-16 MySQL就绪后：39项真实集成通过，独立套件联合63 passed；页面新增ID27/28、SQL Decimal、统计、刷新和8000后端重启后持久化均通过。成功截图发现窄屏可读性缺陷，按主Agent分派前端修复后，QA增强金额单行和备注行数检查，复测通过。最新使用after-restart截图；两笔演示数据暂保留，P1待安排。
