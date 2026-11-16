# P1独立QA执行报告

日期：2026-11-16（Asia/Shanghai）。结论：**P1真实API、页面编辑/删除/筛选、ECharts与窄屏验收通过，无未关闭业务缺陷。** P0历史及重启持久化证据继续保留，不与模拟测试混算。

## API与回归

| 实际命令 | 结果 | 覆盖 |
| --- | --- | --- |
| `FINANCE_QA_INTEGRATION=1 .venv/bin/python -m pytest tests/test_p1_mysql_api.py -q -rs` | 24 passed in 1.76s | 真实PUT/DELETE、SQL、非法输入、404/422、分类与组合筛选 |
| `FINANCE_QA_INTEGRATION=1 .venv/bin/python -m pytest tests -q -rs` | **87 passed in 4.80s，0 skipped** | 24离线/失败路径 + 39项P0真实API + 24项P1真实API |

P1实际验证：PUT替换金额/类型/分类/备注/日期，created_at和ID不变，updated_at不倒退，省略note清空；10组非法PUT保持SQL原记录不变；DELETE204空体、重复404；8组非法/越界ID返回path.id的422；合法不存在ID为404；分类大小写/重音/引号精确匹配；日期端点和AND条件、分类金额汇总一致。

额外按主Agent要求，只对自己新建的测试记录用SQL将updated_at设为2099年，真实PUT后仍不倒退，并清理该测试ID。没有调整系统时钟或用户记录。

所有测试仅在finance_demo操作自己登记的ID。PUT成功后跟踪最新分类/备注，清理采用ID+分类+备注条件，不使用全表清理。后端开发者106项与前端26项模块测试由开发者/主Agent分别报告，本报告不假称为QA独立执行。

## 真实页面、图表与SQL

前后端稳定且主Agent确认加载P1后，实际运行：

```bash
FINANCE_QA_BROWSER_EXECUTABLE=/home/ava/.cache/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-linux64/chrome-headless-shell \
FINANCE_QA_BROWSER_LIBRARY_PATH="$PWD/.tools/browser-runtime/root/usr/lib/x86_64-linux-gnu" \
TMPDIR="$PWD/.tools/browser-runtime/tmp" \
node tests/browser_p1_acceptance.mjs
```

首轮11:32:11～11:32:17通过7组检查，历史结果：[browser-p1-first-result.json](browser-p1-first-result.json)。主Agent审查后将QA工具的保护基线改为本次实际初始记录快照，移除固定ID和“恰好两条”假设，恢复环境后完整复跑。

**最新动态基线运行11:37:22～11:37:28，7组检查通过**，原始证据：[browser-p1-result.json](browser-p1-result.json)。无请求拦截、伪造201或伪造统计。

1. 真正通过页面表单创建4条唯一标记测试记录（最新ID105～108），不是程序HTTP新增替代页面。基线中的所有既有记录受保护，本轮自然包含演示ID27/28。
2. 类型+分类+日期组合筛选含日期两端；页面列表、三项金额、真实summary和ECharts数据一致。非法日期范围只显示本地错误，不发请求；收入筛选和空集合有图表空态；清空恢复全部。
3. 同一事件轮立即应用两个真实筛选请求，最终只显示最后分类的完整列表/summary/图表快照。
4. 编辑完整回填；修改后取消没有PUT且数据不变。真实页面PUT更改全部可写字段，created_at/ID不变，updated_at不倒退；刷新及直接SQL读回一致。
5. 删除取消没有DELETE；真实确认删除ID108返回204且没有内容长度，SQL确认不存在、列表/统计/图表更新。原始API套件另直接验证响应体为空字节。
6. 直接读取页面正在使用的ECharts实例getOption和可访问图例，分类与exactAmount逐项等于真实summary。检查SVG实际宽高及可见path尺寸，排除仅DOM存在但图标CSS把图压成20px的情况。
7. 390px和320px调整后图表实际resize；金额行数均为[1,1,1]，文档无横向溢出，700px表格仅在内部滚动。无未捕获页面JS异常。

320px实测SVG252×210px，最大可见path约163.8×163.7px；390px图表宽308px。SVG压缩问题来自前端开发者自查，QA是在其修复后独立验证，没有虚构先前QA端到端失败。

## 数据清理与截图

最新运行ID105在页面编辑，108在页面删除；finally只按最新期望分类/备注精确清理105、106、107。SQL复核初始基线记录全字段未变，原演示27/28仍保留。首轮101～104也已安全清理，没有测试脏数据残留。

验收过程截图中包含当时真实存在的QA记录；这些临时记录随后清理，截图不是当前最终账本数据。已实际查看桌面、移动及编辑/筛选截图：

- [真实组合筛选](../../screenshots/p1-filtered.png)
- [仅收入图表空态](../../screenshots/p1-empty-chart.png)
- [编辑取消前状态](../../screenshots/p1-editing.png)
- [多分类桌面](../../screenshots/p1-desktop.png)
- [390px验收](../../screenshots/p1-mobile390.png)、[320px验收](../../screenshots/p1-mobile320.png)

清理后另行确认health200、summary200，只读新页面拍摄最终截图，0次写入；真实账本仍为1000.00收入、125.50支出、874.50结余、2笔：

- **[最终桌面](../../screenshots/p1-final-desktop.png)**
- **[最终390px移动端](../../screenshots/p1-final-mobile390.png)**
- [最终320px移动端](../../screenshots/p1-final-mobile320.png)
- [最终截图脱敏证据](final-screenshots.json)

## 过程修正与限制

- QA工具首次把保护记录固定为27/28、要求两条，主Agent审查指出不适合新环境。现改为实际初始快照，自己的ID不得与基线相交，清理不依赖初始数量。已完整复跑通过，属于QA工具改进，不称业务Bug。
- 首轮P1完成后额外只读截图遇到图表等待超时。主Agent确认8000旧进程收到SIGTERM并优雅退出143，无应用异常trace；原因未知。QA调试页无JS异常，正确显示统计未同步。主Agent恢复后端后先确认health/summary再完整复跑，通过。没有操作共享MySQL，也不将环境中断误报为图表业务缺陷。
- 真实“数据库已提交但响应回执丢失”故障注入尚未执行；原先安全提交锁有独立单元与真实503路径证据。不影响已完成的正常CRUD、精度和持久化结论。
- 本轮P1编辑在浏览器刷新和SQL后保持；后端重启持久化的独立实测由P0页面创建记录完成，详情见总报告，不声称P1每一种操作均再次重启验证。

当前独立QA可放行P0/P1，最终交付仍由主Agent复核和联合回归确认。
