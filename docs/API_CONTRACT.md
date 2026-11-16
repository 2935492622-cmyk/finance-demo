# API 契约

版本：0.1，状态：用户已于 2026-11-16 确认，作为前端、后端和 QA 的共同依据。接口路径、字段和行为如需调整，由主 Agent 提出变更和影响，得到用户确认后再更新；子 Agent 不得自行修改。

## 通用约定

- 本地 API 根地址计划为 `http://127.0.0.1:8000/api`；前端通过 Vite 代理调用相对路径 `/api`。
- 请求与响应使用 UTF-8 JSON；DELETE 成功不返回响应体。无鉴权，仅限本地 Demo。
- 类型大小写敏感，仅 `income`、`expense`。
- 所有金额在 JSON 中都是固定两位小数的十进制字符串。单笔金额严格匹配 `^(0|[1-9][0-9]{0,7})\.[0-9]{2}$` 且大于 0。不接受 JSON 数字、前导零、正负号、指数、空格、NaN、Infinity；后端用 Decimal，不经过 float。
- 分类和备注去除首尾空白后校验长度，按 Unicode 字符计数；不做大小写或 Unicode 归一化。拒绝未知请求体字段，所有非可空字段传 `null` 均为 422。
- `transaction_date` 是 `YYYY-MM-DD` 的真实日历日期，范围 `1000-01-01`～`9999-12-31`。它不是 UTC 时间戳。
- `created_at`、`updated_at` 为服务器生成的 UTC ISO 8601 时间，固定格式如 `2026-11-15T12:00:00.000000Z`；前端展示时转换到 Asia/Shanghai。
- `id` 是数据库生成的正整数（INT UNSIGNED），URL 中 ID 超出 `1`～`4294967295` 或不是整数时为 422。无效路径 ID 与合法但不存在的 ID 区分。

## 记录数据结构

### TransactionWrite：POST / PUT 请求体

| 字段 | JSON 类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `amount` | string | 是 | `0.01`～`99999999.99`，固定两位小数 |
| `type` | string | 是 | `income` / `expense` |
| `category` | string | 是 | trim 后 1～50 字符 |
| `note` | string | 否 | 默认 `""`，trim 后最多 500 字符 |
| `transaction_date` | string | 是 | 上述日期格式与范围 |

```json
{
  "amount": "125.50",
  "type": "expense",
  "category": "餐饮",
  "note": "午餐聚会",
  "transaction_date": "2026-11-15"
}
```

### TransactionRead：单条记录响应

包含所有 TransactionWrite 字段，并增加只读字段 `id`、`created_at`、`updated_at`。创建时两个时间相同；编辑不改变 `id` 和 `created_at`，更新 `updated_at`（不得早于旧值）。

```json
{
  "id": 1,
  "amount": "125.50",
  "type": "expense",
  "category": "餐饮",
  "note": "午餐聚会",
  "transaction_date": "2026-11-15",
  "created_at": "2026-11-15T12:00:00.000000Z",
  "updated_at": "2026-11-15T12:00:00.000000Z"
}
```

## 共享筛选参数

GET `/transactions` 和 GET `/summary` 必须共享同一个筛选校验和 SQL 条件构造逻辑。

| 参数 | 类型 | 行为 |
| --- | --- | --- |
| `type` | string，可选 | 按收入 / 支出类型匹配 |
| `category` | string，可选 | trim 后 1～50 字符，大小写和重音敏感的等值匹配，不是模糊搜索 |
| `start_date` | date，可选 | `transaction_date >= start_date`，含当天 |
| `end_date` | date，可选 | `transaction_date <= end_date`，含当天 |

所有条件按 AND 组合；省略参数表示不限制，空字符串不是省略，返回 422。起始日期晚于结束日期返回 422，错误字段为 `query.start_date`。未知查询参数返回 422。前端清空筛选后应完全省略对应参数；中文等参数由 Axios 编码，不手拼 URL。

## 接口清单

| 方法 | 路径（均位于 `/api` 下） | 成功状态 | 结果 |
| --- | --- | --- | --- |
| POST | `/transactions` | 201 | 完成数据库提交后返回 TransactionRead |
| GET | `/transactions` | 200 | 返回符合筛选的全部记录，无分页 |
| GET | `/summary` | 200 | 返回符合筛选的统计和支出分类汇总 |
| PUT | `/transactions/{id}` | 200 | 全量更新可写字段，返回 TransactionRead |
| DELETE | `/transactions/{id}` | 204 | 删除并提交后返回空响应体 |
| GET | `/health` | 200 | 成功执行数据库 `SELECT 1` 后返回健康状态 |

