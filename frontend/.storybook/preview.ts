import type { Preview } from '@storybook/vue3-vite'

const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    backgrounds: {
      options: {
        light: { name: 'Light', value: '#f5f7fa' },
        dark: { name: 'Dark (App Shell)', value: '#1a1a2e' },
        white: { name: 'White', value: '#ffffff' },
      },
    },
    viewport: {
      viewports: {
        mobile: { name: 'Mobile', styles: { width: '375px', height: '667px' } },
        tablet: { name: 'Tablet', styles: { width: '768px', height: '1024px' } },
        desktop: { name: 'Desktop', styles: { width: '1280px', height: '720px' } },
        wide: { name: 'Wide', styles: { width: '1920px', height: '1080px' } },
      },
    },
  },

  decorators: [
    (story, context) => {
      const bg = context.globals.backgrounds?.value
      const isDark = bg === '#1a1a2e'
      const style = isDark
        ? 'background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); color: #e0e0e0; min-height: 100vh; padding: 2rem;'
        : 'padding: 2rem;'
      return {
        components: { story },
        template: `<div style="${style}"><story /></div>`,
      }
    },
  ],
}

export default preview
