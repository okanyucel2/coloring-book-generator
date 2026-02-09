/**
 * Storybook Preview Configuration
 *
 * Custom dark mode decorator that matches our data-theme="light"
 * attribute pattern (default = dark, no attribute).
 */
import type { Preview } from '@storybook/vue3'
import '../src/assets/design-tokens.css'

const preview: Preview = {
  decorators: [
    // Theme decorator: sets data-theme attribute on <html>
    (story, context) => {
      const theme = context.globals?.theme || 'dark'
      if (theme === 'light') {
        document.documentElement.setAttribute('data-theme', 'light')
      } else {
        document.documentElement.removeAttribute('data-theme')
      }
      return story()
    },
  ],
  parameters: {
    viewport: {
      viewports: {
        mobile: { name: 'Mobile (360x640)', styles: { width: '360px', height: '640px' } },
        tablet: { name: 'Tablet (768x1024)', styles: { width: '768px', height: '1024px' } },
        desktop: { name: 'Desktop (1280x720)', styles: { width: '1280px', height: '720px' } },
        desktopWide: { name: 'Desktop Wide (1920x1080)', styles: { width: '1920px', height: '1080px' } },
      },
      defaultViewport: 'desktop',
    },
    backgrounds: {
      default: 'Dark Shell',
      values: [
        { name: 'Dark Shell', value: '#1a1a2e' },
        { name: 'Light Shell', value: '#f0f2f5' },
        { name: 'White', value: '#ffffff' },
      ],
    },
    a11y: {
      config: {
        rules: [
          { id: 'color-contrast', enabled: true },
          { id: 'landmark-one-main', enabled: false },
          { id: 'page-has-heading-one', enabled: false },
          { id: 'region', enabled: false },
        ],
      },
    },
  },
  globalTypes: {
    theme: {
      name: 'Theme',
      description: 'Toggle dark/light mode',
      defaultValue: 'dark',
      toolbar: {
        icon: 'circlehollow',
        items: [
          { value: 'dark', icon: 'moon', title: 'Dark' },
          { value: 'light', icon: 'sun', title: 'Light' },
        ],
        showName: true,
        dynamicTitle: true,
      },
    },
  },
  tags: ['autodocs'],
}

export default preview
