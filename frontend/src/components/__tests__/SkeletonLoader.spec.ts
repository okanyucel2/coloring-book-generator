import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import SkeletonLoader from '../SkeletonLoader.vue'

describe('SkeletonLoader Component', () => {
  let wrapper: any

  beforeEach(() => {
    wrapper = mount(SkeletonLoader, {
      props: {
        variant: 'card',
      },
    })
  })

  describe('Component Structure', () => {
    it('renders skeleton container with correct base class', () => {
      expect(wrapper.find('.skeleton').exists()).toBe(true)
    })

    it('applies variant-specific class', () => {
      expect(wrapper.find('.skeleton-card').exists()).toBe(true)
      expect(wrapper.classes()).toContain('skeleton-card')
    })

    it('has root element with skeleton class', () => {
      const rootClasses = wrapper.classes()
      expect(rootClasses).toContain('skeleton')
    })
  })

  describe('Card Variant', () => {
    beforeEach(() => {
      wrapper = mount(SkeletonLoader, {
        props: {
          variant: 'card',
        },
      })
    })

    it('renders card variant with correct CSS class', () => {
      expect(wrapper.find('.skeleton-card').exists()).toBe(true)
    })

    it('renders skeleton image element', () => {
      expect(wrapper.find('.skeleton-image').exists()).toBe(true)
    })

    it('applies shimmer animation to image', () => {
      const image = wrapper.find('.skeleton-image')
      expect(image.classes()).toContain('shimmer')
    })

    it('renders skeleton lines container', () => {
      expect(wrapper.find('.skeleton-lines').exists()).toBe(true)
    })

    it('renders three skeleton lines', () => {
      const lines = wrapper.findAll('.skeleton-line')
      expect(lines.length).toBe(3)
    })

    it('applies shimmer animation to all lines', () => {
      const lines = wrapper.findAll('.skeleton-line')
      lines.forEach(line => {
        expect(line.classes()).toContain('shimmer')
      })
    })

    it('applies short class to last line', () => {
      const lines = wrapper.findAll('.skeleton-line')
      expect(lines[2].classes()).toContain('short')
    })

    it('has correct width styles for lines', () => {
      const lines = wrapper.findAll('.skeleton-line')
      expect(lines[0].element.style.width).toBe('80%')
      expect(lines[1].element.style.width).toBe('60%')
      expect(lines[2].element.style.width).toBe('40%')
    })
  })

  describe('Row Variant', () => {
    beforeEach(() => {
      wrapper = mount(SkeletonLoader, {
        props: {
          variant: 'row',
        },
      })
    })

    it('renders row variant with correct CSS class', () => {
      expect(wrapper.find('.skeleton-row').exists()).toBe(true)
    })

    it('renders skeleton thumbnail element', () => {
      expect(wrapper.find('.skeleton-thumb').exists()).toBe(true)
    })

    it('applies shimmer animation to thumbnail', () => {
      const thumb = wrapper.find('.skeleton-thumb')
      expect(thumb.classes()).toContain('shimmer')
    })

    it('renders skeleton lines container', () => {
      expect(wrapper.find('.skeleton-lines').exists()).toBe(true)
    })

    it('renders two skeleton lines', () => {
      const lines = wrapper.findAll('.skeleton-line')
      expect(lines.length).toBe(2)
    })

    it('applies shimmer animation to all lines', () => {
      const lines = wrapper.findAll('.skeleton-line')
      lines.forEach(line => {
        expect(line.classes()).toContain('shimmer')
      })
    })

    it('applies short class to last line', () => {
      const lines = wrapper.findAll('.skeleton-line')
      expect(lines[1].classes()).toContain('short')
    })

    it('has correct width styles for lines', () => {
      const lines = wrapper.findAll('.skeleton-line')
      expect(lines[0].element.style.width).toBe('70%')
      expect(lines[1].element.style.width).toBe('50%')
    })
  })

  describe('Default Variant', () => {
    beforeEach(() => {
      wrapper = mount(SkeletonLoader)
    })

    it('defaults to card variant when no variant prop provided', () => {
      expect(wrapper.find('.skeleton-card').exists()).toBe(true)
    })

    it('renders card elements by default', () => {
      expect(wrapper.find('.skeleton-image').exists()).toBe(true)
      expect(wrapper.findAll('.skeleton-line').length).toBe(3)
    })
  })

  describe('Props Reactivity', () => {
    beforeEach(() => {
      wrapper = mount(SkeletonLoader, {
        props: {
          variant: 'card',
        },
      })
    })

    it('switches from card to row variant when prop changes', async () => {
      expect(wrapper.find('.skeleton-card').exists()).toBe(true)
      expect(wrapper.find('.skeleton-row').exists()).toBe(false)

      await wrapper.setProps({
        variant: 'row',
      })

      expect(wrapper.find('.skeleton-card').exists()).toBe(false)
      expect(wrapper.find('.skeleton-row').exists()).toBe(true)
    })

    it('updates rendered elements when variant changes', async () => {
      expect(wrapper.find('.skeleton-image').exists()).toBe(true)
      expect(wrapper.find('.skeleton-thumb').exists()).toBe(false)

      await wrapper.setProps({
        variant: 'row',
      })

      expect(wrapper.find('.skeleton-image').exists()).toBe(false)
      expect(wrapper.find('.skeleton-thumb').exists()).toBe(true)
    })

    it('updates line count when variant changes', async () => {
      let lines = wrapper.findAll('.skeleton-line')
      expect(lines.length).toBe(3)

      await wrapper.setProps({
        variant: 'row',
      })

      lines = wrapper.findAll('.skeleton-line')
      expect(lines.length).toBe(2)
    })
  })

  describe('Shimmer Animation', () => {
    it('shimmer class is present on card image', () => {
      wrapper = mount(SkeletonLoader, {
        props: {
          variant: 'card',
        },
      })
      const image = wrapper.find('.skeleton-image')
      expect(image.classes()).toContain('shimmer')
    })

    it('shimmer class is present on row thumbnail', () => {
      wrapper = mount(SkeletonLoader, {
        props: {
          variant: 'row',
        },
      })
      const thumb = wrapper.find('.skeleton-thumb')
      expect(thumb.classes()).toContain('shimmer')
    })

    it('shimmer class is present on all lines in card variant', () => {
      wrapper = mount(SkeletonLoader, {
        props: {
          variant: 'card',
        },
      })
      const lines = wrapper.findAll('.skeleton-line')
      expect(lines.length).toBeGreaterThan(0)
      lines.forEach(line => {
        expect(line.classes()).toContain('shimmer')
      })
    })

    it('shimmer class is present on all lines in row variant', () => {
      wrapper = mount(SkeletonLoader, {
        props: {
          variant: 'row',
        },
      })
      const lines = wrapper.findAll('.skeleton-line')
      expect(lines.length).toBeGreaterThan(0)
      lines.forEach(line => {
        expect(line.classes()).toContain('shimmer')
      })
    })
  })

  describe('Component Props Validation', () => {
    it('accepts card variant prop', () => {
      wrapper = mount(SkeletonLoader, {
        props: {
          variant: 'card',
        },
      })
      expect(wrapper.props('variant')).toBe('card')
    })

    it('accepts row variant prop', () => {
      wrapper = mount(SkeletonLoader, {
        props: {
          variant: 'row',
        },
      })
      expect(wrapper.props('variant')).toBe('row')
    })

    it('uses default variant value', () => {
      wrapper = mount(SkeletonLoader)
      expect(wrapper.props('variant')).toBe('card')
    })

    it('validator accepts valid variants', () => {
      const cardWrapper = mount(SkeletonLoader, {
        props: {
          variant: 'card',
        },
      })
      expect(cardWrapper.props('variant')).toBe('card')

      const rowWrapper = mount(SkeletonLoader, {
        props: {
          variant: 'row',
        },
      })
      expect(rowWrapper.props('variant')).toBe('row')
    })
  })

  describe('CSS Structure', () => {
    it('card variant has expected child structure', () => {
      wrapper = mount(SkeletonLoader, {
        props: {
          variant: 'card',
        },
      })
      expect(wrapper.find('.skeleton-card').exists()).toBe(true)
      expect(wrapper.find('.skeleton-image.shimmer').exists()).toBe(true)
      expect(wrapper.find('.skeleton-lines').exists()).toBe(true)
    })

    it('row variant has expected child structure', () => {
      wrapper = mount(SkeletonLoader, {
        props: {
          variant: 'row',
        },
      })
      expect(wrapper.find('.skeleton-row').exists()).toBe(true)
      expect(wrapper.find('.skeleton-thumb.shimmer').exists()).toBe(true)
      expect(wrapper.find('.skeleton-lines').exists()).toBe(true)
    })

    it('skeleton-lines container exists in both variants', () => {
      const cardWrapper = mount(SkeletonLoader, {
        props: {
          variant: 'card',
        },
      })
      expect(cardWrapper.find('.skeleton-lines').exists()).toBe(true)

      const rowWrapper = mount(SkeletonLoader, {
        props: {
          variant: 'row',
        },
      })
      expect(rowWrapper.find('.skeleton-lines').exists()).toBe(true)
    })
  })

  describe('Element Count Verification', () => {
    it('card variant renders exactly one image', () => {
      wrapper = mount(SkeletonLoader, {
        props: {
          variant: 'card',
        },
      })
      const images = wrapper.findAll('.skeleton-image')
      expect(images.length).toBe(1)
    })

    it('row variant renders exactly one thumbnail', () => {
      wrapper = mount(SkeletonLoader, {
        props: {
          variant: 'row',
        },
      })
      const thumbs = wrapper.findAll('.skeleton-thumb')
      expect(thumbs.length).toBe(1)
    })

    it('card variant does not render thumbnail', () => {
      wrapper = mount(SkeletonLoader, {
        props: {
          variant: 'card',
        },
      })
      expect(wrapper.find('.skeleton-thumb').exists()).toBe(false)
    })

    it('row variant does not render image', () => {
      wrapper = mount(SkeletonLoader, {
        props: {
          variant: 'row',
        },
      })
      expect(wrapper.find('.skeleton-image').exists()).toBe(false)
    })
  })
})
