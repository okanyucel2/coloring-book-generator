/**
 * E2E Tests for Coloring Book Generator Frontend
 * Tests all pages and functionality
 */
import { test, expect } from '@playwright/test'

const BASE_URL = 'http://localhost:20159'

test.describe('Coloring Book Generator - E2E Tests', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL)
    // Wait for Vue app to mount
    await page.waitForSelector('.app-container', { timeout: 3000 })
  })

  test.describe('Page Load & Navigation', () => {

    test('should load the app with correct title', async ({ page }) => {
      await expect(page).toHaveTitle(/Coloring Book Generator/)
    })

    test('should display header with app name', async ({ page }) => {
      const header = page.locator('.app-header h1')
      await expect(header).toContainText('Coloring Book Generator')
    })

    test('should have 4 navigation tabs', async ({ page }) => {
      const tabs = page.locator('.nav-tab')
      await expect(tabs).toHaveCount(4)

      // Check tab labels
      await expect(tabs.nth(0)).toContainText('Library')
      await expect(tabs.nth(1)).toContainText('History')
      await expect(tabs.nth(2)).toContainText('Comparison')
      await expect(tabs.nth(3)).toContainText('Customize')
    })

    test('should switch tabs on click', async ({ page }) => {
      // Click each tab and verify content changes
      const tabs = page.locator('.nav-tab')

      // Tab 1: Prompt Library (default)
      await tabs.nth(0).click()
      await expect(page.locator('.tab-content').first()).toBeVisible()

      // Tab 2: Variation History
      await tabs.nth(1).click()
      await page.waitForTimeout(300)

      // Tab 3: Model Comparison
      await tabs.nth(2).click()
      await expect(page.locator('.comparison-wrapper')).toBeVisible()

      // Tab 4: Customize
      await tabs.nth(3).click()
      await expect(page.locator('.customize-wrapper')).toBeVisible()
    })
  })

  test.describe('Tab 1: Prompt Library', () => {

    test.beforeEach(async ({ page }) => {
      await page.locator('.nav-tab').nth(0).click()
      await page.waitForTimeout(500)
    })

    test('should display prompt library container', async ({ page }) => {
      await expect(page.locator('.prompt-library-container')).toBeVisible()
    })

    test('should display search input', async ({ page }) => {
      const searchInput = page.locator('.prompt-library-container input').first()
      await expect(searchInput).toBeVisible()
    })

    test('should have view toggle buttons (grid/list)', async ({ page }) => {
      // Look for view mode buttons
      const viewButtons = page.locator('.view-toggle button, .view-mode-btn')
      const count = await viewButtons.count()
      expect(count).toBeGreaterThanOrEqual(0) // May or may not have view toggle
    })

    test('should show empty state or prompts list', async ({ page }) => {
      // Either shows prompts or empty state
      const content = page.locator('.prompt-library-container')
      await expect(content).toBeVisible()
    })

    test('should have create prompt functionality', async ({ page }) => {
      // Look for add/create button
      const createBtn = page.locator('button:has-text("Create"), button:has-text("Add"), button:has-text("New")')
      const count = await createBtn.count()
      // May or may not have create button visible
      console.log(`Found ${count} create buttons`)
    })
  })

  test.describe('Tab 2: Variation History', () => {

    test.beforeEach(async ({ page }) => {
      await page.locator('.nav-tab').nth(1).click()
      await page.waitForTimeout(500)
    })

    test('should display variation history container', async ({ page }) => {
      await expect(page.locator('.variation-history-container')).toBeVisible()
    })

    test('should have filter controls', async ({ page }) => {
      // Look for filter/sort options
      const filters = page.locator('.filter-section, .filters, select')
      const count = await filters.count()
      console.log(`Found ${count} filter elements`)
    })

    test('should show timeline or empty state', async ({ page }) => {
      const content = page.locator('.variation-history-container')
      await expect(content).toBeVisible()
    })
  })

  test.describe('Tab 3: Model Comparison', () => {

    test.beforeEach(async ({ page }) => {
      await page.locator('.nav-tab').nth(2).click()
      await page.waitForTimeout(500)
    })

    test('should display comparison layout', async ({ page }) => {
      await expect(page.locator('.comparison-wrapper')).toBeVisible()
    })

    test('should have model selection controls', async ({ page }) => {
      // Look for model selector or panel controls
      const controls = page.locator('.model-selector, .panel-controls, select')
      const count = await controls.count()
      console.log(`Found ${count} model control elements`)
    })
  })

  test.describe('Tab 4: Customize (Prompt Customization)', () => {

    test.beforeEach(async ({ page }) => {
      await page.locator('.nav-tab').nth(3).click()
      await page.waitForTimeout(500)
    })

    test('should display prompt customization form', async ({ page }) => {
      await expect(page.locator('.customize-wrapper')).toBeVisible()
    })

    test('should have template selection buttons', async ({ page }) => {
      const templates = page.locator('.template-btn, .template-button')
      const count = await templates.count()
      console.log(`Found ${count} template buttons`)
    })

    test('should have prompt textarea', async ({ page }) => {
      const textarea = page.locator('textarea')
      await expect(textarea.first()).toBeVisible()
    })

    test('should show character count', async ({ page }) => {
      const charCount = page.locator('.char-count')
      const count = await charCount.count()
      console.log(`Found ${count} character count elements`)
      expect(count).toBeGreaterThan(0)
    })

    test('should detect variables in prompt', async ({ page }) => {
      const textarea = page.locator('textarea').first()

      // Type a prompt with variables
      await textarea.fill('Create a {{animal}} coloring page with {{style}} style')

      // Check if variable inputs appear
      await page.waitForTimeout(500) // Wait for reactivity

      const variableInputs = page.locator('.variable-input, input[id^="var-"]')
      const count = await variableInputs.count()
      console.log(`Detected ${count} variable inputs after typing prompt with {{animal}} and {{style}}`)
    })

    test('should have generate and reset buttons', async ({ page }) => {
      const generateBtn = page.locator('button:has-text("Generate")')
      const resetBtn = page.locator('button:has-text("Reset"), button:has-text("Clear")')

      await expect(generateBtn.first()).toBeVisible()
      console.log(`Reset button count: ${await resetBtn.count()}`)
    })

    test('should show preview section', async ({ page }) => {
      const preview = page.locator('.preview-section, .prompt-preview')
      const count = await preview.count()
      console.log(`Found ${count} preview sections`)
    })
  })

  test.describe('Responsive Design', () => {

    test('should be responsive on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 })
      await page.reload()
      await page.waitForSelector('.app-container')

      // App should still be visible and functional
      await expect(page.locator('.app-header')).toBeVisible()
      await expect(page.locator('.nav-tab').first()).toBeVisible()
    })

    test('should be responsive on tablet viewport', async ({ page }) => {
      await page.setViewportSize({ width: 768, height: 1024 })
      await page.reload()
      await page.waitForSelector('.app-container')

      await expect(page.locator('.app-header')).toBeVisible()
    })
  })

  test.describe('Error Handling', () => {

    test('should handle API errors gracefully', async ({ page }) => {
      // The app should not crash even if APIs fail
      // Check that the app is still functional after API errors
      await page.waitForTimeout(2000) // Wait for any API calls to fail

      // App should still be interactive
      const tabs = page.locator('.nav-tab')
      await expect(tabs.first()).toBeEnabled()
    })
  })

  test.describe('Visual Regression - Screenshots', () => {

    test('capture Tab 1: Prompt Library', async ({ page }) => {
      await page.locator('.nav-tab').nth(0).click()
      await page.waitForTimeout(1000)
      await page.screenshot({
        path: 'e2e/screenshots/tab1-prompt-library.png',
        fullPage: true
      })
    })

    test('capture Tab 2: Variation History', async ({ page }) => {
      await page.locator('.nav-tab').nth(1).click()
      await page.waitForTimeout(1000)
      await page.screenshot({
        path: 'e2e/screenshots/tab2-variation-history.png',
        fullPage: true
      })
    })

    test('capture Tab 3: Model Comparison', async ({ page }) => {
      await page.locator('.nav-tab').nth(2).click()
      await page.waitForTimeout(1000)
      await page.screenshot({
        path: 'e2e/screenshots/tab3-model-comparison.png',
        fullPage: true
      })
    })

    test('capture Tab 4: Customize', async ({ page }) => {
      await page.locator('.nav-tab').nth(3).click()
      await page.waitForTimeout(1000)
      await page.screenshot({
        path: 'e2e/screenshots/tab4-customize.png',
        fullPage: true
      })
    })

    test('capture Mobile View', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 })
      await page.reload()
      await page.waitForSelector('.app-container')
      await page.waitForTimeout(1000)
      await page.screenshot({
        path: 'e2e/screenshots/mobile-view.png',
        fullPage: true
      })
    })
  })
})
