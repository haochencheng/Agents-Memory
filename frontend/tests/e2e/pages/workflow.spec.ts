import { test, expect } from '@playwright/test'
import { takeScreenshot, waitForPageReady } from '../helpers'

test.describe('Workflow (/workflow)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/workflow')
    await waitForPageReady(page)
  })

  test('page title visible', async ({ page }) => {
    await takeScreenshot(page, 'workflow-full')
    await expect(page.locator('h1').first()).toBeVisible()
  })

  test('workflow stepper or empty state visible', async ({ page }) => {
    const hasStepper = await page.locator('[data-testid="workflow-stepper"]').count()
    const hasEmpty = await page.locator('text=暂无工作流记录').count()
    expect(hasStepper + hasEmpty).toBeGreaterThan(0)
  })

  test('workflow explanation section visible', async ({ page }) => {
    await expect(page.locator('text=工作流说明')).toBeVisible()
  })
})
