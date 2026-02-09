import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import type { StorybookConfig } from '@storybook/vue3-vite'

const __dirname = dirname(fileURLToPath(import.meta.url))

const config: StorybookConfig = {
  stories: ['../src/components/stories/**/*.stories.@(js|jsx|ts|tsx)'],
  addons: [
    getAbsolutePath('@storybook/addon-docs'),
    getAbsolutePath('@storybook/addon-a11y'),
  ],

  framework: {
    name: getAbsolutePath('@storybook/vue3-vite'),
    options: {},
  },

  viteFinal: async (config) => {
    // Note: Do NOT add vue() plugin here — @storybook/vue3-vite already includes it
    config.resolve = config.resolve || {}
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': resolve(__dirname, '../src'),
    }
    return config
  },
}

export default config

function getAbsolutePath(value: string): any {
  return dirname(fileURLToPath(import.meta.resolve(`${value}/package.json`)))
}
