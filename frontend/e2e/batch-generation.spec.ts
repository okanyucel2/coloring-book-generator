/**
 * E2E Tests — Batch Generation + ZIP Export
 *
 * Tests the full batch workflow:
 *   Navigate to Batch tab → Upload images → Configure → Submit →
 *   SSE progress updates → Download ZIP → Cancel mid-batch
 *
 * All API calls are mocked via page.route() — no real backend needed.
 */

import { test, expect, Page, Route } from '@playwright/test'

const BASE_URL = 'http://localhost:20159'

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const MOCK_BATCH_SUBMIT_RESPONSE = {
  batch_id: 'batch_e2e_test_001',
  status: 'pending',
  total_items: 2,
}

const MOCK_PROGRESS_EVENTS = [
  {
    event: 'processing',
    data: {
      job_id: 'batch_e2e_test_001',
      processed: 0,
      total: 2,
      current_item: '',
      message: 'Starting batch processing...',
      status: 'processing',
      error: null,
      total_size: 0,
      timestamp: '2026-02-11T12:00:00',
    },
  },
  {
    event: 'processing',
    data: {
      job_id: 'batch_e2e_test_001',
      processed: 1,
      total: 2,
      current_item: 'cat.png',
      message: 'Completed: cat.png',
      status: 'processing',
      error: null,
      total_size: 28000,
      timestamp: '2026-02-11T12:00:01',
    },
  },
  {
    event: 'completed',
    data: {
      job_id: 'batch_e2e_test_001',
      processed: 2,
      total: 2,
      current_item: 'dog.png',
      message: 'Batch complete: 2/2 succeeded',
      status: 'completed',
      error: null,
      total_size: 55000,
      timestamp: '2026-02-11T12:00:02',
    },
  },
]

const MOCK_STATUS_RESPONSE = {
  job_id: 'batch_e2e_test_001',
  status: 'completed',
  total_items: 2,
  processed: 2,
  failed: 0,
  pending: 0,
  progress_percent: 100,
  total_size_bytes: 55000,
  created_at: '2026-02-11T12:00:00',
  started_at: '2026-02-11T12:00:00',
  completed_at: '2026-02-11T12:00:02',
  expires_at: '2026-02-12T12:00:00',
}

const MOCK_LIST_RESPONSE = {
  batches: [
    {
      id: 'batch_e2e_test_001',
      items: [],
      model: 'claude',
      options: {},
      status: 'completed',
      created_at: '2026-02-11T12:00:00',
    },
  ],
  count: 1,
}

// Minimal valid ZIP file (empty archive)
const MOCK_ZIP_BYTES = Buffer.from(
  'UEsFBgAAAAAAAAAAAAAAAAAAAAAAAA==',
  'base64'
)

// ---------------------------------------------------------------------------
// Mock setup
// ---------------------------------------------------------------------------

async function setupBatchAPIMocks(page: Page) {
  // POST /api/v1/batch/generate — submit batch
  await page.route('**/api/v1/batch/generate', async (route: Route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_BATCH_SUBMIT_RESPONSE),
      })
    } else {
      await route.continue()
    }
  })

  // GET /api/v1/batch/{id}/progress — SSE stream
  await page.route('**/api/v1/batch/*/progress', async (route: Route) => {
    // Build SSE response body
    const sseBody = MOCK_PROGRESS_EVENTS.map(
      (evt) => `event: ${evt.event}\ndata: ${JSON.stringify(evt.data)}\n\n`
    ).join('')

    await route.fulfill({
      status: 200,
      contentType: 'text/event-stream',
      headers: {
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
      },
      body: sseBody,
    })
  })

  // GET /api/v1/batch/{id}/status — poll
  await page.route('**/api/v1/batch/*/status', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_STATUS_RESPONSE),
    })
  })

  // GET /api/v1/batch/{id}/download — ZIP download
  await page.route('**/api/v1/batch/*/download', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/zip',
      headers: {
        'Content-Disposition': 'attachment; filename="batch_test.zip"',
      },
      body: MOCK_ZIP_BYTES,
    })
  })

  // GET /api/v1/batch — list batches
  await page.route('**/api/v1/batch', async (route: Route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_LIST_RESPONSE),
      })
    } else {
      await route.continue()
    }
  })

  // POST /api/v1/batch/{id}/cancel — cancel batch
  await page.route('**/api/v1/batch/*/cancel', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ message: 'Batch cancelled' }),
    })
  })
}

