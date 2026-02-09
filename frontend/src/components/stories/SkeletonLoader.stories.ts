import type { Meta, StoryObj } from '@storybook/vue3'
import SkeletonLoader from '../SkeletonLoader.vue'

const meta: Meta<typeof SkeletonLoader> = {
  title: 'Atoms/SkeletonLoader',
  component: SkeletonLoader,
  tags: ['autodocs'],
}
export default meta
type Story = StoryObj<typeof SkeletonLoader>

export const Card: Story = {
  args: { variant: 'card' },
}

export const Row: Story = {
  args: { variant: 'row' },
}

export const CardGrid: Story = {
  render: () => ({
    components: { SkeletonLoader },
    template: `
      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; max-width: 900px;">
        <SkeletonLoader variant="card" />
        <SkeletonLoader variant="card" />
        <SkeletonLoader variant="card" />
        <SkeletonLoader variant="card" />
        <SkeletonLoader variant="card" />
        <SkeletonLoader variant="card" />
      </div>
    `,
  }),
}

export const RowList: Story = {
  render: () => ({
    components: { SkeletonLoader },
    template: `
      <div style="display: flex; flex-direction: column; gap: 12px; max-width: 600px;">
        <SkeletonLoader variant="row" />
        <SkeletonLoader variant="row" />
        <SkeletonLoader variant="row" />
        <SkeletonLoader variant="row" />
      </div>
    `,
  }),
}
