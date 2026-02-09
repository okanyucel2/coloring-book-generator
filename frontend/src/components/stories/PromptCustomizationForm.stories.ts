import type { Meta, StoryObj } from '@storybook/vue3'
import PromptCustomizationForm from '../PromptCustomizationForm.vue'

const meta: Meta<typeof PromptCustomizationForm> = {
  title: 'Molecules/PromptCustomizationForm',
  component: PromptCustomizationForm,
  tags: ['autodocs'],
  argTypes: {
    templates: {
      description: 'Array of prompt templates with {{variable}} placeholders',
      control: 'object',
    },
    onGenerate: { action: 'generate' },
    onReset: { action: 'reset' },
    onCopy: { action: 'copy' },
  },
}

export default meta
type Story = StoryObj<typeof PromptCustomizationForm>

export const Default: Story = {
  args: {
    templates: [
      {
        id: 'animal-simple',
        name: 'Simple Animal',
        description: 'Clean line art of animals for coloring',
        template:
          'A simple coloring book outline of a {{animal}}, black and white line art',
      },
      {
        id: 'nature-scene',
        name: 'Nature Scene',
        description: 'Beautiful nature landscapes',
        template:
          'A coloring book page featuring a {{scene}} with {{elements}}',
      },
      {
        id: 'mandala',
        name: 'Mandala Pattern',
        description: 'Intricate mandala designs',
        template: 'A {{complexity}} mandala pattern with {{theme}} motifs',
      },
      {
        id: 'custom',
        name: 'Custom Prompt',
        description: 'Start from scratch',
        template: '',
      },
    ],
  },
}

export const NoTemplates: Story = {
  args: {
    templates: [],
  },
}

export const SingleTemplate: Story = {
  args: {
    templates: [
      {
        id: 'animal-simple',
        name: 'Simple Animal',
        description: 'Clean line art of animals for coloring',
        template:
          'A simple coloring book outline of a {{animal}}, black and white line art',
      },
    ],
  },
}
