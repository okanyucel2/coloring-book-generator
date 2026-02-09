import type { Meta, StoryObj } from '@storybook/vue3'
import PromptLibraryUI from '../PromptLibraryUI.vue'

const meta: Meta<typeof PromptLibraryUI> = {
  title: 'Organisms/PromptLibraryUI',
  component: PromptLibraryUI,
  tags: ['autodocs'],
}
export default meta
type Story = StoryObj<typeof PromptLibraryUI>

export const Default: Story = {}
