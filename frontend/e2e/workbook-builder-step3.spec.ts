/**
 * E2E Tests for WorkbookBuilder Step 3 — Preview & Generate Overhaul
 *
 * Tests the interactive Step 3 features:
 *  1. Page Thumbnail Gallery (horizontal scroll, lightbox)
 *  2. Activity Mix Adjustment (inline ActivityMixer)
 *  3. Staged Generation Progress (stage dots + labels)
 *  4. PDF Viewer (inline iframe preview)
 *
 * Uses route mocking to simulate backend responses without a running server.
 */
import { test, expect, Page, Route } from '@playwright/test'

const BASE_URL = 'http://localhost:20159'

// --- Mock Data ---

const MOCK_THEMES = {
  data: [
    {
      slug: 'vehicles',
      display_name: 'Vehicles',
      category: 'transport',
      items: ['car', 'truck', 'bus', 'train', 'plane', 'boat', 'helicopter', 'motorcycle'],
      item_count: 8,
      age_groups: ['3-5', '6-8'],
      etsy_tags: ['vehicles', 'coloring'],
    },
  ],
}

const MOCK_WORKBOOK_ID = 'test-wb-001'

const MOCK_WORKBOOK_RESPONSE = {
  id: MOCK_WORKBOOK_ID,
  theme: 'vehicles',
  title: 'Vehicles Activity Workbook',
  subtitle: 'For Ages 3-5',
  age_min: 3,
  age_max: 5,
  page_count: 30,
  items: ['car', 'truck', 'bus', 'train', 'plane', 'boat', 'helicopter', 'motorcycle'],
  activity_mix: {
    trace_and_color: 18,
    which_different: 2,
    count_circle: 2,
    match: 2,
    word_to_image: 1,
    find_circle: 2,
  },
  page_size: 'letter',
  status: 'draft',
  progress: null,
  pdf_url: null,
  etsy_listing_id: null,
}

const MOCK_PREVIEW = {
  id: MOCK_WORKBOOK_ID,
  status: 'draft',
  title: 'Vehicles Activity Workbook',
  theme: 'vehicles',
  total_pages: 28,
  activity_mix: {
    trace_and_color: 18,
    which_different: 2,
    count_circle: 2,
    match: 2,
    word_to_image: 1,
    find_circle: 2,
  },
  activity_breakdown: [
    { activity_type: 'trace_and_color', page_count: 18, page_range: { start: 2, end: 19 }, sampled_items: ['car', 'truck', 'bus', 'train', 'plane'] },
    { activity_type: 'which_different', page_count: 2, page_range: { start: 20, end: 21 }, sampled_items: ['boat', 'helicopter'] },
  ],
  page_thumbnails: [
    { page: 1, type: 'cover', label: 'Vehicles Activity Workbook', description: 'Cover page - vehicles theme' },
    { page: 2, type: 'trace_and_color', label: 'Car', description: 'Trace And Color - Car' },
    { page: 3, type: 'trace_and_color', label: 'Truck', description: 'Trace And Color - Truck' },
    { page: 4, type: 'trace_and_color', label: 'Bus', description: 'Trace And Color - Bus' },
    { page: 5, type: 'trace_and_color', label: 'Train', description: 'Trace And Color - Train' },
    { page: 6, type: 'trace_and_color', label: 'Plane', description: 'Trace And Color - Plane' },
    { page: 7, type: 'trace_and_color', label: 'Boat', description: 'Trace And Color - Boat' },
    { page: 8, type: 'trace_and_color', label: 'Helicopter', description: 'Trace And Color - Helicopter' },
  ],
  item_count: 8,
}

// Generation status sequence (simulates staged progress)
const STATUS_SEQUENCE = [
  { id: MOCK_WORKBOOK_ID, status: 'generating', progress: 0.05, stage: 'Preparing configuration...' },
  { id: MOCK_WORKBOOK_ID, status: 'generating', progress: 0.10, stage: 'Generating images... (0/?)' },
  { id: MOCK_WORKBOOK_ID, status: 'generating', progress: 0.35, stage: 'Generating images... (5/10)' },
  { id: MOCK_WORKBOOK_ID, status: 'generating', progress: 0.60, stage: 'Generating images... (10/10)' },
  { id: MOCK_WORKBOOK_ID, status: 'generating', progress: 0.65, stage: 'Building page sequence...' },
  { id: MOCK_WORKBOOK_ID, status: 'generating', progress: 0.75, stage: 'Rendering pages to PDF...' },
  { id: MOCK_WORKBOOK_ID, status: 'generating', progress: 0.90, stage: 'Finalizing PDF...' },
  { id: MOCK_WORKBOOK_ID, status: 'ready', progress: 1.0, stage: 'Complete!' },
]

