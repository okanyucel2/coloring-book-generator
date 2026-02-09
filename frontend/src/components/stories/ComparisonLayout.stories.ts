import type { Meta, StoryObj } from '@storybook/vue3'
import ComparisonLayout from '../ComparisonLayout.vue'

const meta: Meta<typeof ComparisonLayout> = {
  title: 'Organisms/ComparisonLayout',
  component: ComparisonLayout,
  tags: ['autodocs'],
}
export default meta
type Story = StoryObj<typeof ComparisonLayout>

export const Default: Story = {}

export const WithOutputs: Story = {
  play: async ({ canvasElement }) => {
    const component = canvasElement.__vue_app__?.config.globalProperties
    // Access the component instance to call setModelOutput
    const vm = (canvasElement as any).__vueParentComponent?.exposed
      ?? (canvasElement.querySelector('[data-v-app]') as any)?.__vue_app__

    // Fallback: use DOM-level interaction since setModelOutput is a component method.
    // The render function below handles this via the mounted hook instead.
  },
  render: (args) => ({
    components: { ComparisonLayout },
    setup() {
      const compRef = { value: null as any }
      const onMounted = () => {
        setTimeout(() => {
          if (compRef.value) {
            compRef.value.setModelOutput('claude-3.5', 'https://picsum.photos/seed/claude/512/512')
            compRef.value.setModelOutput('gpt-4', 'https://picsum.photos/seed/gpt4/512/512')
            compRef.value.setModelOutput('gemini-2.0', 'https://picsum.photos/seed/gemini/512/512')
          }
        }, 100)
      }
      return { args, compRef, onMounted }
    },
    template: `
      <ComparisonLayout
        ref="compRef"
        v-bind="args"
        @vue:mounted="onMounted"
      />
    `,
  }),
}
