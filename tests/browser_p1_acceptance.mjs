// Actual local P1 UI, MySQL-backed chart/filters/edit/delete. Never fakes responses.
import assert from 'node:assert/strict'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { spawnSync } from 'node:child_process'
import { randomUUID } from 'node:crypto'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from '../frontend/node_modules/playwright/index.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const statePath = path.join(root, 'tests/.p1-demo-state.json')
const resultPath = path.join(root, 'docs/qa/browser-p1-result.json')
const frontend = process.env.FINANCE_QA_FRONTEND_URL || 'http://127.0.0.1:5173'
assert(['127.0.0.1', 'localhost', '[::1]'].includes(new URL(frontend).hostname))
assert(process.env.FINANCE_QA_BROWSER_EXECUTABLE, 'Set the existing local browser executable')
const env = { ...process.env }
if (process.env.FINANCE_QA_BROWSER_LIBRARY_PATH) {
  env.LD_LIBRARY_PATH = [process.env.FINANCE_QA_BROWSER_LIBRARY_PATH, env.LD_LIBRARY_PATH].filter(Boolean).join(':')
}
await mkdir(path.join(root, 'screenshots'), { recursive: true })
const previous = await readFile(statePath, 'utf8').catch((error) => {
  if (error.code === 'ENOENT') return null
  throw error
})
if (previous) assert.equal(JSON.parse(previous).phase, 'cleaned', 'Previous P1 run did not finish cleanup; inspect its known IDs before rerunning')
const marker = `qa-p1-${randomUUID().slice(0, 8)}`
const state = { run_marker: marker, phase: 'running', created_records: [], protected_records: [], baseline_captured: false }
const evidence = { scenario: 'Real page P1 edit/delete/filter/ECharts acceptance', run_marker: marker,
  started_at: new Date().toISOString(), checks: [], screenshots: [] }