// --- Helpers ---

async function setupAPIMocks(page: Page) {
  let statusCallCount = 0

  // Themes
  await page.route('**/api/v1/themes', async (route: Route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_THEMES) })
  })

  // Create workbook
  await page.route('**/api/v1/workbooks', async (route: Route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(MOCK_WORKBOOK_RESPONSE) })
    } else if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([MOCK_WORKBOOK_RESPONSE]) })
    } else {
      await route.continue()
    }
  })

  // Update workbook (PUT)
  await page.route(`**/api/v1/workbooks/${MOCK_WORKBOOK_ID}`, async (route: Route) => {
    if (route.request().method() === 'PUT') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ...MOCK_WORKBOOK_RESPONSE, status: 'draft' }),
      })
    } else if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_WORKBOOK_RESPONSE) })
    } else {
      await route.continue()
    }
  })

  // Preview
  await page.route(`**/api/v1/workbooks/${MOCK_WORKBOOK_ID}/preview`, async (route: Route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_PREVIEW) })
  })

  // Generate (POST)
  await page.route(`**/api/v1/workbooks/${MOCK_WORKBOOK_ID}/generate`, async (route: Route) => {
    statusCallCount = 0
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ id: MOCK_WORKBOOK_ID, status: 'generating', progress: 0.0, stage: null }),
    })
  })

  // Status (polled — returns staged responses)
  await page.route(`**/api/v1/workbooks/${MOCK_WORKBOOK_ID}/status`, async (route: Route) => {
    const idx = Math.min(statusCallCount, STATUS_SEQUENCE.length - 1)
    statusCallCount++
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(STATUS_SEQUENCE[idx]) })
  })

  // View (inline PDF) — return a minimal PDF
  await page.route(`**/api/v1/workbooks/${MOCK_WORKBOOK_ID}/view`, async (route: Route) => {
    // Minimal PDF header (enough to verify the iframe loads)
    await route.fulfill({
      status: 200,
      contentType: 'application/pdf',
      headers: { 'Content-Disposition': 'inline; filename="Test_Workbook.pdf"' },
      body: Buffer.from('%PDF-1.4 minimal'),
    })
  })

  // Download
  await page.route(`**/api/v1/workbooks/${MOCK_WORKBOOK_ID}/download`, async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/pdf',
      headers: { 'Content-Disposition': 'attachment; filename="Test_Workbook.pdf"' },
      body: Buffer.from('%PDF-1.4 minimal'),
    })
  })
}

/**
 * Navigate from Step 1 to Step 3 (the Generate step).
 * Selects a theme, configures items, and clicks through to Step 4.
 */
async function navigateToStep3(page: Page) {
  await page.goto(BASE_URL)
  await page.waitForSelector('.workbook-builder', { timeout: 5000 })

  // Step 1: Select theme
  await page.locator('.themes-grid').waitFor({ state: 'visible' })
  await page.locator('.themes-grid > *').first().click()

  // Step 1 → Step 2
  await page.locator('.nav-btn.primary').click()

  // Step 2: Config is auto-filled from theme selection — just proceed
  await page.waitForTimeout(300)

  // Step 2 → Step 3 (Activities)
  await page.locator('.nav-btn.primary').click()
  await page.waitForTimeout(300)

  // Step 3 → Step 4 (Generate)
  await page.locator('.nav-btn.primary').click()
  await page.waitForTimeout(500)
}

// --- Tests ---

