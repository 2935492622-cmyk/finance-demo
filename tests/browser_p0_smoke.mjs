// Real local browser + actual backend 503 checks. No request interception or fake 201.
import assert from 'node:assert/strict'
import { mkdir, writeFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import path from 'node:path'
import { chromium } from '../frontend/node_modules/playwright/index.mjs'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const frontend = process.env.FINANCE_QA_FRONTEND_URL || 'http://127.0.0.1:5173'
const address = new URL(frontend)
assert(['127.0.0.1', 'localhost', '[::1]'].includes(address.hostname), 'Browser QA only targets localhost')
const executablePath = process.env.FINANCE_QA_BROWSER_EXECUTABLE
assert(executablePath, 'Set FINANCE_QA_BROWSER_EXECUTABLE to an existing local browser')
const env = { ...process.env }
if (process.env.FINANCE_QA_BROWSER_LIBRARY_PATH) {
  env.LD_LIBRARY_PATH = [process.env.FINANCE_QA_BROWSER_LIBRARY_PATH, env.LD_LIBRARY_PATH].filter(Boolean).join(':')
}
const screenshotDir = path.join(root, 'screenshots')
await mkdir(screenshotDir, { recursive: true })
await mkdir(path.join(root, 'docs/qa'), { recursive: true })
const browser = await chromium.launch({ executablePath, env, headless: true })
const evidence = {
  scenario: 'P0 actual database-unavailable UI; successful CRUD and persistence NOT tested',
  started_at: new Date().toISOString(), checks: [], screenshots: [],
}
try {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1080 }, locale: 'zh-CN', timezoneId: 'Asia/Shanghai' })
  const page = await context.newPage()
  const runtimeErrors = []
  const posts = []
  page.on('pageerror', (error) => runtimeErrors.push(error.message))
  page.on('request', (request) => {
    if (request.method() === 'POST' && new URL(request.url()).pathname === '/api/transactions') posts.push(request.postDataJSON())
  })
  const health = await page.request.get(`${frontend}/api/health`)
  assert.equal(health.status(), 503, '503-only smoke must stop if database is available or backend is unreachable')
  const response = await page.goto(frontend, { waitUntil: 'networkidle' })
  assert.equal(response.status(), 200)
  await page.getByRole('heading', { name: '把日子，记得清楚一点。' }).waitFor()
  await page.getByRole('alert').filter({ hasText: '数据库暂不可用' }).waitFor()
  const amounts = await page.locator('.summary-amount').allTextContents()
  assert.equal(amounts.length, 3)
  assert(amounts.every((text) => text.includes('—')), 'Failure must not be presented as successful zero totals')
  assert.equal(await page.getByRole('heading', { name: '从第一笔开始' }).count(), 0)
  evidence.checks.push('Real API health=503, page=200; visible failure, unknown totals, no fake empty success')

  await page.locator('#amount').fill('12.345')
  await page.locator('#category').fill('餐饮')
  await page.getByRole('button', { name: '保存这一笔', exact: true }).click()
  await page.locator('#amount-error').waitFor()
  assert.equal(posts.length, 0, 'Invalid decimal input must not cause a POST')
  evidence.checks.push('Amount with three decimal places rejected visibly before HTTP write')

  await page.locator('#amount').fill('12.3')
  await page.locator('#note').fill('qa-browser-p0-database-unavailable')
  assert.equal((await page.request.get(`${frontend}/api/health`)).status(), 503)
  const writeResponse = page.waitForResponse((item) => item.request().method() === 'POST' && new URL(item.url()).pathname === '/api/transactions')
  await page.locator('.entry-panel form').evaluate((form) => { form.requestSubmit(); form.requestSubmit() })
  assert.equal((await writeResponse).status(), 503)
  await page.getByRole('status').filter({ hasText: '保存结果尚未确认' }).waitFor()
  assert.equal(posts.length, 1, 'Duplicate submit in the same turn must create only one request')
  assert.equal(posts[0].amount, '12.30')
  assert.equal(await page.locator('#amount').inputValue(), '12.3')
  assert.equal(await page.locator('#category').inputValue(), '餐饮')
  assert.equal(await page.locator('#note').inputValue(), 'qa-browser-p0-database-unavailable')
  assert.equal(await page.locator('.notice.success').count(), 0)
  assert(await page.getByRole('button', { name: '请先刷新核对记录', exact: true }).isDisabled())
  assert(await page.locator('#amount').isDisabled())
  assert(await page.locator('form fieldset').evaluate((fieldset) => fieldset.disabled))
  const retryRead = page.waitForResponse((item) => item.request().method() === 'GET' && new URL(item.url()).pathname === '/api/transactions')
  await page.getByRole('button', { name: '刷新核对', exact: true }).click()
  assert.equal((await retryRead).status(), 503)
  await page.waitForFunction(() => !document.querySelector('.secondary-button').disabled)
  assert(await page.getByRole('button', { name: '请先刷新核对记录', exact: true }).isDisabled())
  assert.equal(posts.length, 1)
  evidence.checks.push('Real POST=503; 12.3 serialized as 12.30; double submit suppressed; input retained; no success notice')
  evidence.checks.push('Write result unconfirmed after 503; form locked; failed refresh keeps lock without retrying POST')

  const desktopName = 'p0-desktop-database-unavailable.png'
  await page.screenshot({ path: path.join(screenshotDir, desktopName), fullPage: true })
  evidence.screenshots.push(`screenshots/${desktopName}`)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.getByRole('heading', { name: '记一笔', exact: true }).waitFor()
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'Mobile document must not overflow horizontally')
  assert(await page.getByRole('button', { name: '请先刷新核对记录', exact: true }).isVisible())
  const mobileName = 'p0-mobile-database-unavailable.png'
  await page.screenshot({ path: path.join(screenshotDir, mobileName), fullPage: true })
  evidence.screenshots.push(`screenshots/${mobileName}`)
  evidence.checks.push('390px narrow layout has no document horizontal overflow; form remains visible')
  assert.deepEqual(runtimeErrors, [])
  evidence.checks.push('No uncaught page JavaScript exceptions')
  evidence.finished_at = new Date().toISOString()
  evidence.status = 'passed: database-unavailable smoke only'
  await writeFile(path.join(root, 'docs/qa/browser-p0-result.json'), `${JSON.stringify(evidence, null, 2)}\n`)
  console.log(JSON.stringify(evidence, null, 2))
} finally {
  await browser.close()
}