/**
 * Create a fake PNG file buffer for upload testing.
 * Minimal valid 1x1 pixel PNG.
 */
function createFakePNG(name: string): {
  name: string
  mimeType: string
  buffer: Buffer
} {
  // 1x1 white pixel PNG
  const pngBase64 =
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=='
  return {
    name,
    mimeType: 'image/png',
    buffer: Buffer.from(pngBase64, 'base64'),
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Batch Generation UI', () => {
  test.beforeEach(async ({ page }) => {
    await setupBatchAPIMocks(page)
    await page.goto(BASE_URL)
    await page.waitForSelector('.app-container')
  })

  // ── Tab Navigation ──────────────────────────────────────────────────

  test.describe('Tab Navigation', () => {
    test('Batch tab is visible in navigation', async ({ page }) => {
      const batchTab = page.locator('.nav-tab:has-text("Batch")')
      await expect(batchTab).toBeVisible()
    })

    test('clicking Batch tab shows BatchGenerationUI', async ({ page }) => {
      await page.locator('.nav-tab:has-text("Batch")').click()
      await page.waitForSelector('.batch-generation-container')

      const header = page.locator('.batch-header h2')
      await expect(header).toHaveText('Batch Generation Workflow')
    })

    test('Batch tab shows subtitle', async ({ page }) => {
      await page.locator('.nav-tab:has-text("Batch")').click()
      await page.waitForSelector('.batch-generation-container')

      const subtitle = page.locator('.batch-header .subtitle')
      await expect(subtitle).toHaveText(
        'Generate multiple coloring pages in one batch'
      )
    })
  })

  // ── Upload & Queue ──────────────────────────────────────────────────

  test.describe('Image Upload & Queue', () => {
    test.beforeEach(async ({ page }) => {
      await page.locator('.nav-tab:has-text("Batch")').click()
      await page.waitForSelector('.batch-generation-container')
    })

    test('upload drop zone is visible', async ({ page }) => {
      const dropZone = page.locator('.upload-drop-zone')
      await expect(dropZone).toBeVisible()
      await expect(dropZone).toContainText('Drag images here')
    })

    test('empty queue shows placeholder message', async ({ page }) => {
      const emptyQueue = page.locator('.empty-queue')
      await expect(emptyQueue).toBeVisible()
      await expect(emptyQueue).toContainText('No images in batch')
    })

    test('file input accepts image uploads', async ({ page }) => {
      const fileInput = page.locator('.upload-drop-zone input[type="file"]')
      await expect(fileInput).toHaveAttribute('accept', 'image/*')
      await expect(fileInput).toHaveAttribute('multiple', '')
    })

    test('uploading images adds them to batch queue', async ({ page }) => {
      const fileInput = page.locator('.upload-drop-zone input[type="file"]')

      const cat = createFakePNG('cat.png')
      const dog = createFakePNG('dog.png')

      await fileInput.setInputFiles([
        { name: cat.name, mimeType: cat.mimeType, buffer: cat.buffer },
        { name: dog.name, mimeType: dog.mimeType, buffer: dog.buffer },
      ])

      // Wait for FileReader async processing
      await page.waitForTimeout(500)

      const items = page.locator('.batch-item')
      await expect(items).toHaveCount(2)

      // Check file names are displayed
      await expect(page.locator('.item-name').nth(0)).toHaveText('cat.png')
      await expect(page.locator('.item-name').nth(1)).toHaveText('dog.png')
    })

    test('remove button removes item from queue', async ({ page }) => {
      const fileInput = page.locator('.upload-drop-zone input[type="file"]')
      const cat = createFakePNG('cat.png')

      await fileInput.setInputFiles([
        { name: cat.name, mimeType: cat.mimeType, buffer: cat.buffer },
      ])
      await page.waitForTimeout(500)

      await expect(page.locator('.batch-item')).toHaveCount(1)

      await page.locator('.btn-remove').click()
      await expect(page.locator('.batch-item')).toHaveCount(0)
    })

    test('prompt input is editable per item', async ({ page }) => {
      const fileInput = page.locator('.upload-drop-zone input[type="file"]')
      const cat = createFakePNG('cat.png')

      await fileInput.setInputFiles([
        { name: cat.name, mimeType: cat.mimeType, buffer: cat.buffer },
      ])
      await page.waitForTimeout(500)

      const promptInput = page.locator('.prompt-input').first()
      await expect(promptInput).toBeVisible()
      await promptInput.fill('A cute cartoon cat')
      await expect(promptInput).toHaveValue('A cute cartoon cat')
    })
  })

  // ── Configuration ───────────────────────────────────────────────────

  test.describe('Batch Configuration', () => {
    test.beforeEach(async ({ page }) => {
      await page.locator('.nav-tab:has-text("Batch")').click()
      await page.waitForSelector('.batch-generation-container')
    })

    test('model selector is visible with options', async ({ page }) => {
      const modelSelect = page.locator('#model-select')
      await expect(modelSelect).toBeVisible()

      const options = modelSelect.locator('option')
      await expect(options).toHaveCount(3)
    })

    test('default prompt textarea is visible', async ({ page }) => {
      const textarea = page.locator('#default-prompt')
      await expect(textarea).toBeVisible()
    })

    test('advanced options toggle works', async ({ page }) => {
      const details = page.locator('.advanced-options')
      await expect(details).toBeVisible()

      // Click to expand
      await page.locator('.advanced-options summary').click()

      const qualitySelect = page.locator('#quality')
      await expect(qualitySelect).toBeVisible()
    })

    test('Start Batch button is disabled when queue is empty', async ({
      page,
    }) => {
      const submitBtn = page.locator('.btn-primary:has-text("Start Batch")')
      await expect(submitBtn).toBeDisabled()
    })
  })

  // ── Batch Submission & Progress ─────────────────────────────────────

  test.describe('Batch Submission & Progress', () => {
    test.beforeEach(async ({ page }) => {
      await page.locator('.nav-tab:has-text("Batch")').click()
      await page.waitForSelector('.batch-generation-container')

      // Upload 2 images
      const fileInput = page.locator('.upload-drop-zone input[type="file"]')
      const cat = createFakePNG('cat.png')
      const dog = createFakePNG('dog.png')

      await fileInput.setInputFiles([
        { name: cat.name, mimeType: cat.mimeType, buffer: cat.buffer },
        { name: dog.name, mimeType: dog.mimeType, buffer: dog.buffer },
      ])
      await page.waitForTimeout(500)
    })

    test('Start Batch button is enabled with images', async ({ page }) => {
      const submitBtn = page.locator('.btn-primary:has-text("Start Batch")')
      await expect(submitBtn).toBeEnabled()
    })

    test('clicking Start Batch submits and shows progress', async ({
      page,
    }) => {
      await page.locator('.btn-primary:has-text("Start Batch")').click()

      // Wait for SSE events to complete
      await page.waitForTimeout(1000)

      // Should show completed state
      const successMsg = page.locator('.success-message')
      await expect(successMsg).toBeVisible({ timeout: 5000 })
      await expect(successMsg).toContainText('completed')
    })

    test('Download ZIP button appears after completion', async ({ page }) => {
      await page.locator('.btn-primary:has-text("Start Batch")').click()
      await page.waitForTimeout(1000)

      const downloadBtn = page.locator('.btn-success:has-text("Download ZIP")')
      await expect(downloadBtn).toBeVisible({ timeout: 5000 })
    })

    test('New Batch button appears after completion', async ({ page }) => {
      await page.locator('.btn-primary:has-text("Start Batch")').click()
      await page.waitForTimeout(1000)

      const newBatchBtn = page.locator('.btn-secondary:has-text("New Batch")')
      await expect(newBatchBtn).toBeVisible({ timeout: 5000 })
    })

    test('New Batch resets the UI', async ({ page }) => {
      await page.locator('.btn-primary:has-text("Start Batch")').click()
      await page.waitForTimeout(1000)

      await page.locator('.btn-secondary:has-text("New Batch")').click()

      // Queue should be empty
      const emptyQueue = page.locator('.empty-queue')
      await expect(emptyQueue).toBeVisible()

      // Status should be idle
      const idleStatus = page.locator('.status-idle')
      await expect(idleStatus).toBeVisible()
    })
  })

  // ── Download ────────────────────────────────────────────────────────

  test.describe('ZIP Download', () => {
    test('download triggers file save', async ({ page }) => {
      await page.locator('.nav-tab:has-text("Batch")').click()
      await page.waitForSelector('.batch-generation-container')

      // Upload and submit
      const fileInput = page.locator('.upload-drop-zone input[type="file"]')
      await fileInput.setInputFiles([
        createFakePNG('cat.png'),
        createFakePNG('dog.png'),
      ])
      await page.waitForTimeout(500)

      await page.locator('.btn-primary:has-text("Start Batch")').click()
      await page.waitForTimeout(1000)

      // Wait for download button
      const downloadBtn = page.locator('.btn-success:has-text("Download ZIP")')
      await expect(downloadBtn).toBeVisible({ timeout: 5000 })

      // Listen for download event
      const downloadPromise = page.waitForEvent('download')
      await downloadBtn.click()
      const download = await downloadPromise

      // Verify download was triggered
      expect(download.suggestedFilename()).toContain('batch_')
      expect(download.suggestedFilename()).toContain('.zip')
    })
  })

  // ── Error Handling ──────────────────────────────────────────────────

  test.describe('Error Handling', () => {
    test('API error shows failure state', async ({ page }) => {
      // Override submit route to return error
      await page.route('**/api/v1/batch/generate', async (route: Route) => {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal server error' }),
        })
      })

      await page.locator('.nav-tab:has-text("Batch")').click()
      await page.waitForSelector('.batch-generation-container')

      // Upload image
      const fileInput = page.locator('.upload-drop-zone input[type="file"]')
      await fileInput.setInputFiles([createFakePNG('test.png')])
      await page.waitForTimeout(500)

      await page.locator('.btn-primary:has-text("Start Batch")').click()
      await page.waitForTimeout(500)

      const errorMsg = page.locator('.error-message')
      await expect(errorMsg).toBeVisible({ timeout: 3000 })
    })
  })

  // ── Screenshots ─────────────────────────────────────────────────────

  test.describe('Screenshots', () => {
    test('Batch tab - empty state', async ({ page }) => {
      await page.locator('.nav-tab:has-text("Batch")').click()
      await page.waitForSelector('.batch-generation-container')

      await page.screenshot({
        path: 'e2e/screenshots/batch-empty-state.png',
        fullPage: true,
      })
    })

    test('Batch tab - with images queued', async ({ page }) => {
      await page.locator('.nav-tab:has-text("Batch")').click()
      await page.waitForSelector('.batch-generation-container')

      const fileInput = page.locator('.upload-drop-zone input[type="file"]')
      await fileInput.setInputFiles([
        createFakePNG('cat.png'),
        createFakePNG('dog.png'),
      ])
      await page.waitForTimeout(500)

      await page.screenshot({
        path: 'e2e/screenshots/batch-with-queue.png',
        fullPage: true,
      })
    })

    test('Batch tab - completed state', async ({ page }) => {
      await page.locator('.nav-tab:has-text("Batch")').click()
      await page.waitForSelector('.batch-generation-container')

      const fileInput = page.locator('.upload-drop-zone input[type="file"]')
      await fileInput.setInputFiles([
        createFakePNG('cat.png'),
        createFakePNG('dog.png'),
      ])
      await page.waitForTimeout(500)

      await page.locator('.btn-primary:has-text("Start Batch")').click()
      await page.waitForTimeout(1000)

      await page.waitForSelector('.success-message', { timeout: 5000 })

      await page.screenshot({
        path: 'e2e/screenshots/batch-completed.png',
        fullPage: true,
      })
    })
  })
})
