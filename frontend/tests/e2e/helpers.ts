import { test, expect } from '@playwright/test'
import path from 'path'
import fs from 'fs'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const SCREENSHOT_DIR = path.join(__dirname, 'screenshots')

export async function takeScreenshot(page: import('@playwright/test').Page, name: string) {
  const dir = path.join(SCREENSHOT_DIR, new Date().toISOString().slice(0, 10))
  fs.mkdirSync(dir, { recursive: true })
  await page.screenshot({ path: path.join(dir, `${name}.png`), fullPage: true })
}

export async function waitForPageReady(page: import('@playwright/test').Page) {
  // Wait for loading spinner to disappear (if any)
  await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => {})
  const spinner = page.locator('[data-testid="loading-spinner"]')
  if (await spinner.count() > 0) {
    await spinner.waitFor({ state: 'hidden', timeout: 8000 }).catch(() => {})
  }
}

export { test, expect }
