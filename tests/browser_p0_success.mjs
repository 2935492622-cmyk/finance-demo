// Actual page form -> API -> MySQL acceptance. Only GETs are sent programmatically.
import assert from 'node:assert/strict'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { spawnSync } from 'node:child_process'
import { randomUUID } from 'node:crypto'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from '../frontend/node_modules/playwright/index.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const statePath = path.join(root, 'tests/.p0-demo-state.json')
const evidencePath = path.join(root, 'docs/qa/browser-p0-success-result.json')
const verifyRestart = process.argv.includes('--verify-after-restart')
const frontend = process.env.FINANCE_QA_FRONTEND_URL || 'http://127.0.0.1:5173'
assert(['127.0.0.1', 'localhost', '[::1]'].includes(new URL(frontend).hostname))
const executablePath = process.env.FINANCE_QA_BROWSER_EXECUTABLE
assert(executablePath, 'Set FINANCE_QA_BROWSER_EXECUTABLE')
const env = { ...process.env }
if (process.env.FINANCE_QA_BROWSER_LIBRARY_PATH) {
  env.LD_LIBRARY_PATH = [process.env.FINANCE_QA_BROWSER_LIBRARY_PATH, env.LD_LIBRARY_PATH].filter(Boolean).join(':')
}
await mkdir(path.join(root, 'screenshots'), { recursive: true })
let state
if (verifyRestart) {
  state = JSON.parse(await readFile(statePath, 'utf8'))
  assert.equal(state.created_records.length, 2)
} else {
  const existing = await readFile(statePath, 'utf8').catch((error) => {
    if (error.code === 'ENOENT') return null
    throw error
  })
  assert.equal(existing, null, 'Demo state exists: do not create duplicate records; inspect it or use --verify-after-restart')
  state = { run_marker: `qa-demo-${randomUUID().slice(0, 12)}`, created_records: [], started_at: new Date().toISOString() }
}
async function saveState() {
  await writeFile(statePath, `${JSON.stringify(state, null, 2)}\n`, { mode: 0o600 })
}
function cents(value) {
  assert.match(value, /^-?\d+\.\d{2}$/)
  const negative = value.startsWith('-')
  const [whole, fraction] = value.replace('-', '').split('.')
  return (negative ? -1n : 1n) * (BigInt(whole) * 100n + BigInt(fraction))
}
function decimal(value) {
  const negative = value < 0n
  const absolute = negative ? -value : value
  return `${negative ? '-' : ''}${absolute / 100n}.${String(absolute % 100n).padStart(2, '0')}`
}
function formatted(value) {
  const [whole, fraction] = value.split('.')
  return `${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}.${fraction}`
}
const browser = await chromium.launch({ executablePath, env, headless: true })
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1080 }, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' })
  const page = await context.newPage()
  const errors = []
  const pagePosts = []
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('request', (request) => {
    if (request.method() === 'POST' && new URL(request.url()).pathname === '/api/transactions') pagePosts.push(request.postDataJSON())
  })
  const health = await page.request.get(`${frontend}/api/health`)
  assert.equal(health.status(), 200)
  const initialSummary = await page.request.get(`${frontend}/api/summary`)
  assert.equal(initialSummary.status(), 200)
  const before = await initialSummary.json()
  const response = await page.goto(frontend, { waitUntil: 'networkidle' })
  assert.equal(response.status(), 200)
  await page.locator('.count-badge').filter({ hasText: `${before.transaction_count} 笔记录` }).waitFor()

  if (!verifyRestart) {
    state.baseline = { total_income: before.total_income, total_expense: before.total_expense, balance: before.balance, transaction_count: before.transaction_count }
    state.expected = {
      total_income: decimal(cents(before.total_income) + 100000n),
      total_expense: decimal(cents(before.total_expense) + 12550n),
      balance: decimal(cents(before.balance) + 87450n),
      transaction_count: before.transaction_count + 2,
    }
    await saveState()
    for (const [amount, type, category] of [['1000.00', 'income', '工资'], ['125.50', 'expense', '餐饮']]) {
      await page.getByRole('button', { name: type === 'income' ? '收入' : '支出', exact: true }).click()
      await page.locator('#amount').fill(amount)
      await page.locator('#category').fill(category)
      await page.locator('#transaction-date').fill('2026-11-15')
      const note = `${state.run_marker}-${type}`
      await page.locator('#note').fill(note)
      const saved = page.waitForResponse((item) => item.request().method() === 'POST' && new URL(item.url()).pathname === '/api/transactions')
      await page.getByRole('button', { name: '保存这一笔', exact: true }).click()
      const result = await saved
      assert.equal(result.status(), 201)
      const record = await result.json()
      state.created_records.push(record)
      await saveState()
      assert.equal(record.amount, amount)
      assert.equal(record.type, type)
      assert.equal(record.category, category)
      assert.equal(record.note, note)
      await page.getByText(note, { exact: true }).waitFor()
      await page.waitForFunction(() => document.querySelector('#amount').value === '' && !document.querySelector('.save-button').disabled)
    }
    assert.equal(pagePosts.length, 2)
    assert.deepEqual(pagePosts.map((item) => item.type), ['income', 'expense'])
    state.page_post_count = 2
  } else {
    assert.equal(pagePosts.length, 0, 'Restart verification must not create records')
  }

  const listed = await page.request.get(`${frontend}/api/transactions`)
  const summaryResponse = await page.request.get(`${frontend}/api/summary`)
  assert.equal(listed.status(), 200)
  assert.equal(summaryResponse.status(), 200)
  const records = await listed.json()
  const summary = await summaryResponse.json()
  assert.equal(records.total, records.items.length)
  for (const own of state.created_records) {
    assert.deepEqual(records.items.find((item) => item.id === own.id), own)
    await page.getByText(own.note, { exact: true }).waitFor()
  }
  if (!verifyRestart) {
    for (const [key, expected] of Object.entries(state.expected)) assert.equal(summary[key], expected)
  }
  const sqlProcess = spawnSync(path.join(root, '.venv/bin/python'), [path.join(root, 'tests/sql_p0_evidence.py'), statePath], {
    cwd: root, encoding: 'utf8', timeout: 15000,
  })
  assert.equal(sqlProcess.status, 0, sqlProcess.stderr || 'SQL evidence bridge failed')
  const sql = JSON.parse(sqlProcess.stdout)
  for (const [key, expected] of Object.entries(sql.sql_totals)) assert.equal(summary[key], expected)
  await page.reload({ waitUntil: 'networkidle' })
  for (const own of state.created_records) await page.getByText(own.note, { exact: true }).waitFor()
  await page.locator('.count-badge').filter({ hasText: `${records.total} 笔记录` }).waitFor()
  const actualAmounts = await page.locator('.summary-amount').allTextContents()
  for (const [index, key] of ['total_income', 'total_expense', 'balance'].entries()) {
    assert.equal(actualAmounts[index].replace(/[¥\s]/g, ''), formatted(summary[key]))
  }
  assert.equal(await page.locator('table tbody tr').count(), records.total)
  assert.equal(await page.getByRole('alert').count(), 0)
  assert.deepEqual(errors, [])
  const suffix = verifyRestart ? 'after-restart' : 'success'
  const screenshots = []
  const desktop = `screenshots/p0-desktop-${suffix}.png`
  await page.screenshot({ path: path.join(root, desktop), fullPage: true })
  screenshots.push(desktop)
  await page.setViewportSize({ width: 390, height: 844 })
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth))
  const mobileMetrics = await page.evaluate((notes) => {
    const amountLines = [...document.querySelectorAll('.summary-amount')].map((element) => {
      const text = [...element.childNodes].find((node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim())
      if (!text) return 0
      const range = document.createRange()
      range.selectNodeContents(text)
      return range.getClientRects().length
    })
    const noteLines = [...document.querySelectorAll('.record-note')]
      .filter((element) => notes.includes(element.textContent))
      .map((element) => element.getBoundingClientRect().height / Number.parseFloat(getComputedStyle(element).lineHeight))
    const wrapper = document.querySelector('.table-scroll')
    return { amountLines, noteLines, tableWidth: wrapper.querySelector('table').getBoundingClientRect().width, viewportWidth: window.innerWidth }
  }, state.created_records.map((record) => record.note))
  assert(mobileMetrics.amountLines.every((count) => count === 1), 'Mobile money must remain a single readable line')
  assert(mobileMetrics.noteLines.every((count) => count <= 2.1), 'Known demo notes must not become narrow vertical fragments')
  const mobile = `screenshots/p0-mobile-${suffix}.png`
  await page.screenshot({ path: path.join(root, mobile), fullPage: true })
  screenshots.push(mobile)
  const evidence = verifyRestart ? JSON.parse(await readFile(evidencePath, 'utf8')) : {
    scenario: 'Actual browser form creates income and expense; real MySQL cross-check; records retained for user preview',
    run_marker: state.run_marker, baseline: state.baseline, expected_after_page_writes: state.expected,
    page_created_records: state.created_records, page_post_count: state.page_post_count,
    browser_refresh_verified: true, sql_before_restart: sql, screenshots,
    mobile_readability: mobileMetrics,
    completed_before_restart_at: new Date().toISOString(), backend_restart_verified: false,
  }
  if (verifyRestart) {
    evidence.backend_restart_verified = true
    evidence.sql_after_restart = sql
    evidence.summary_after_restart = summary
    evidence.screenshots_after_restart = screenshots
    evidence.mobile_readability_after_restart = mobileMetrics
    evidence.completed_after_restart_at = new Date().toISOString()
    state.phase = 'p0-persistence-verified-records-retained'
  } else {
    state.phase = 'awaiting-backend-restart'
  }
  await saveState()
  await writeFile(evidencePath, `${JSON.stringify(evidence, null, 2)}\n`)
  console.log(JSON.stringify({
    phase: state.phase, run_marker: state.run_marker, ids: state.created_records.map((row) => row.id),
    summary: Object.fromEntries(['total_income', 'total_expense', 'balance', 'transaction_count'].map((key) => [key, summary[key]])),
    screenshots, evidence: 'docs/qa/browser-p0-success-result.json',
    records_retained: true,
  }, null, 2))
} finally {
  await browser.close()
}
