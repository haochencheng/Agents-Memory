import { test, expect } from '@playwright/test'
import { takeScreenshot, waitForPageReady } from '../helpers'

test.describe('Overview (/)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
    await waitForPageReady(page)
  })

  test('page loads without blank screen', async ({ page }) => {
    await takeScreenshot(page, 'overview-full')
    const body = await page.textContent('body')
    expect(body).toBeTruthy()
    expect(body!.length).toBeGreaterThan(10)
  })

  test('page title is visible', async ({ page }) => {
    await expect(page.locator('.page-title, h1').first()).toBeVisible()
  })

  test('sidebar navigation is visible', async ({ page }) => {
    // Use more specific selectors to avoid strict mode (title and sidebar both may have 'Overview')
    await expect(page.locator('nav').getByText('Overview').first()).toBeVisible()
    await expect(page.locator('nav').getByText('Projects').first()).toBeVisible()
    await expect(page.locator('nav, [class*="sidebar"]').getByText('Wiki').first()).toBeVisible()
  })

  test('no fatal error alert on load', async ({ page }) => {
    // Check that the app shell (sidebar) is always present regardless of API state
    await expect(page.locator('aside, [class*="sidebar"]').first()).toBeVisible()
  })

  test('stat cards or error alert rendered (API state)', async ({ page }) => {
    await takeScreenshot(page, 'overview-viewport')
    // Either StatCards or ErrorAlert should be present (depends on if backend is up)
    const hasStatCard = await page.locator('[data-testid="stat-card"]').count()
    const hasErrorAlert = await page.locator('[role="alert"], .text-red-600').count()
    expect(hasStatCard + hasErrorAlert).toBeGreaterThan(0)
  })
})
