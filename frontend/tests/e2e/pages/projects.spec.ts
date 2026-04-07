import { test, expect } from '@playwright/test'
import { takeScreenshot, waitForPageReady } from '../helpers'

test.describe('Projects (/projects)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/projects')
    await waitForPageReady(page)
  })

  test('page title is visible', async ({ page }) => {
    await takeScreenshot(page, 'projects-full')
    await expect(page.locator('h1').first()).toBeVisible()
  })

  test('project list or empty state shown', async ({ page }) => {
    const hasCards = await page.locator('[data-testid="project-card"]').count()
    const hasEmpty = await page.locator('text=暂无接入项目').count()
    expect(hasCards + hasEmpty).toBeGreaterThan(0)
  })

  test('sidebar active state on Projects link', async ({ page }) => {
    await expect(page.locator('a[href="/projects"]').first()).toBeVisible()
  })
})

test.describe('Project Detail (/projects/:id)', () => {
  test('navigating to non-existent project shows error', async ({ page }) => {
    await page.goto('/projects/nonexistent-test-project')
    await waitForPageReady(page)
    await takeScreenshot(page, 'project-detail-notfound')
    // Should show error alert or back link
    const hasBack = await page.locator('text=返回项目列表').count()
    const hasError = await page.locator('[role="alert"], .text-red-500').count()
    expect(hasBack + hasError).toBeGreaterThan(0)
  })
})
