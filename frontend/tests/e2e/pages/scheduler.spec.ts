import { test, expect } from '@playwright/test'
import { takeScreenshot, waitForPageReady } from '../helpers'

test.describe('Scheduler (/scheduler)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/scheduler')
    await waitForPageReady(page)
  })

  test('page title visible', async ({ page }) => {
    await takeScreenshot(page, 'scheduler-full')
    await expect(page.locator('h1').first()).toBeVisible()
  })

  test('new task button visible', async ({ page }) => {
    await expect(page.locator('button').filter({ hasText: '新增任务' })).toBeVisible()
  })

  test('task list or empty state shown', async ({ page }) => {
    const hasTasks = await page.locator('[data-testid="task-item"]').count()
    const hasEmpty = await page.locator('text=暂无调度任务').count()
    expect(hasTasks + hasEmpty).toBeGreaterThan(0)
  })

  test('create form toggles on button click', async ({ page }) => {
    await page.locator('button').filter({ hasText: '新增任务' }).click()
    await expect(page.locator('[data-testid="create-task-form"]')).toBeVisible()
    await takeScreenshot(page, 'scheduler-form-open')
  })
})
