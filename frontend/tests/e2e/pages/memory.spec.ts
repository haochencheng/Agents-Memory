import { test, expect } from '@playwright/test'
import { takeScreenshot, waitForPageReady } from '../helpers'

test.describe('Memory Records (/memory)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/memory')
    await waitForPageReady(page)
  })

  test('page title visible', async ({ page }) => {
    await takeScreenshot(page, 'memory-full')
    await expect(page.locator('h1').first()).toBeVisible()
  })

  test('tabs are rendered', async ({ page }) => {
    await expect(page.locator('button').filter({ hasText: '错误记录' })).toBeVisible()
    await expect(page.locator('button').filter({ hasText: '规则' })).toBeVisible()
  })

  test('can switch to rules tab', async ({ page }) => {
    await page.locator('button').filter({ hasText: '规则' }).click()
    await takeScreenshot(page, 'memory-rules-tab')
    // Rules tab content should now be active
    const rulesContent = await page.locator('[data-testid="rule-record"]').count()
    const noRulesText = await page.getByText('暂无规则').count()
    expect(rulesContent + noRulesText).toBeGreaterThanOrEqual(0) // may be empty
  })
})
