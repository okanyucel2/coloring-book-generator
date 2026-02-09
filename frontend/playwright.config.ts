/**
 * Project001 (Coloring Book) Playwright E2E Configuration
 * Extends shared @genesis/playwright-config
 *
 * Uses projectSlug for dynamic port resolution via getProjectPorts()
 * Calculated ports: backend=10159, frontend=20159, websocket=25159
 */
import { createPlaywrightConfig } from '@genesis/playwright-config'

export default createPlaywrightConfig({
  projectSlug: 'project001',
  testDir: './e2e',
  timeout: 10000,
})
