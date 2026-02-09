import type { StorybookConfig } from '@storybook/vue3-vite'
import { dirname, join } from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const config: StorybookConfig = {
  stories: ['../src/**/*.stories.@(js|jsx|ts|tsx)'],

  addons: [
    '@storybook/addon-docs',
    '@storybook/addon-a11y',
  ],

  framework: {
    name: '@storybook/vue3-vite',
    options: {},
  },

  docs: {
    autodocs: true,
  },

  typescript: {
    check: false,
  },

  core: {
    disableTelemetry: true,
  },

  async viteFinal(viteConfig) {
    viteConfig.resolve = viteConfig.resolve || {}
    viteConfig.resolve.alias = viteConfig.resolve.alias || {}

    if (Array.isArray(viteConfig.resolve.alias)) {
      viteConfig.resolve.alias.push({
        find: '@',
        replacement: join(__dirname, '../src'),
      })
    } else {
      (viteConfig.resolve.alias as Record<string, string>)['@'] = join(__dirname, '../src')
    }

    return viteConfig
  },
}

export default config
