import type { Meta, StoryObj } from '@storybook/vue3'
import VariationHistoryComparison from '../VariationHistoryComparison.vue'

const meta: Meta<typeof VariationHistoryComparison> = {
  title: 'Organisms/VariationHistoryComparison',
  component: VariationHistoryComparison,
  tags: ['autodocs'],
}
export default meta
type Story = StoryObj<typeof VariationHistoryComparison>

export const Default: Story = {}