POST、GET 列表、GET 统计为 P0；PUT、DELETE 及筛选 UI、图表为 P1。后端可先完成基本新增 / 查询，再落实其余已约定行为，不能以静态内存数据替代数据库。

### GET /api/transactions

默认不带筛选返回全部记录，固定按 `transaction_date DESC, id DESC` 排序。`total` 是筛选后的数量，等于 `items.length`。无匹配记录为正常成功。

```json
{"items": [], "total": 0}
```

非空时 `items` 中每项为 TransactionRead。无分页参数和默认截断。

### GET /api/summary

```json
{
  "total_income": "1000.00",
  "total_expense": "125.50",
  "balance": "874.50",
  "transaction_count": 2,
  "expense_by_category": [
    {"category": "餐饮", "amount": "125.50"}
  ]
}
```

汇总当前筛选范围内所有记录，`balance = total_income - total_expense`。收入和支出总额非负，结余允许负数。分类汇总只包含支出，按金额降序，同金额按分类升序；分类比较遵循数据库中指定的分类排序规则。分类汇总金额之和等于 `total_expense`。

所有汇总金额仍为固定两位小数字符串，可能超过单笔 `DECIMAL(10,2)` 的上限，不能对汇总套用单笔上限或转 float。空集合返回：

```json
{
  "total_income": "0.00",
  "total_expense": "0.00",
  "balance": "0.00",
  "transaction_count": 0,
  "expense_by_category": []
}
```

列表和统计是独立请求，不保证多客户端并发写入时属于同一数据库快照；本 Demo 每次写入成功后刷新两者，验收时不并发写入。

### PUT /api/transactions/{id}

请求体与 POST 完全相同，是全量更新；缺少必填字段返回 422，省略可选 `note` 表示清空备注，不是局部保留。有效请求的目标 ID 不存在时返回 404。不实现版本冲突检查，多个客户端编辑时最后一次成功提交生效。

### DELETE /api/transactions/{id}

有效 ID 存在时物理删除，仅成功提交后返回 204；前端不得对 204 调用 JSON 解析。目标不存在（包括重复删除）返回 404。删除后统计按剩余记录重新计算。

### GET /api/health

```json
{"status": "ok", "database": "connected"}
```

数据库连接失败或不可用时返回下述 503 错误，不伪报健康。

## 统一错误格式

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "请求参数不合法",
    "details": [
      {"field": "body.amount", "message": "金额必须大于 0，且保留两位小数"}
    ]
  }
}
```

| HTTP 状态 | `error.code` | 场景 |
| --- | --- | --- |
| 422 | `VALIDATION_ERROR` | 请求体、查询参数、日期、ID 不合法，或 JSON 无法解析 |
| 404 | `NOT_FOUND` | 有效请求指向不存在的记录 |
| 503 | `DATABASE_UNAVAILABLE` | 连接、查询或提交阶段数据库不可用 |
| 500 | `INTERNAL_ERROR` | 未预期的内部异常 |

所有错误都有 `code`、中文 `message`、`details` 数组；非字段错误的 `details` 为空数组。字段路径使用 `body.amount`、`query.start_date`、`path.id` 等；请求体整体异常使用 `body`。`message` 为可读提示，测试不绑定 Pydantic 自动生成的整段英文文案。

需自定义 FastAPI 校验和异常响应，不能直接透传默认 422 的 `detail` 格式、异常上下文、原始输入、SQL、连接串或密码。写操作异常必须回滚，失败不得残留部分写入。

## 前端对接示例与边界

```text
POST   /api/transactions
GET    /api/transactions?type=expense&start_date=2026-11-01&end_date=2026-11-30
GET    /api/summary?type=expense&start_date=2026-11-01&end_date=2026-11-30
PUT    /api/transactions/1
DELETE /api/transactions/1
```

Axios 封装统一处理上述错误。金额展示使用原始十进制文本；只有 ECharts 的可视化数值允许转 Number，不能以图表浮点结果更新账目或统计卡片。网络超时不能证明写入失败，不自动重试 POST；先提示结果未确认并引导刷新核对。
