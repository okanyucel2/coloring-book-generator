import type { Meta, StoryObj } from '@storybook/vue3'
import ModelOutputPanel from '../ModelOutputPanel.vue'

const meta: Meta<typeof ModelOutputPanel> = {
  title: 'Molecules/ModelOutputPanel',
  component: ModelOutputPanel,
  tags: ['autodocs'],
  argTypes: {
    select: { action: 'select' },
  },
}
export default meta
type Story = StoryObj<typeof ModelOutputPanel>

export const Default: Story = {
  args: {
    modelName: 'Claude 3.5',
    imageUrl: 'https://picsum.photos/seed/default/512/512',
    generationTime: 2.3,
    qualityScore: 0.92,
  },
}

export const HighQuality: Story = {
  args: {
    modelName: 'Claude 3.5',
    imageUrl: 'https://picsum.photos/seed/highquality/512/512',
    generationTime: 1.8,
    qualityScore: 0.95,
  },
}

export const LowQuality: Story = {
  args: {
    modelName: 'GPT-4',
    imageUrl: 'https://picsum.photos/seed/lowquality/512/512',
    generationTime: 4.1,
    qualityScore: 0.45,
  },
}

export const Loading: Story = {
  args: {
    modelName: 'Gemini 2.0',
    imageUrl: '',
    generationTime: 0,
    qualityScore: 0,
  },
}

export const Selected: Story = {
  args: {
    modelName: 'Claude 3.5',
    imageUrl: 'https://picsum.photos/seed/selected/512/512',
    generationTime: 2.1,
    qualityScore: 0.93,
  },
  render: (args) => ({
    components: { ModelOutputPanel },
    setup() {
      return { args }
    },
    template: `
      <div style="border: 2px solid #3b82f6; border-radius: 8px; box-shadow: 0 0 12px rgba(59, 130, 246, 0.4);">
        <ModelOutputPanel v-bind="args" />
      </div>
    `,
  }),
}
