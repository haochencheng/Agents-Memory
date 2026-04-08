import { test, expect } from '@playwright/test'
import { takeScreenshot, waitForPageReady } from '../helpers'

const PROJECT_ROOT = '/Users/cliff/workspace/agent/Synapse-Network'
const APP_ROOT = 'http://127.0.0.1:10000'

async function mockOnboardingSuccess(page: import('@playwright/test').Page) {
  const wikiTopics = {
    topics: [
      {
        topic: 'synapse-network-readme',
        title: 'Synapse Network Readme',
        tags: ['onboarding'],
        word_count: 220,
        updated_at: '2026-04-08',
        project: 'synapse-network',
        source_path: 'README.md',
      },
      {
        topic: 'synapse-network-agents',
        title: 'Synapse Network Agents',
        tags: ['instructions'],
        word_count: 140,
        updated_at: '2026-04-08',
        project: 'synapse-network',
        source_path: 'AGENTS.md',
      },
      {
        topic: 'synapse-network-docs-design',
        title: 'Synapse Network Docs Design',
        tags: ['design'],
        word_count: 310,
        updated_at: '2026-04-08',
        project: 'synapse-network',
        source_path: 'docs/DESIGN.md',
      },
    ],
  }

  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    if (!url.pathname.startsWith('/api/')) {
      await route.continue()
      return
    }
    if (url.pathname === '/api/stats') {
      await route.fulfill({ json: { wiki_count: 3, error_count: 1, ingest_count: 3, projects: ['synapse-network'] } })
      return
    }
    if (url.pathname === '/api/wiki/lint') {
      await route.fulfill({ json: { issues: [], total: 0 } })
      return
    }
    if (url.pathname === '/api/checks/summary') {
      await route.fulfill({ json: {} })
      return
    }
    if (url.pathname === '/api/projects') {
      await route.fulfill({
        json: {
          projects: [
            {
              id: 'synapse-network',
              name: 'synapse-network',
              health: 'ok',
              wiki_count: 3,
              error_count: 1,
              last_ingest: '2026-04-08T09:30:00Z',
            },
          ],
        },
      })
      return
    }
    if (url.pathname === '/api/projects/synapse-network/stats') {
      await route.fulfill({
        json: {
          id: 'synapse-network',
          health: 'ok',
          wiki_count: 3,
          error_count: 1,
          checklist_done: 0,
          ingest_count: 3,
          last_error: 'ERR-2026-0312-001',
          last_ingest: '2026-04-08T09:30:00Z',
        },
      })
      return
    }
    if (url.pathname === '/api/wiki') {
      await route.fulfill({ json: wikiTopics })
      return
    }
    if (url.pathname === '/api/onboarding/bootstrap') {
      await route.fulfill({
        json: {
          success: true,
          project_id: 'synapse-network',
          project_root: PROJECT_ROOT,
          full: true,
          ingest_wiki: true,
          dry_run: false,
          enable_exit_code: 0,
          enable_log: '- registry: created (synapse-network)\n- wiki ingest: imported 3 files',
          discovered_files: ['README.md', 'AGENTS.md', 'docs/DESIGN.md'],
          ingested_files: 3,
          wiki_topics: wikiTopics.topics.map(item => item.topic),
          sources: wikiTopics.topics.map(item => ({ source_path: item.source_path, topic: item.topic })),
        },
      })
      return
    }
    if (url.pathname === '/api/ingest') {
      await route.fulfill({ json: { ingested: true, id: 'ERR-2026-0408-001', dry_run: false } })
      return
    }
    if (url.pathname === '/api/ingest/log') {
      await route.fulfill({ json: { entries: [], total: 0 } })
      return
    }
    await route.fulfill({ json: {} })
  })
}

test('frontend shows successful Synapse-Network onboarding flow', async ({ page }) => {
  test.setTimeout(60000)
  await mockOnboardingSuccess(page)

  await page.goto(`${APP_ROOT}/wiki/ingest`)
  await waitForPageReady(page)
  await expect(page.getByTestId('onboarding-root-input')).toBeVisible()
  await page.getByTestId('onboarding-root-input').fill(PROJECT_ROOT)
  await page.getByTestId('project-onboarding-submit').click()
  await expect(page.getByText(/项目接入完成/)).toBeVisible()
  await takeScreenshot(page, 'onboarding-success-ingest-page')

  await page.goto(`${APP_ROOT}/`)
  await waitForPageReady(page)
  await expect(page.getByText('synapse-network')).toBeVisible()
  await takeScreenshot(page, 'onboarding-success-overview')

  await page.goto(`${APP_ROOT}/projects`)
  await waitForPageReady(page)
  await expect(page.getByText('synapse-network')).toBeVisible()
  await takeScreenshot(page, 'onboarding-success-projects')

  await page.goto(`${APP_ROOT}/projects/synapse-network`)
  await waitForPageReady(page)
  await expect(page.getByText('最近摄入')).toBeVisible()
  await takeScreenshot(page, 'onboarding-success-project-detail')
})