import type { Meta, StoryObj } from '@storybook/vue3'
import App from '../../App.vue'

const meta: Meta<typeof App> = {
  title: 'Pages/App',
  component: App,
  tags: ['autodocs'],
  parameters: {
    layout: 'fullscreen',
  },
}
export default meta
type Story = StoryObj<typeof App>

export const Default: Story = {}
