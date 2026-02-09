import type { Meta, StoryObj } from '@storybook/vue3'
import ConfirmDialog from '../ConfirmDialog.vue'

const meta: Meta<typeof ConfirmDialog> = {
  title: 'Molecules/ConfirmDialog',
  component: ConfirmDialog,
  tags: ['autodocs'],
}
export default meta
type Story = StoryObj<typeof ConfirmDialog>

export const Default: Story = {
  args: {
    visible: true,
    title: 'Confirm Action',
    message: 'Are you sure you want to proceed?',
    confirmText: 'Yes, Continue',
    cancelText: 'Cancel',
    destructive: false,
  },
}

export const Destructive: Story = {
  args: {
    visible: true,
    title: 'Delete Prompt',
    message: 'This action cannot be undone. The prompt will be permanently deleted.',
    confirmText: 'Delete',
    cancelText: 'Keep',
    destructive: true,
  },
}

export const LongMessage: Story = {
  args: {
    visible: true,
    title: 'Clear All History',
    message: 'You are about to clear your entire variation history. This will remove all saved variations, ratings, and notes. This action cannot be undone.',
    confirmText: 'Clear Everything',
    cancelText: 'Cancel',
    destructive: true,
  },
}
