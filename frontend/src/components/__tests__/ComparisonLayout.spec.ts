import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ComparisonLayout from '../ComparisonLayout.vue'

describe('ComparisonLayout Component', () => {
  let wrapper: ReturnType<typeof mount>

  beforeEach(() => {
    wrapper = mount(ComparisonLayout)
  })

  describe('Grid Structure', () => {
    it('should render exactly 3 model columns', () => {
      const columns = wrapper.findAll('.model-column')
      expect(columns).toHaveLength(3)
    })

    it('should have comparison-grid container', () => {
      const grid = wrapper.find('.comparison-grid')
      expect(grid.exists()).toBe(true)
    })

    it('should render models in correct order: Gemini, Imagen, Imagen Ultra', () => {
      const headers = wrapper.findAll('.model-header h2')
      expect(headers.at(0)?.text()).toBe('Gemini Flash')
      expect(headers.at(1)?.text()).toBe('Imagen 4.0')
      expect(headers.at(2)?.text()).toBe('Imagen 4.0 Ultra')
    })

    it('should assign correct data-model attributes to columns', () => {
      const columns = wrapper.findAll('.model-column')
      expect(columns.at(0)?.attributes('data-model')).toBe('gemini')
      expect(columns.at(1)?.attributes('data-model')).toBe('imagen')
      expect(columns.at(2)?.attributes('data-model')).toBe('imagen-ultra')
    })
  })

  describe('Output Display', () => {
    it('should show placeholder text when no output exists', () => {
      const placeholders = wrapper.findAll('.model-placeholder')
      expect(placeholders).toHaveLength(3)
      expect(placeholders.at(0)?.text()).toBe('Waiting for output...')
    })

    it('should display image when output is provided', async () => {
      const component = wrapper.vm as any
      component.setModelOutput('gemini', 'data:image/png;base64,test')

      await wrapper.vm.$nextTick()

      const images = wrapper.findAll('.output-image')
      expect(images.length).toBeGreaterThan(0)
      expect(images.at(0)?.attributes('src')).toBe('data:image/png;base64,test')
    })

    it('should replace placeholder with image when output is set', async () => {
      const component = wrapper.vm as any
      component.setModelOutput('imagen', 'https://example.com/imagen.png')

      await wrapper.vm.$nextTick()

      const columns = wrapper.findAll('.model-column')
      const imagenColumn = columns.at(1)!
      const image = imagenColumn.find('.output-image')

      expect(image.exists()).toBe(true)
      expect(image.attributes('src')).toBe('https://example.com/imagen.png')
    })

    it('should have correct alt text for images', async () => {
      const component = wrapper.vm as any
      component.setModelOutput('gemini', 'data:image/png;base64,test')

      await wrapper.vm.$nextTick()

      const image = wrapper.find('.output-image')
      expect(image.attributes('alt')).toBe('Gemini Flash output')
    })

    it('should set correct alt text for all models when outputs are set', async () => {
      const component = wrapper.vm as any
      component.setModelOutput('gemini', 'img1.png')
      component.setModelOutput('imagen', 'img2.png')
      component.setModelOutput('imagen-ultra', 'img3.png')

      await wrapper.vm.$nextTick()

      const images = wrapper.findAll('.output-image')
      expect(images.at(0)?.attributes('alt')).toBe('Gemini Flash output')
      expect(images.at(1)?.attributes('alt')).toBe('Imagen 4.0 output')
      expect(images.at(2)?.attributes('alt')).toBe('Imagen 4.0 Ultra output')
    })
  })

  describe('Loading State', () => {
    it('should show loading spinner when setModelLoading is called', async () => {
      const vm = wrapper.vm as any
      vm.setModelLoading('gemini', true)

      await wrapper.vm.$nextTick()

      expect(wrapper.find('.model-loading').exists()).toBe(true)
      expect(wrapper.find('.spinner').exists()).toBe(true)
    })

    it('should hide loading and show image after setModelOutput', async () => {
      const vm = wrapper.vm as any
      vm.setModelLoading('gemini', true)
      await wrapper.vm.$nextTick()

      vm.setModelOutput('gemini', 'img.png')
      await wrapper.vm.$nextTick()

      expect(wrapper.find('.model-loading').exists()).toBe(false)
      expect(wrapper.find('.output-image').exists()).toBe(true)
    })
  })

  describe('Metadata Display', () => {
    it('should display metadata when provided with setModelOutput', async () => {
      const vm = wrapper.vm as any
      vm.setModelOutput('gemini', 'img.png', {
        duration: '3.2',
        cost: '0.002',
        size: '423.5 KB',
        cached: false,
      })

      await wrapper.vm.$nextTick()

      const meta = wrapper.find('.model-meta')
      expect(meta.exists()).toBe(true)
      expect(meta.text()).toContain('3.2s')
      expect(meta.text()).toContain('$0.002')
      expect(meta.text()).toContain('423.5 KB')
    })

    it('should show cached badge when cached is true', async () => {
      const vm = wrapper.vm as any
      vm.setModelOutput('gemini', 'img.png', {
        duration: '0.1',
        cost: '0.000',
        size: '423.5 KB',
        cached: true,
      })

      await wrapper.vm.$nextTick()

      expect(wrapper.find('.meta-badge.cached').exists()).toBe(true)
    })

    it('should not show metadata when not provided', async () => {
      const vm = wrapper.vm as any
      vm.setModelOutput('gemini', 'img.png')

      await wrapper.vm.$nextTick()

      expect(wrapper.find('.model-meta').exists()).toBe(false)
    })
  })

  describe('Component API', () => {
    it('should expose setModelOutput method', () => {
      const vm = wrapper.vm as any
      expect(typeof vm.setModelOutput).toBe('function')
    })

    it('should expose setModelLoading method', () => {
      const vm = wrapper.vm as any
      expect(typeof vm.setModelLoading).toBe('function')
    })

    it('should expose models ref', () => {
      const vm = wrapper.vm as any
      expect(Array.isArray(vm.models)).toBe(true)
      expect(vm.models).toHaveLength(3)
    })

    it('should update model reactively via setModelOutput', async () => {
      const vm = wrapper.vm as any
      vm.setModelOutput('gemini', 'https://example.com/image.png')

      await wrapper.vm.$nextTick()

      expect(vm.models[0].output).toBe('https://example.com/image.png')
    })

    it('should only update target model, not others', async () => {
      const vm = wrapper.vm as any
      vm.setModelOutput('imagen', 'https://example.com/imagen.png')

      await wrapper.vm.$nextTick()

      expect(vm.models[0].output).toBeUndefined()
      expect(vm.models[1].output).toBe('https://example.com/imagen.png')
      expect(vm.models[2].output).toBeUndefined()
    })
  })

  describe('Content & Structure', () => {
    it('should have title "Multi-Model Comparison"', () => {
      expect(wrapper.find('h1').text()).toBe('Multi-Model Comparison')
    })

    it('should render exactly one comparison-layout div', () => {
      const layouts = wrapper.findAll('.comparison-layout')
      expect(layouts).toHaveLength(1)
    })

    it('should have model-header in each column', () => {
      const headers = wrapper.findAll('.model-header')
      expect(headers).toHaveLength(3)
    })
  })

  describe('Reactivity & State', () => {
    it('should initialize all models with undefined output', () => {
      const vm = wrapper.vm as any
      expect(vm.models.every((m: any) => m.output === undefined)).toBe(true)
    })

    it('should handle multiple sequential updates', async () => {
      const vm = wrapper.vm as any

      vm.setModelOutput('gemini', 'img1.png')
      await wrapper.vm.$nextTick()
      expect(vm.models[0].output).toBe('img1.png')

      vm.setModelOutput('imagen', 'img2.png')
      await wrapper.vm.$nextTick()
      expect(vm.models[1].output).toBe('img2.png')
      expect(vm.models[0].output).toBe('img1.png')

      vm.setModelOutput('imagen-ultra', 'img3.png')
      await wrapper.vm.$nextTick()
      expect(vm.models[2].output).toBe('img3.png')
      expect(vm.models[0].output).toBe('img1.png')
      expect(vm.models[1].output).toBe('img2.png')
    })

    it('should gracefully handle unknown model IDs', async () => {
      const vm = wrapper.vm as any
      vm.setModelOutput('unknown', 'img.png')

      await wrapper.vm.$nextTick()

      expect(vm.models[0].output).toBeUndefined()
      expect(vm.models[1].output).toBeUndefined()
      expect(vm.models[2].output).toBeUndefined()
    })
  })
})