test.describe('WorkbookBuilder Step 3 — Preview & Generate', () => {
  test.beforeEach(async ({ page }) => {
    await setupAPIMocks(page)
  })

  test.describe('Page Thumbnail Gallery', () => {
    test('should display thumbnail gallery with page cards', async ({ page }) => {
      await navigateToStep3(page)

      const gallery = page.locator('.thumbnail-gallery')
      await expect(gallery).toBeVisible()

      const cards = page.locator('.page-card')
      const count = await cards.count()
      expect(count).toBeGreaterThanOrEqual(2) // cover + at least 1 activity
      expect(count).toBeLessThanOrEqual(9)    // cover + max 8
    })

    test('first card should be the cover page', async ({ page }) => {
      await navigateToStep3(page)

      const firstCard = page.locator('.page-card').first()
      await expect(firstCard).toHaveClass(/type-cover/)

      const badge = firstCard.locator('.page-badge')
      await expect(badge).toHaveText('1')
    })

    test('should display total page count', async ({ page }) => {
      await navigateToStep3(page)

      const count = page.locator('.gallery-count')
      await expect(count).toContainText('pages')
    })

    test('clicking a card should open lightbox', async ({ page }) => {
      await navigateToStep3(page)

      // Click second card (activity page)
      await page.locator('.page-card').nth(1).click()

      const lightbox = page.locator('.lightbox-overlay')
      await expect(lightbox).toBeVisible()

      const label = page.locator('.lightbox-label')
      await expect(label).toBeVisible()

      // Close lightbox
      await page.locator('.lightbox-close').click()
      await expect(lightbox).not.toBeVisible()
    })

    test('lightbox should close when clicking overlay', async ({ page }) => {
      await navigateToStep3(page)

      await page.locator('.page-card').nth(0).click()
      const lightbox = page.locator('.lightbox-overlay')
      await expect(lightbox).toBeVisible()

      // Click outside the card (on overlay)
      await lightbox.click({ position: { x: 10, y: 10 } })
      await expect(lightbox).not.toBeVisible()
    })
  })

  test.describe('Activity Mix Adjustment', () => {
    test('should display ActivityMixer in Step 3', async ({ page }) => {
      await navigateToStep3(page)

      // There should be two ActivityMixer instances: one in Step 3 (Activities) and one in Step 4
      // We're on Step 4, so the visible one should be in the generate-section
      const mixer = page.locator('.generate-section .activity-mixer')
      await expect(mixer).toBeVisible()
    })

    test('should show activity rows with +/- buttons', async ({ page }) => {
      await navigateToStep3(page)

      const rows = page.locator('.generate-section .activity-row')
      const count = await rows.count()
      expect(count).toBeGreaterThan(0)

      // Each row should have increment/decrement buttons
      const buttons = page.locator('.generate-section .count-btn')
      expect(await buttons.count()).toBeGreaterThan(0)
    })

    test('should show total page count', async ({ page }) => {
      await navigateToStep3(page)

      const total = page.locator('.generate-section .mixer-total')
      await expect(total).toBeVisible()
      await expect(total).toContainText('Total')
    })
  })

  test.describe('Summary Card', () => {
    test('should display summary card with workbook details', async ({ page }) => {
      await navigateToStep3(page)

      const card = page.locator('.summary-card')
      await expect(card).toBeVisible()

      await expect(card.locator('h3')).toHaveText('Summary')
      await expect(card).toContainText('Theme')
      await expect(card).toContainText('Title')
      await expect(card).toContainText('Age Range')
    })
  })

  test.describe('Generation with Staged Progress', () => {
    test('should show Generate PDF button', async ({ page }) => {
      await navigateToStep3(page)

      const btn = page.locator('.generate-btn')
      await expect(btn).toBeVisible()
      await expect(btn).toContainText('Generate PDF')
    })

    test('clicking Generate should show stage progress indicator', async ({ page }) => {
      await navigateToStep3(page)

      await page.locator('.generate-btn').click()

      // Wait for the progress stages to appear
      const stages = page.locator('.progress-stages')
      await expect(stages).toBeVisible({ timeout: 3000 })

      // Should have 5 stage dots
      const dots = page.locator('.stage-dot')
      await expect(dots).toHaveCount(5)
    })

    test('stage dots should have labels', async ({ page }) => {
      await navigateToStep3(page)
      await page.locator('.generate-btn').click()

      await page.locator('.progress-stages').waitFor({ state: 'visible' })

      const labels = page.locator('.stage-label')
      const count = await labels.count()
      expect(count).toBe(5)

      // Check label text
      await expect(labels.nth(0)).toHaveText('Prepare')
      await expect(labels.nth(1)).toHaveText('Images')
      await expect(labels.nth(2)).toHaveText('Sequence')
      await expect(labels.nth(3)).toHaveText('Render')
      await expect(labels.nth(4)).toHaveText('Finalize')
    })

    test('progress text should show current stage description', async ({ page }) => {
      await navigateToStep3(page)
      await page.locator('.generate-btn').click()

      const progressText = page.locator('.progress-text')
      await expect(progressText).toBeVisible({ timeout: 3000 })
    })

    test('should transition to ready state with success message', async ({ page }) => {
      await navigateToStep3(page)
      await page.locator('.generate-btn').click()

      // Wait for generation to complete (mock returns 'ready' after 8 polls)
      const readySection = page.locator('.generation-ready')
      await expect(readySection).toBeVisible({ timeout: 15000 })
      await expect(readySection).toContainText('PDF generated successfully')
    })

    test('should show Preview PDF and Download buttons when ready', async ({ page }) => {
      await navigateToStep3(page)
      await page.locator('.generate-btn').click()

      await page.locator('.generation-ready').waitFor({ state: 'visible', timeout: 15000 })

      const previewBtn = page.locator('.preview-pdf-btn')
      await expect(previewBtn).toBeVisible()
      await expect(previewBtn).toHaveText('Preview PDF')

      const downloadBtn = page.locator('.generation-ready .download-btn')
      await expect(downloadBtn).toBeVisible()
      await expect(downloadBtn).toHaveText('Download PDF')
    })

    test('should show Regenerate button after completion', async ({ page }) => {
      await navigateToStep3(page)
      await page.locator('.generate-btn').click()

      await page.locator('.generation-ready').waitFor({ state: 'visible', timeout: 15000 })

      const btn = page.locator('.generate-btn')
      await expect(btn).toContainText('Regenerate')
    })
  })

  test.describe('PDF Viewer', () => {
    test('clicking Preview PDF should open the viewer', async ({ page }) => {
      await navigateToStep3(page)

      // Generate first
      await page.locator('.generate-btn').click()
      await page.locator('.generation-ready').waitFor({ state: 'visible', timeout: 15000 })

      // Click Preview PDF
      await page.locator('.preview-pdf-btn').click()

      const viewer = page.locator('.pdf-viewer')
      await expect(viewer).toBeVisible()

      // Should have toolbar
      const toolbar = page.locator('.pdf-toolbar')
      await expect(toolbar).toBeVisible()
      await expect(toolbar).toContainText('PDF Preview')
    })

    test('PDF viewer should have download and close buttons', async ({ page }) => {
      await navigateToStep3(page)
      await page.locator('.generate-btn').click()
      await page.locator('.generation-ready').waitFor({ state: 'visible', timeout: 15000 })
      await page.locator('.preview-pdf-btn').click()

      const downloadBtn = page.locator('.pdf-action-btn.download')
      await expect(downloadBtn).toBeVisible()
      await expect(downloadBtn).toContainText('Download')

      const closeBtn = page.locator('.pdf-action-btn.close')
      await expect(closeBtn).toBeVisible()
      await expect(closeBtn).toContainText('Close')
    })

    test('clicking Close should hide the PDF viewer', async ({ page }) => {
      await navigateToStep3(page)
      await page.locator('.generate-btn').click()
      await page.locator('.generation-ready').waitFor({ state: 'visible', timeout: 15000 })
      await page.locator('.preview-pdf-btn').click()

      const viewer = page.locator('.pdf-viewer')
      await expect(viewer).toBeVisible()

      await page.locator('.pdf-action-btn.close').click()
      await expect(viewer).not.toBeVisible()
    })

    test('PDF viewer should contain an iframe', async ({ page }) => {
      await navigateToStep3(page)
      await page.locator('.generate-btn').click()
      await page.locator('.generation-ready').waitFor({ state: 'visible', timeout: 15000 })
      await page.locator('.preview-pdf-btn').click()

      const iframe = page.locator('.pdf-frame')
      await expect(iframe).toBeVisible()

      // iframe src should point to the view endpoint
      const src = await iframe.getAttribute('src')
      expect(src).toContain('/view')
    })
  })

  test.describe('WorkbookPreview component', () => {
    test('should display WorkbookPreview in left column', async ({ page }) => {
      await navigateToStep3(page)

      const preview = page.locator('.preview-section .workbook-preview')
      await expect(preview).toBeVisible()
    })

    test('should show activity breakdown bars', async ({ page }) => {
      await navigateToStep3(page)

      const bars = page.locator('.breakdown-row')
      await expect(bars.first()).toBeVisible({ timeout: 3000 })
      const count = await bars.count()
      expect(count).toBeGreaterThan(0)
    })
  })

  test.describe('Screenshots', () => {
    test('capture Step 3 initial state', async ({ page }) => {
      await navigateToStep3(page)
      await page.waitForTimeout(1000)
      await page.screenshot({
        path: 'e2e/screenshots/step3-preview-generate.png',
        fullPage: true,
      })
    })

    test('capture Step 3 during generation', async ({ page }) => {
      await navigateToStep3(page)
      await page.locator('.generate-btn').click()
      // Wait for stage indicator to appear
      await page.locator('.progress-stages').waitFor({ state: 'visible', timeout: 3000 })
      await page.screenshot({
        path: 'e2e/screenshots/step3-generating.png',
        fullPage: true,
      })
    })

    test('capture Step 3 with PDF viewer', async ({ page }) => {
      await navigateToStep3(page)
      await page.locator('.generate-btn').click()
      await page.locator('.generation-ready').waitFor({ state: 'visible', timeout: 15000 })
      await page.locator('.preview-pdf-btn').click()
      await page.waitForTimeout(500)
      await page.screenshot({
        path: 'e2e/screenshots/step3-pdf-viewer.png',
        fullPage: true,
      })
    })
  })
})
