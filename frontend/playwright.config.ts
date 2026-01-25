/**
 * Project001 (Coloring Book) Playwright E2E Configuration
 * Extends shared @genesis/playwright-config
 */
import { createPlaywrightConfig } from '@genesis/playwright-config'

export default createPlaywrightConfig({
  baseURL: 'http://localhost:5174',
})
