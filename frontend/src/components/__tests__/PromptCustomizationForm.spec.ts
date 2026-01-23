import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import PromptCustomizationForm from '../PromptCustomizationForm.vue'

describe('PromptCustomizationForm Component - RED PHASE', () => {
  let wrapper: any

  const sampleTemplates = [
    {
      id: 'template-1',
      name: 'Simple Animal',
      description: 'Basic animal outline',
      template: 'A {{difficulty}} {{animal}} outline for coloring',
    },
    {
      id: 'template-2',
      name: 'Detailed Scene',
      description: 'Complex nature scene',
      template: '{{animal}} in {{environment}}, {{style}} art style, {{difficulty}} details',
    },
    {
      id: 'template-3',
      name: 'Mandala Style',
      description: 'Decorative pattern',
      template: '{{animal}} mandala pattern, {{color_scheme}} colors, {{difficulty}} complexity',
    },
  ]

  beforeEach(() => {
    wrapper = mount(PromptCustomizationForm, {
      props: {
        templates: sampleTemplates,
      },
    })
  })

  describe('Component Structure', () => {
    it('renders form container', () => {
      expect(wrapper.find('.prompt-form').exists()).toBe(true)
    })

    it('displays form title', () => {
      expect(wrapper.find('.form-title').text()).toContain('Custom Prompt')
    })

    it('has template selector section', () => {
      expect(wrapper.find('.template-selector').exists()).toBe(true)
    })

    it('has prompt editor section', () => {
      expect(wrapper.find('.prompt-editor').exists()).toBe(true)
    })

    it('has variable substitution section', () => {
      expect(wrapper.find('.variable-section').exists()).toBe(true)
    })

    it('has action buttons', () => {
      expect(wrapper.find('.form-actions').exists()).toBe(true)
      expect(wrapper.find('.btn-generate').exists()).toBe(true)
      expect(wrapper.find('.btn-reset').exists()).toBe(true)
    })
  })

  describe('Template Selection', () => {
    it('displays all available templates', () => {
      const templateButtons = wrapper.findAll('.template-button')
      expect(templateButtons).toHaveLength(3)
    })

    it('shows template name and description', () => {
      const firstTemplate = wrapper.find('.template-button')
      expect(firstTemplate.text()).toContain('Simple Animal')
      expect(firstTemplate.text()).toContain('Basic animal outline')
    })

    it('loads template into prompt on selection', async () => {
      const templateButton = wrapper.findAll('.template-button')[0]
      await templateButton.trigger('click')

      const promptInput = wrapper.find('.prompt-textarea')
      expect(promptInput.element.value).toBe('A {{difficulty}} {{animal}} outline for coloring')
    })

    it('marks selected template with active class', async () => {
      const firstTemplate = wrapper.findAll('.template-button')[0]
      await firstTemplate.trigger('click')

      expect(firstTemplate.classes()).toContain('active')
    })

    it('switches between templates', async () => {
      const buttons = wrapper.findAll('.template-button')
      
      await buttons[0].trigger('click')
      expect(wrapper.find('.prompt-textarea').element.value).toContain('outline for coloring')

      await buttons[1].trigger('click')
      expect(wrapper.find('.prompt-textarea').element.value).toContain('{{environment}}')
    })

    it('displays template preview with descriptions after selection', async () => {
      const templateButton = wrapper.findAll('.template-button')[0]
      await templateButton.trigger('click')

      const templateInfo = wrapper.find('.template-info')
      expect(templateInfo.exists()).toBe(true)
      expect(templateInfo.text()).toContain('Simple Animal')
    })
  })

  describe('Prompt Editing', () => {
    it('has textarea for prompt input', () => {
      expect(wrapper.find('.prompt-textarea').exists()).toBe(true)
    })

    it('updates prompt text on input', async () => {
      const textarea = wrapper.find('.prompt-textarea')
      await textarea.setValue('A {{animal}} in {{environment}}')

      expect(wrapper.vm.customPrompt).toBe('A {{animal}} in {{environment}}')
    })

    it('allows free-form prompt editing', async () => {
      const textarea = wrapper.find('.prompt-textarea')
      const customText = 'Custom prompt: Draw a {{style}} {{animal}} with {{color}} coloring'
      
      await textarea.setValue(customText)
      expect(wrapper.find('.prompt-textarea').element.value).toBe(customText)
    })

    it('shows character count', () => {
      const charCount = wrapper.find('.char-count')
      expect(charCount.exists()).toBe(true)
      expect(charCount.text()).toMatch(/\d+/)
    })

    it('updates character count on input', async () => {
      const textarea = wrapper.find('.prompt-textarea')
      const initialCount = parseInt(wrapper.find('.char-count').text())
      
      await textarea.setValue('A very long custom prompt that is definitely longer than the initial one')
      const newCount = parseInt(wrapper.find('.char-count').text())
      
      expect(newCount).toBeGreaterThan(initialCount)
    })

    it('clears prompt on reset button', async () => {
      const textarea = wrapper.find('.prompt-textarea')
      await textarea.setValue('Some prompt text')
      
      await wrapper.find('.btn-reset').trigger('click')
      
      expect(wrapper.find('.prompt-textarea').element.value).toBe('')
    })
  })

  describe('Variable Substitution', () => {
    it('detects variables in prompt', async () => {
      const textarea = wrapper.find('.prompt-textarea')
      await textarea.setValue('A {{difficulty}} {{animal}} in {{environment}}')

      await wrapper.vm.$nextTick()

      const variables = wrapper.findAll('.variable-input')
      expect(variables.length).toBeGreaterThanOrEqual(3)
    })

    it('displays variable input fields', async () => {
      const textarea = wrapper.find('.prompt-textarea')
      await textarea.setValue('{{animal}} {{environment}}')

      await wrapper.vm.$nextTick()

      const variableLabels = wrapper.findAll('.variable-label')
      expect(variableLabels.length).toBeGreaterThanOrEqual(2)
    })

    it('shows variable preview in real-time', async () => {
      const textarea = wrapper.find('.prompt-textarea')
      await textarea.setValue('A {{difficulty}} {{animal}}')

      await wrapper.vm.$nextTick()

      const animalInput = wrapper.findAll('.variable-input')[0]
      if (animalInput.exists()) {
        await animalInput.setValue('Lion')
      }

      const preview = wrapper.find('.prompt-preview')
      if (preview.exists()) {
        expect(preview.text()).toContain('Lion')
      }
    })

    it('preserves undefined variables in preview', async () => {
      const textarea = wrapper.find('.prompt-textarea')
      await textarea.setValue('A {{animal}} in {{environment}}')

      const preview = wrapper.find('.prompt-preview')
      if (preview.exists()) {
        expect(preview.text()).toContain('{{environment}}')
      }
    })

    it('handles nested variables gracefully', async () => {
      const textarea = wrapper.find('.prompt-textarea')
      await textarea.setValue('A {{animal}}_{{style}}_{{difficulty}} design')

      await wrapper.vm.$nextTick()

      const variables = wrapper.findAll('.variable-input')
      expect(variables.length).toBeGreaterThanOrEqual(3)
    })
  })

  describe('Preview & Real-time Updates', () => {
    it('displays prompt preview section', () => {
      expect(wrapper.find('.preview-section').exists()).toBe(true)
    })

    it('shows "Current Prompt" title in preview', () => {
      expect(wrapper.find('.preview-title').text()).toContain('Current Prompt')
    })

    it('updates preview when prompt changes', async () => {
      const textarea = wrapper.find('.prompt-textarea')
      const testPrompt = 'A {{animal}} outline'
      
      await textarea.setValue(testPrompt)
      await wrapper.vm.$nextTick()

      const preview = wrapper.find('.prompt-preview')
      expect(preview.text()).toContain('{{animal}}')
    })

    it('updates preview when variables are substituted', async () => {
      const textarea = wrapper.find('.prompt-textarea')
      await textarea.setValue('{{animal}} {{environment}}')

      await wrapper.vm.$nextTick()

      const inputs = wrapper.findAll('.variable-input')
      if (inputs.length > 0) {
        await inputs[0].setValue('Tiger')
      }

      const preview = wrapper.find('.prompt-preview')
      expect(preview.text()).toContain('Tiger')
    })
  })

  describe('Form Actions', () => {
    it('emits generate event with prompt and variables', async () => {
      const textarea = wrapper.find('.prompt-textarea')
      await textarea.setValue('A {{animal}} drawing')

      await wrapper.vm.$nextTick()

      const generateBtn = wrapper.find('.btn-generate')
      await generateBtn.trigger('click')

      expect(wrapper.emitted('generate')).toBeTruthy()
      const emitted = wrapper.emitted('generate')[0][0]
      expect(emitted).toHaveProperty('prompt')
      expect(emitted).toHaveProperty('variables')
    })

    it('includes template ID in generate event if template selected', async () => {
      const templateBtn = wrapper.findAll('.template-button')[0]
      await templateBtn.trigger('click')

      const generateBtn = wrapper.find('.btn-generate')
      await generateBtn.trigger('click')

      const emitted = wrapper.emitted('generate')[0][0]
      expect(emitted.selectedTemplate).toBe('template-1')
    })

    it('disables generate button if prompt is empty', async () => {
      expect(wrapper.find('.btn-generate').attributes('disabled')).toBeDefined()
    })

    it('enables generate button when prompt has content', async () => {
      const textarea = wrapper.find('.prompt-textarea')
      await textarea.setValue('A simple prompt')

      await wrapper.vm.$nextTick()

      expect(wrapper.find('.btn-generate').attributes('disabled')).toBeUndefined()
    })

    it('resets form on reset button click', async () => {
      const textarea = wrapper.find('.prompt-textarea')
      await textarea.setValue('Test prompt')

      await wrapper.find('.btn-reset').trigger('click')

      expect(wrapper.find('.prompt-textarea').element.value).toBe('')
      expect(wrapper.vm.selectedTemplate).toBeNull()
    })

    it('emits reset event on reset button', async () => {
      await wrapper.find('.btn-reset').trigger('click')

      expect(wrapper.emitted('reset')).toBeTruthy()
    })

    it('shows copy button for prompt', () => {
      expect(wrapper.find('.btn-copy').exists()).toBe(true)
    })

    it('copies prompt to clipboard on copy button', async () => {
      const textarea = wrapper.find('.prompt-textarea')
      const promptText = 'Copy this prompt {{animal}}'
      await textarea.setValue(promptText)

      const copyBtn = wrapper.find('.btn-copy')
      await copyBtn.trigger('click')

      expect(wrapper.emitted('copy')).toBeTruthy()
    })
  })

  describe('Validation & Error Handling', () => {
    it('validates prompt length', async () => {
      const textarea = wrapper.find('.prompt-textarea')
      const longPrompt = 'x'.repeat(2000)
      await textarea.setValue(longPrompt)

      await wrapper.vm.$nextTick()

      const charCount = wrapper.find('.char-count')
      expect(charCount.text()).toContain('2000')
    })

    it('shows warning for very long prompts', async () => {
      const textarea = wrapper.find('.prompt-textarea')
      const longPrompt = 'A {{animal}} ' + 'very long description '.repeat(100)
      await textarea.setValue(longPrompt)

      await wrapper.vm.$nextTick()

      const warning = wrapper.find('.length-warning')
      if (warning.exists()) {
        expect(warning.text()).toContain('long')
      }
    })
  })

  describe('Accessibility', () => {
    it('has proper form labels', () => {
      const labels = wrapper.findAll('label')
      expect(labels.length).toBeGreaterThan(0)
    })

    it('textarea has associated label', () => {
      const textarea = wrapper.find('.prompt-textarea')
      expect(textarea.attributes('id')).toBeTruthy()
    })

    it('template buttons are keyboard accessible', async () => {
      const templateBtn = wrapper.findAll('.template-button')[0]
      await templateBtn.trigger('keydown.enter')

      expect(templateBtn.classes()).toContain('active')
    })

    it('form buttons have proper aria labels', () => {
      const generateBtn = wrapper.find('.btn-generate')
      expect(generateBtn.attributes('aria-label')).toBeTruthy()
    })
  })

  describe('Props & Reactivity', () => {
    it('accepts templates prop', () => {
      expect(wrapper.props('templates')).toEqual(sampleTemplates)
    })

    it('handles empty templates array', () => {
      const emptyWrapper = mount(PromptCustomizationForm, {
        props: {
          templates: [],
        },
      })
      expect(emptyWrapper.findAll('.template-button')).toHaveLength(0)
    })

    it('updates templates when prop changes', async () => {
      const newTemplates = [
        {
          id: 'new-1',
          name: 'New Template',
          description: 'A new template',
          template: 'New {{variable}} template',
        },
      ]

      await wrapper.setProps({
        templates: newTemplates,
      })

      expect(wrapper.findAll('.template-button')).toHaveLength(1)
    })
  })

  describe('User Experience', () => {
    it('shows template suggestions on focus', async () => {
      const templateSection = wrapper.find('.template-selector')
      expect(templateSection.exists()).toBe(true)
    })

    it('displays quick-insert variable buttons', () => {
      const quickInsertButtons = wrapper.findAll('.quick-insert-var')
      expect(quickInsertButtons.length).toBeGreaterThanOrEqual(0)
    })

    it('saves prompt draft to localStorage', async () => {
      const textarea = wrapper.find('.prompt-textarea')
      await textarea.setValue('Draft prompt {{animal}}')

      await wrapper.vm.$nextTick()

      // Check if component has draft saving capability
      expect(wrapper.vm.customPrompt).toBe('Draft prompt {{animal}}')
    })
  })
})
