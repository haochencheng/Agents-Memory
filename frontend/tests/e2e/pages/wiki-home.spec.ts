import { test, expect } from '@playwright/test'
import { takeScreenshot, waitForPageReady } from '../helpers'

test.describe('Wiki Home (/wiki)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/wiki')
    await waitForPageReady(page)
  })

  test('page title visible', async ({ page }) => {
    await takeScreenshot(page, 'wiki-home-full')
    await expect(page.locator('h1').first()).toBeVisible()
  })

  test('search input is rendered', async ({ page }) => {
    await expect(page.locator('[data-testid="wiki-search-input"]')).toBeVisible()
  })

  test('topic cards or empty state shown', async ({ page }) => {
    const hasCards = await page.locator('[data-testid="wiki-card"]').count()
    const hasEmpty = await page.locator('text=暂无 Wiki 页面').count()
    expect(hasCards + hasEmpty).toBeGreaterThan(0)
  })

  test('search filters topics', async ({ page }) => {
    const input = page.locator('[data-testid="wiki-search-input"]')
    await input.fill('nonexistent-xyzabc123')
    await page.waitForTimeout(300)
    await takeScreenshot(page, 'wiki-home-search')
    await expect(page.locator('text=未找到匹配')).toBeVisible()
  })
})
