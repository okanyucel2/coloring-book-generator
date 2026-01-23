import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ComparisonLayout from '../ComparisonLayout.vue'

describe('ComparisonLayout Component - TDD Flow', () => {
  let wrapper: ReturnType<typeof mount>

  beforeEach(() => {
    wrapper = mount(ComparisonLayout)
  })

  describe('🎯 CRITICAL: Grid Structure (Must Pass)', () => {
    it('should render exactly 3 model columns', () => {
      const columns = wrapper.findAll('.model-column')
      expect(columns).toHaveLength(3)
    })

    it('should have comparison-grid container', () => {
      const grid = wrapper.find('.comparison-grid')
      expect(grid.exists()).toBe(true)
    })

    it('should render models in correct order: Claude, GPT-4, Gemini', () => {
      const headers = wrapper.findAll('.model-header h2')
      expect(headers[0].text()).toBe('Claude 3.5')
      expect(headers[1].text()).toBe('GPT-4')
      expect(headers[2].text()).toBe('Gemini 2.0')
    })

    it('should assign correct data-model attributes to columns', () => {
      const columns = wrapper.findAll('.model-column')
      expect(columns[0].attributes('data-model')).toBe('claude')
      expect(columns[1].attributes('data-model')).toBe('gpt4')
      expect(columns[2].attributes('data-model')).toBe('gemini')
    })
  })

  describe('🎯 Output Display (Must Pass)', () => {
    it('should show placeholder text when no output exists', () => {
      const placeholders = wrapper.findAll('.model-placeholder')
      expect(placeholders).toHaveLength(3)
      expect(placeholders[0].text()).toBe('Waiting for output...')
    })

    it('should display image when output is provided', async () => {
      const component = wrapper.vm as any
      component.setModelOutput('claude', 'data:image/png;base64,test')
      
      await wrapper.vm.$nextTick()
      
      const images = wrapper.findAll('.output-image')
      expect(images.length).toBeGreaterThan(0)
      expect(images[0].attributes('src')).toBe('data:image/png;base64,test')
    })

    it('should replace placeholder with image when output is set', async () => {
      const component = wrapper.vm as any
      component.setModelOutput('gpt4', 'https://example.com/gpt4.png')
      
      await wrapper.vm.$nextTick()
      
      const columns = wrapper.findAll('.model-column')
      const gpt4Column = columns[1]
      const image = gpt4Column.find('.output-image')
      
      expect(image.exists()).toBe(true)
      expect(image.attributes('src')).toBe('https://example.com/gpt4.png')
    })

    it('should have correct alt text for images', async () => {
      const component = wrapper.vm as any
      component.setModelOutput('claude', 'data:image/png;base64,test')
      
      await wrapper.vm.$nextTick()
      
      const image = wrapper.find('.output-image')
      expect(image.attributes('alt')).toBe('Claude 3.5 output')
    })

    it('should set correct alt text for all models when outputs are set', async () => {
      const component = wrapper.vm as any
      component.setModelOutput('claude', 'img1.png')
      component.setModelOutput('gpt4', 'img2.png')
      component.setModelOutput('gemini', 'img3.png')
      
      await wrapper.vm.$nextTick()
      
      const images = wrapper.findAll('.output-image')
      expect(images[0].attributes('alt')).toBe('Claude 3.5 output')
      expect(images[1].attributes('alt')).toBe('GPT-4 output')
      expect(images[2].attributes('alt')).toBe('Gemini 2.0 output')
    })
  })

  describe('🎯 Component API (Must Pass)', () => {
    it('should expose setModelOutput method', () => {
      const vm = wrapper.vm as any
      expect(typeof vm.setModelOutput).toBe('function')
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
      
      expect(vm.models[2].output).toBe('https://example.com/image.png')
    })

    it('should only update target model, not others', async () => {
      const vm = wrapper.vm as any
      vm.setModelOutput('gpt4', 'https://example.com/gpt4.png')
      
      await wrapper.vm.$nextTick()
      
      expect(vm.models[0].output).toBeUndefined()
      expect(vm.models[1].output).toBe('https://example.com/gpt4.png')
      expect(vm.models[2].output).toBeUndefined()
    })
  })

  describe('🎯 Content & Structure (Must Pass)', () => {
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

    it('should have valid HTML structure with proper nesting', () => {
      const layout = wrapper.find('.comparison-layout')
      expect(layout.exists()).toBe(true)
      
      const grid = layout.find('.comparison-grid')
      expect(grid.exists()).toBe(true)
      
      const columns = grid.findAll('.model-column')
      expect(columns).toHaveLength(3)
    })
  })

  describe('🎯 Reactivity & State (Must Pass)', () => {
    it('should initialize all models with undefined output', () => {
      const vm = wrapper.vm as any
      expect(vm.models.every((m: any) => m.output === undefined)).toBe(true)
    })

    it('should handle multiple sequential updates', async () => {
      const vm = wrapper.vm as any
      
      vm.setModelOutput('claude', 'img1.png')
      await wrapper.vm.$nextTick()
      expect(vm.models[0].output).toBe('img1.png')
      
      vm.setModelOutput('gpt4', 'img2.png')
      await wrapper.vm.$nextTick()
      expect(vm.models[1].output).toBe('img2.png')
      expect(vm.models[0].output).toBe('img1.png') // unchanged
      
      vm.setModelOutput('gemini', 'img3.png')
      await wrapper.vm.$nextTick()
      expect(vm.models[2].output).toBe('img3.png')
      expect(vm.models[0].output).toBe('img1.png')
      expect(vm.models[1].output).toBe('img2.png')
    })

    it('should gracefully handle unknown model IDs', async () => {
      const vm = wrapper.vm as any
      vm.setModelOutput('unknown', 'img.png')
      
      await wrapper.vm.$nextTick()
      
      // No error, models unchanged
      expect(vm.models[0].output).toBeUndefined()
      expect(vm.models[1].output).toBeUndefined()
      expect(vm.models[2].output).toBeUndefined()
    })
  })
})
