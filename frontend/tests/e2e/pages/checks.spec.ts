import { test, expect } from '@playwright/test'
import { takeScreenshot, waitForPageReady } from '../helpers'

test.describe('Checks (/checks)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/checks')
    await waitForPageReady(page)
  })

  test('page title visible', async ({ page }) => {
    await takeScreenshot(page, 'checks-full')
    await expect(page.locator('h1').first()).toBeVisible()
  })

  test('check type tabs rendered', async ({ page }) => {
    await expect(page.locator('button').filter({ hasText: 'docs-check' })).toBeVisible()
    await expect(page.locator('button').filter({ hasText: 'profile-check' })).toBeVisible()
    await expect(page.locator('button').filter({ hasText: 'plan-check' })).toBeVisible()
  })

  test('can switch to profile-check tab', async ({ page }) => {
    await page.locator('button').filter({ hasText: 'profile-check' }).click()
    await page.waitForTimeout(500)
    await takeScreenshot(page, 'checks-profile-tab')
  })

  test('refresh button is clickable', async ({ page }) => {
    const refreshBtn = page.locator('button').filter({ hasText: '刷新' })
    await expect(refreshBtn).toBeVisible()
    await refreshBtn.click()
  })
})
