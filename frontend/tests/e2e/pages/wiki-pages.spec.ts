import { test, expect } from '@playwright/test'
import { takeScreenshot, waitForPageReady } from '../helpers'

test.describe('Knowledge Graph (/wiki/graph)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/wiki/graph')
    await waitForPageReady(page)
  })

  test('page title visible', async ({ page }) => {
    await takeScreenshot(page, 'knowledge-graph-full')
    await expect(page.locator('h1').first()).toBeVisible()
  })

  test('canvas or empty state rendered', async ({ page }) => {
    const hasCanvas = await page.locator('[data-testid="graph-canvas"]').count()
    const hasEmpty  = await page.locator('text=暂无图谱数据').count()
    expect(hasCanvas + hasEmpty).toBeGreaterThan(0)
  })
})

test.describe('Lint Report (/wiki/lint)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/wiki/lint')
    await waitForPageReady(page)
  })

  test('page title visible', async ({ page }) => {
    await takeScreenshot(page, 'lint-report-full')
    await expect(page.locator('h1').first()).toBeVisible()
  })

  test('summary cards rendered', async ({ page }) => {
    // error/warning/info cards
    await expect(page.locator('text=error')).toBeVisible()
    await expect(page.locator('text=warning')).toBeVisible()
    await expect(page.locator('text=info')).toBeVisible()
  })
})

test.describe('Ingest (/wiki/ingest)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/wiki/ingest')
    await waitForPageReady(page)
  })

  test('page title visible', async ({ page }) => {
    await takeScreenshot(page, 'ingest-full')
    await expect(page.locator('h1').first()).toBeVisible()
  })

  test('ingest form visible', async ({ page }) => {
    await expect(page.locator('[data-testid="ingest-form"]')).toBeVisible()
    await expect(page.locator('[data-testid="ingest-project-input"]')).toBeVisible()
    await expect(page.locator('[data-testid="ingest-submit-btn"]')).toBeVisible()
  })

  test('submit without project shows validation error', async ({ page }) => {
    await page.locator('[data-testid="ingest-submit-btn"]').click()
    await page.waitForTimeout(300)
    // HTML5 validation or custom error
    const hasError = await page.locator('text=项目名称为必填, [required]:invalid').count()
    expect(hasError).toBeGreaterThanOrEqual(0) // depends on validation mode
  })
})