async function saveState() { await writeFile(statePath, `${JSON.stringify(state, null, 2)}\n`, { mode: 0o600 }) }
function sqlCheck(cleanup = false) {
  const result = spawnSync(path.join(root, '.venv/bin/python'), [path.join(root, 'tests/sql_p1_evidence.py'), ...(cleanup ? ['--cleanup'] : [])],
    { cwd: root, encoding: 'utf8', timeout: 15000 })
  assert.equal(result.status, 0, result.stderr || 'P1 SQL evidence failed')
  return JSON.parse(result.stdout)
}
function formatted(value) { return value.replace(/\B(?=(\d{3})+(?!\d))/g, ',') }
const browser = await chromium.launch({ executablePath: process.env.FINANCE_QA_BROWSER_EXECUTABLE, env, headless: true })
let page
let failed
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1080 }, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' })
  page = await context.newPage()
  const runtimeErrors = []
  const writes = []
  const reads = []
  page.on('pageerror', (error) => runtimeErrors.push(error.message))
  page.on('request', (request) => {
    const url = new URL(request.url())
    if (!url.pathname.startsWith('/api/')) return
    if (request.method() === 'GET') reads.push({ path: url.pathname, query: Object.fromEntries(url.searchParams) })
    else writes.push({ method: request.method(), path: url.pathname })
  })
  assert.equal((await page.request.get(`${frontend}/api/health`)).status(), 200)
  const initial = await (await page.request.get(`${frontend}/api/transactions`)).json()
  state.protected_records = initial.items
  state.baseline_captured = true
  state.baseline_count = initial.total
  await saveState()
  assert.equal((await page.goto(frontend, { waitUntil: 'networkidle' })).status(), 200)
  await page.getByRole('heading', { name: '筛选记录', exact: true }).waitFor()

  async function syncDone() {
    await page.waitForFunction(() => !document.querySelector('.summary-grid').getAttribute('aria-busy') || document.querySelector('.summary-grid').getAttribute('aria-busy') === 'false')
  }
  async function screenshot(name) {
    const relative = `screenshots/${name}`
    await page.evaluate(() => window.scrollTo({ top: 0, left: 0, behavior: 'instant' }))
    await page.screenshot({ path: path.join(root, relative), fullPage: true })
    evidence.screenshots.push(relative)
  }
  async function getRecords(params = {}) {
    const response = await page.request.get(`${frontend}/api/transactions`, { params })
    assert.equal(response.status(), 200)
    return response.json()
  }
  async function assertChartAndCards(params = {}) {
    await syncDone()
    const summaryResponse = await page.request.get(`${frontend}/api/summary`, { params })
    assert.equal(summaryResponse.status(), 200)
    const summary = await summaryResponse.json()
    const cards = await page.locator('.summary-amount').allTextContents()
    for (const [index, key] of ['total_income', 'total_expense', 'balance'].entries()) {
      assert.equal(cards[index].replace(/[¥\s]/g, ''), formatted(summary[key]))
    }
    const listed = await getRecords(params)
    assert.equal(listed.total, summary.transaction_count)
    assert.equal(await page.locator('table tbody tr').count(), listed.total)
    if (!summary.expense_by_category.length) {
      await page.locator('.chart-empty').filter({ hasText: '暂无支出' }).waitFor()
      assert.equal(await page.locator('.expense-chart').count(), 0)
    } else {
      await page.locator('.expense-chart svg').waitFor()
      const chart = await page.evaluate(async () => {
        const moduleUrl = performance.getEntriesByType('resource').map((entry) => entry.name).find((name) => name.includes('/echarts_core.js'))
        if (!moduleUrl) throw new Error('Loaded ECharts core module not found')
        const { getInstanceByDom } = await import(moduleUrl)
        const container = document.querySelector('.expense-chart')
        const instance = getInstanceByDom(container)
        const svgRect = container.querySelector('svg').getBoundingClientRect()
        const paths = [...container.querySelectorAll('svg path')].map((element) => element.getBoundingClientRect())
        return { data: instance.getOption().series[0].data.map((item) => ({ category: item.name, amount: item.exactAmount })),
          width: instance.getWidth(), height: instance.getHeight(), containerWidth: container.clientWidth,
          svgWidth: svgRect.width, svgHeight: svgRect.height,
          largestPathWidth: Math.max(0, ...paths.map((rect) => rect.width)),
          largestPathHeight: Math.max(0, ...paths.map((rect) => rect.height)) }
      })
      assert.deepEqual(chart.data, summary.expense_by_category)
      assert(chart.width > 0 && chart.height > 0 && Math.abs(chart.width - chart.containerWidth) <= 2)
      assert(Math.abs(chart.svgWidth - chart.containerWidth) <= 2 && chart.svgHeight > 50, 'Actual chart SVG must not be compressed by icon CSS')
      assert(chart.largestPathWidth > 20 && chart.largestPathHeight > 20, 'Visible pie paths must have meaningful drawing dimensions')
      const legend = await page.locator('.chart-legend li').evaluateAll((items) => items.map((item) => ({
        category: item.querySelector('.chart-category').textContent, amount: item.querySelector('strong').textContent.replace(/¥|,/g, ''),
      })))
      assert.deepEqual(legend, summary.expense_by_category)
      evidence.last_chart = { ...chart, groups: chart.data.length }
    }
    return { summary, listed }
  }
  async function filter(params) {
    await page.locator('#filter-type').selectOption(params.type || '')
    await page.locator('#filter-category').fill(params.category || '')
    await page.locator('#filter-start').fill(params.start_date || '')
    await page.locator('#filter-end').fill(params.end_date || '')
    const expectedList = page.waitForResponse((response) => response.request().method() === 'GET' && new URL(response.url()).pathname === '/api/transactions')
    await page.getByRole('button', { name: '应用筛选', exact: true }).click()
    assert.equal((await expectedList).status(), 200)
    await syncDone()
    const pair = reads.filter((item) => ['/api/transactions', '/api/summary'].includes(item.path)).slice(-2)
    assert.equal(pair.length, 2)
    for (const item of pair) assert.deepEqual(item.query, params)
    return assertChartAndCards(params)
  }
  async function clear() {
    const result = page.waitForResponse((response) => response.request().method() === 'GET' && new URL(response.url()).pathname === '/api/summary')
    await page.getByRole('button', { name: '清空筛选', exact: true }).click()
    assert.equal((await result).status(), 200)
    await syncDone()
    for (const selector of ['#filter-category', '#filter-start', '#filter-end']) assert.equal(await page.locator(selector).inputValue(), '')
    return assertChartAndCards()
  }

  const categoryA = `${marker}-餐饮`
  const categoryB = `${marker}-交通`
  for (const [amount, type, category, day, suffix] of [
    ['20.00', 'expense', categoryA, '2040-01-01', 'a'],
    ['30.00', 'expense', categoryB, '2040-01-02', 'b'],
    ['100.00', 'income', categoryA, '2040-01-02', 'c'],
    ['4.50', 'expense', categoryA, '2040-01-03', 'd'],
  ]) {
    await page.getByRole('button', { name: type === 'income' ? '收入' : '支出', exact: true }).click()
    await page.locator('#amount').fill(amount)
    await page.locator('#category').fill(category)
    await page.locator('#transaction-date').fill(day)
    await page.locator('#note').fill(`${marker}-${suffix}`)
    const result = page.waitForResponse((response) => response.request().method() === 'POST' && new URL(response.url()).pathname === '/api/transactions')
    await page.getByRole('button', { name: '保存这一笔', exact: true }).click()
    const response = await result
    assert.equal(response.status(), 201)
    const record = await response.json()
    assert(!state.protected_records.some((item) => item.id === record.id), 'New QA ID must not belong to the initial user-data baseline')
    assert(!state.created_records.some((item) => item.id === record.id), 'Each page create must return a new ID')
    state.created_records.push(record)
    await saveState()
    await page.getByText(record.note, { exact: true }).waitFor()
    await page.waitForFunction(() => document.querySelector('#amount').value === '' && !document.querySelector('.save-button').disabled)
  }
  evidence.checks.push('Four actual page-created records with independent IDs; P0 demo IDs excluded')
  assert.equal((await assertChartAndCards()).listed.total, state.baseline_count + 4)

  const filtered = await filter({ type: 'expense', category: categoryA, start_date: '2040-01-01', end_date: '2040-01-03' })
  assert.equal(filtered.listed.total, 2)
  assert.equal(filtered.summary.total_expense, '24.50')
  await screenshot('p1-filtered.png')
  const incomeOnly = await filter({ type: 'income', category: categoryA })
  assert.equal(incomeOnly.summary.total_income, '100.00')
  await screenshot('p1-empty-chart.png')
  const empty = await filter({ category: `${marker}-missing` })
  assert.equal(empty.listed.total, 0)
  await page.getByRole('heading', { name: '没有符合条件的记录', exact: true }).waitFor()
  const readsBeforeInvalid = reads.length
  await page.locator('#filter-start').fill('2040-01-03')
  await page.locator('#filter-end').fill('2040-01-01')
  await page.getByRole('button', { name: '应用筛选', exact: true }).click()
  await page.locator('.filter-form .field-error').waitFor()
  assert.equal(reads.length, readsBeforeInvalid)
  await clear()
  evidence.checks.push('Combined exact filters include date endpoints; list/summary/chart match; income/empty chart states; invalid range stays local; clear restores all')

  const latestRapid = page.waitForResponse((response) => {
    const url = new URL(response.url())
    return response.request().method() === 'GET' && url.pathname === '/api/summary' && url.searchParams.get('category') === categoryB
  })
  await page.evaluate(({ first, last }) => {
    const input = document.querySelector('#filter-category')
    const form = document.querySelector('.filter-form')
    input.value = first; input.dispatchEvent(new Event('input', { bubbles: true })); form.requestSubmit()
    input.value = last; input.dispatchEvent(new Event('input', { bubbles: true })); form.requestSubmit()
  }, { first: categoryA, last: categoryB })
  assert.equal((await latestRapid).status(), 200)
  const rapidResult = await assertChartAndCards({ category: categoryB })
  assert.equal(rapidResult.listed.total, 1)
  assert.equal(rapidResult.listed.items[0].id, state.created_records[1].id)
  await clear()
  evidence.checks.push('Two immediate real filter submissions leave only the latest category/list/summary/chart snapshot')

  const cancelTarget = state.created_records[1]
  const putsBeforeCancel = writes.filter((item) => item.method === 'PUT').length
  await page.getByRole('button', { name: `编辑第 ${cancelTarget.id} 笔记录`, exact: true }).click()
  assert.equal(await page.locator('#amount').inputValue(), cancelTarget.amount)
  assert.equal(await page.locator('#category').inputValue(), cancelTarget.category)
  assert.equal(await page.locator('#note').inputValue(), cancelTarget.note)
  await page.locator('#amount').fill('999.00')
  await screenshot('p1-editing.png')
  await page.getByRole('button', { name: '取消编辑', exact: true }).click()
  assert.equal(writes.filter((item) => item.method === 'PUT').length, putsBeforeCancel)
  assert.deepEqual((await getRecords()).items.find((item) => item.id === cancelTarget.id), cancelTarget)

  const editTarget = state.created_records[0]
  await page.getByRole('button', { name: `编辑第 ${editTarget.id} 笔记录`, exact: true }).click()
  await page.getByRole('button', { name: '收入', exact: true }).click()
  await page.locator('#amount').fill('22.75')
  await page.locator('#category').fill(`${categoryA}-edited`)
  await page.locator('#transaction-date').fill('2040-01-04')
  await page.locator('#note').fill(`${marker}-edited`)
  const editedResponse = page.waitForResponse((response) => response.request().method() === 'PUT' && new URL(response.url()).pathname === `/api/transactions/${editTarget.id}`)
  await page.getByRole('button', { name: '保存修改', exact: true }).click()
  const edited = await editedResponse
  assert.equal(edited.status(), 200)
  const updated = await edited.json()
  assert.equal(updated.id, editTarget.id)
  assert.equal(updated.created_at, editTarget.created_at)
  assert(updated.updated_at >= editTarget.updated_at)
  state.created_records[0] = updated
  await saveState()
  await page.getByText(updated.note, { exact: true }).waitFor()
  await page.reload({ waitUntil: 'networkidle' })
  await page.getByText(updated.note, { exact: true }).waitFor()
  evidence.sql_after_edit = sqlCheck()
  evidence.checks.push('Edit prefill/cancel sends no PUT; full page PUT changes fields and survives reload; SQL and readonly identity/time match')

  const deleteTarget = state.created_records[3]
  const deletesBeforeCancel = writes.filter((item) => item.method === 'DELETE').length
  await page.getByRole('button', { name: `删除第 ${deleteTarget.id} 笔记录`, exact: true }).click()
  await page.getByRole('dialog').getByRole('button', { name: '取消', exact: true }).click()
  assert.equal(writes.filter((item) => item.method === 'DELETE').length, deletesBeforeCancel)
  assert((await getRecords()).items.some((item) => item.id === deleteTarget.id))
  await page.getByRole('button', { name: `删除第 ${deleteTarget.id} 笔记录`, exact: true }).click()
  const deletion = page.waitForResponse((response) => response.request().method() === 'DELETE' && new URL(response.url()).pathname === `/api/transactions/${deleteTarget.id}`)
  await page.getByRole('dialog').getByRole('button', { name: '确认删除', exact: true }).click()
  const deleted = await deletion
  assert.equal(deleted.status(), 204)
  assert([null, '0'].includes(await deleted.headerValue('content-length')))
  state.created_records[3] = { ...deleteTarget, deleted: true }
  await saveState()
  await page.getByRole('dialog').waitFor({ state: 'hidden' })
  const afterDelete = await assertChartAndCards()
  assert.equal(afterDelete.listed.total, state.baseline_count + 3)
  evidence.sql_after_delete = sqlCheck()
  evidence.checks.push('Delete cancel sends no request; confirmed page DELETE=204 empty; SQL absence and summary/chart update')
  await screenshot('p1-desktop.png')

  evidence.mobile = []
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 })
    await page.waitForFunction(() => {
      const container = document.querySelector('.expense-chart')
      const svg = container?.querySelector('svg')
      return svg && Math.abs(Number(svg.getAttribute('width')) - container.clientWidth) <= 2
    })
    await assertChartAndCards()
    const metrics = await page.evaluate(() => ({
      overflow: document.documentElement.scrollWidth > window.innerWidth,
      moneyLines: [...document.querySelectorAll('.summary-amount')].map((element) => {
        const text = [...element.childNodes].find((node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim())
        const range = document.createRange(); range.selectNodeContents(text); return range.getClientRects().length
      }),
      chartWidth: document.querySelector('.expense-chart').clientWidth,
      tableWidth: document.querySelector('.table-scroll table').getBoundingClientRect().width,
    }))
    assert.equal(metrics.overflow, false)
    assert(metrics.moneyLines.every((count) => count === 1))
    assert(metrics.chartWidth > 0)
    evidence.mobile.push({ width, ...metrics })
    await screenshot(`p1-mobile${width}.png`)
  }
  evidence.checks.push('ECharts actual SVG instance data/legend match real summary; resize works at390/320; amounts single-line and document has no overflow')
  assert.deepEqual(runtimeErrors, [])
  evidence.checks.push('No uncaught page JavaScript errors')
  evidence.status = 'passed'
} catch (error) {
  failed = error
  evidence.status = 'failed'
  evidence.failure = error.message
  if (page) await page.screenshot({ path: path.join(root, 'screenshots/p1-failure.png'), fullPage: true }).catch(() => {})
} finally {
  try {
    if (state.baseline_captured) {
      await saveState()
      evidence.cleanup = sqlCheck(true)
      state.phase = 'cleaned'
      await saveState()
      if (page) {
        await page.setViewportSize({ width: 1440, height: 1080 })
        await page.reload({ waitUntil: 'networkidle' })
        await page.evaluate(() => window.scrollTo({ top: 0, left: 0, behavior: 'instant' }))
        await page.screenshot({ path: path.join(root, 'screenshots/p1-final-desktop.png'), fullPage: true })
        evidence.screenshots.push('screenshots/p1-final-desktop.png')
      }
    }
  } catch (error) {
    failed ||= error
    evidence.cleanup_failure = error.message
    evidence.status = 'failed'
  }
  evidence.finished_at = new Date().toISOString()
  await writeFile(resultPath, `${JSON.stringify(evidence, null, 2)}\n`)
  await browser.close()
}
if (failed) throw failed
console.log(JSON.stringify(evidence, null, 2))
