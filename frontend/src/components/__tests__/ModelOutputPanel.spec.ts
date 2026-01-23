import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ModelOutputPanel from '../ModelOutputPanel.vue'

describe('ModelOutputPanel Component - RED PHASE', () => {
  let wrapper: any

  beforeEach(() => {
    wrapper = mount(ModelOutputPanel, {
      props: {
        modelName: 'Gemini',
        imageUrl: 'https://example.com/image.png',
        generationTime: 2.5,
        qualityScore: 0.92,
      },
    })
  })

  describe('Component Structure', () => {
    it('renders model name as header', () => {
      expect(wrapper.find('.model-header').text()).toBe('Gemini')
    })

    it('displays image URL in image element', () => {
      const img = wrapper.find('img.model-image')
      expect(img.attributes('src')).toBe('https://example.com/image.png')
      expect(img.attributes('alt')).toBe('Gemini output')
    })

    it('has container with correct CSS classes', () => {
      expect(wrapper.find('.model-output-panel').exists()).toBe(true)
      expect(wrapper.find('.model-output-panel').classes()).toContain('panel')
    })
  })

  describe('Metadata Display', () => {
    it('displays generation time in seconds', () => {
      const timeText = wrapper.find('.metric-generation-time').text()
      expect(timeText).toContain('2.5')
      expect(timeText).toContain('s')
    })

    it('displays quality score as percentage', () => {
      const scoreText = wrapper.find('.metric-quality-score').text()
      expect(scoreText).toContain('92')
      expect(scoreText).toContain('%')
    })

    it('renders metadata section', () => {
      expect(wrapper.find('.metadata-section').exists()).toBe(true)
    })

    it('formats quality score to 0-100 range', () => {
      const wrapper2 = mount(ModelOutputPanel, {
        props: {
          modelName: 'Imagen',
          imageUrl: 'https://example.com/image2.png',
          generationTime: 1.8,
          qualityScore: 0.75,
        },
      })
      const scoreText = wrapper2.find('.metric-quality-score').text()
      expect(scoreText).toContain('75')
    })
  })

  describe('Visual Indicators', () => {
    it('applies quality-based CSS class to panel', () => {
      // High quality (>0.85) should have premium class
      const wrapper2 = mount(ModelOutputPanel, {
        props: {
          modelName: 'Ultra',
          imageUrl: 'https://example.com/ultra.png',
          generationTime: 3.2,
          qualityScore: 0.95,
        },
      })
      expect(wrapper2.find('.model-output-panel').classes()).toContain('quality-premium')
    })

    it('applies medium quality class for 0.7-0.85 range', () => {
      const wrapper2 = mount(ModelOutputPanel, {
        props: {
          modelName: 'Imagen',
          imageUrl: 'https://example.com/img.png',
          generationTime: 2.0,
          qualityScore: 0.78,
        },
      })
      expect(wrapper2.find('.model-output-panel').classes()).toContain('quality-medium')
    })

    it('applies low quality class for <0.7 range', () => {
      const wrapper2 = mount(ModelOutputPanel, {
        props: {
          modelName: 'Test',
          imageUrl: 'https://example.com/test.png',
          generationTime: 1.5,
          qualityScore: 0.65,
        },
      })
      expect(wrapper2.find('.model-output-panel').classes()).toContain('quality-low')
    })
  })

  describe('Props Reactivity', () => {
    it('updates image URL when prop changes', async () => {
      expect(wrapper.find('img.model-image').attributes('src')).toBe('https://example.com/image.png')
      
      await wrapper.setProps({
        imageUrl: 'https://example.com/new-image.png',
      })
      
      expect(wrapper.find('img.model-image').attributes('src')).toBe('https://example.com/new-image.png')
    })

    it('updates quality score display on prop change', async () => {
      let scoreText = wrapper.find('.metric-quality-score').text()
      expect(scoreText).toContain('92')
      
      await wrapper.setProps({
        qualityScore: 0.88,
      })
      
      scoreText = wrapper.find('.metric-quality-score').text()
      expect(scoreText).toContain('88')
    })

    it('updates generation time on prop change', async () => {
      let timeText = wrapper.find('.metric-generation-time').text()
      expect(timeText).toContain('2.5')
      
      await wrapper.setProps({
        generationTime: 1.9,
      })
      
      timeText = wrapper.find('.metric-generation-time').text()
      expect(timeText).toContain('1.9')
    })
  })

  describe('Selection & Interaction', () => {
    it('emits select event when clicked', async () => {
      await wrapper.find('.model-output-panel').trigger('click')
      expect(wrapper.emitted('select')).toBeTruthy()
    })

    it('includes model name in select event payload', async () => {
      await wrapper.find('.model-output-panel').trigger('click')
      expect(wrapper.emitted('select')[0]).toEqual(['Gemini'])
    })

    it('toggles selected state on click', async () => {
      expect(wrapper.find('.model-output-panel').classes()).not.toContain('selected')
      
      await wrapper.find('.model-output-panel').trigger('click')
      expect(wrapper.find('.model-output-panel').classes()).toContain('selected')
      
      await wrapper.find('.model-output-panel').trigger('click')
      expect(wrapper.find('.model-output-panel').classes()).not.toContain('selected')
    })

    it('updates selected class when prop changes', async () => {
      const wrapper2 = mount(ModelOutputPanel, {
        props: {
          modelName: 'Imagen',
          imageUrl: 'https://example.com/image.png',
          generationTime: 2.0,
          qualityScore: 0.85,
          selected: true,
        },
      })
      expect(wrapper2.find('.model-output-panel').classes()).toContain('selected')
      
      await wrapper2.setProps({
        selected: false,
      })
      
      await wrapper2.vm.$nextTick()
      expect(wrapper2.find('.model-output-panel').classes()).not.toContain('selected')
    })
  })

  describe('Error Handling', () => {
    it('shows error message when image fails to load', async () => {
      wrapper = mount(ModelOutputPanel, {
        props: {
          modelName: 'Gemini',
          imageUrl: 'https://example.com/broken.png',
          generationTime: 2.5,
          qualityScore: 0.92,
        },
      })
      
      const img = wrapper.find('img.model-image')
      await img.trigger('error')
      
      expect(wrapper.find('.error-message').exists()).toBe(true)
      expect(wrapper.find('.error-message').text()).toContain('Failed to load')
    })

    it('hides image and shows placeholder on error', async () => {
      const img = wrapper.find('img.model-image')
      await img.trigger('error')
      
      await wrapper.vm.$nextTick()
      expect(wrapper.find('.image-placeholder').exists()).toBe(true)
      expect(wrapper.find('img.model-image').exists()).toBe(false)
    })
  })

  describe('Accessibility', () => {
    it('has proper image alt text', () => {
      const img = wrapper.find('img.model-image')
      expect(img.attributes('alt')).toBeTruthy()
      expect(img.attributes('alt')).toContain('Gemini')
    })

    it('panel is keyboard accessible (tabindex)', () => {
      expect(wrapper.find('.model-output-panel').attributes('tabindex')).toBe('0')
    })

    it('emits event on Enter key press', async () => {
      await wrapper.find('.model-output-panel').trigger('keydown.enter')
      expect(wrapper.emitted('select')).toBeTruthy()
    })

    it('emits event on Space key press', async () => {
      await wrapper.find('.model-output-panel').trigger('keydown.space')
      expect(wrapper.emitted('select')).toBeTruthy()
    })
  })

  describe('Component Props Validation', () => {
    it('accepts all required props', () => {
      expect(wrapper.props('modelName')).toBe('Gemini')
      expect(wrapper.props('imageUrl')).toBe('https://example.com/image.png')
      expect(wrapper.props('generationTime')).toBe(2.5)
      expect(wrapper.props('qualityScore')).toBe(0.92)
    })

    it('handles optional props gracefully', () => {
      const wrapper2 = mount(ModelOutputPanel, {
        props: {
          modelName: 'Test',
          imageUrl: 'https://example.com/test.png',
          generationTime: 1.0,
          qualityScore: 0.8,
        },
      })
      expect(wrapper2.props('selected')).toBe(false)
    })
  })
})
