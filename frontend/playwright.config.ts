/**
 * Project001 (Coloring Book) Playwright E2E Configuration
 * Extends shared @genesis/playwright-config
 *
 * Uses projectSlug for dynamic port resolution via getProjectPorts()
 * Calculated ports: backend=10159, frontend=20159, websocket=25159
 */
import { createPlaywrightConfig, getProjectPorts } from '@genesis/playwright-config'

const PROJECT_SLUG = 'project001'
const ports = getProjectPorts(PROJECT_SLUG)

export default createPlaywrightConfig({
  projectSlug: PROJECT_SLUG,
  testDir: './e2e',
  timeout: 10000,
  webServer: {
    command: `npx vite --port ${ports.frontend}`,
    url: `http://localhost:${ports.frontend}`,
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
})
