import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ConfirmDialog from '../ConfirmDialog.vue'

describe('ConfirmDialog Component', () => {
  let wrapper: any

  beforeEach(() => {
    wrapper = mount(ConfirmDialog, {
      props: {
        visible: true,
        title: 'Delete Item',
        message: 'Are you sure you want to delete this item?',
        confirmText: 'Delete',
        cancelText: 'Cancel',
        destructive: false,
      },
    })
  })

  describe('Component Structure', () => {
    it('renders when visible is true', () => {
      expect(wrapper.find('.dialog-overlay').exists()).toBe(true)
      expect(wrapper.find('.dialog-content').exists()).toBe(true)
    })

    it('does not render when visible is false', () => {
      const wrapper2 = mount(ConfirmDialog, {
        props: {
          visible: false,
          message: 'Test message',
        },
      })
      expect(wrapper2.find('.dialog-overlay').exists()).toBe(false)
    })

    it('has Transition wrapper', () => {
      expect(wrapper.findComponent({ name: 'Transition' }).exists()).toBe(true)
    })

    it('has dialog content container', () => {
      expect(wrapper.find('.dialog-content').exists()).toBe(true)
    })
  })

  describe('Props Display', () => {
    it('displays title prop in header', () => {
      expect(wrapper.find('.dialog-title').text()).toBe('Delete Item')
    })

    it('displays message prop', () => {
      expect(wrapper.find('.dialog-message').text()).toBe('Are you sure you want to delete this item?')
    })

    it('displays custom confirm button text', () => {
      const confirmBtn = wrapper.findAll('.btn')[1]
      expect(confirmBtn.text()).toBe('Delete')
    })

    it('displays custom cancel button text', () => {
      const cancelBtn = wrapper.find('.btn-cancel')
      expect(cancelBtn.text()).toBe('Cancel')
    })

    it('uses default title when not provided', () => {
      const wrapper2 = mount(ConfirmDialog, {
        props: {
          visible: true,
          message: 'Test message',
        },
      })
      expect(wrapper2.find('.dialog-title').text()).toBe('Confirm')
    })

    it('uses default confirm text when not provided', () => {
      const wrapper2 = mount(ConfirmDialog, {
        props: {
          visible: true,
          message: 'Test message',
        },
      })
      const confirmBtn = wrapper2.findAll('.btn')[1]
      expect(confirmBtn.text()).toBe('Confirm')
    })

    it('uses default cancel text when not provided', () => {
      const wrapper2 = mount(ConfirmDialog, {
        props: {
          visible: true,
          message: 'Test message',
        },
      })
      const cancelBtn = wrapper2.find('.btn-cancel')
      expect(cancelBtn.text()).toBe('Cancel')
    })
  })

  describe('Destructive Mode', () => {
    it('applies btn-confirm class when destructive is false', () => {
      const confirmBtn = wrapper.findAll('.btn')[1]
      expect(confirmBtn.classes()).toContain('btn-confirm')
      expect(confirmBtn.classes()).not.toContain('btn-destructive')
    })

    it('applies btn-destructive class when destructive is true', () => {
      const wrapper2 = mount(ConfirmDialog, {
        props: {
          visible: true,
          message: 'Delete permanently?',
          destructive: true,
        },
      })
      const confirmBtn = wrapper2.findAll('.btn')[1]
      expect(confirmBtn.classes()).toContain('btn-destructive')
      expect(confirmBtn.classes()).not.toContain('btn-confirm')
    })

    it('always has btn base class on confirm button', () => {
      const confirmBtn = wrapper.findAll('.btn')[1]
      expect(confirmBtn.classes()).toContain('btn')
    })
  })

  describe('Confirm Button Interaction', () => {
    it('emits confirm event when confirm button is clicked', async () => {
      const confirmBtn = wrapper.findAll('.btn')[1]
      await confirmBtn.trigger('click')
      expect(wrapper.emitted('confirm')).toBeTruthy()
    })

    it('emits update:visible event with false when confirm is clicked', async () => {
      const confirmBtn = wrapper.findAll('.btn')[1]
      await confirmBtn.trigger('click')
      expect(wrapper.emitted('update:visible')).toBeTruthy()
      expect(wrapper.emitted('update:visible')[0]).toEqual([false])
    })

    it('emits both confirm and update:visible events', async () => {
      const confirmBtn = wrapper.findAll('.btn')[1]
      await confirmBtn.trigger('click')
      expect(wrapper.emitted('confirm')).toBeTruthy()
      expect(wrapper.emitted('update:visible')).toBeTruthy()
    })
  })

  describe('Cancel Button Interaction', () => {
    it('emits cancel event when cancel button is clicked', async () => {
      const cancelBtn = wrapper.find('.btn-cancel')
      await cancelBtn.trigger('click')
      expect(wrapper.emitted('cancel')).toBeTruthy()
    })

    it('emits update:visible event with false when cancel is clicked', async () => {
      const cancelBtn = wrapper.find('.btn-cancel')
      await cancelBtn.trigger('click')
      expect(wrapper.emitted('update:visible')).toBeTruthy()
      expect(wrapper.emitted('update:visible')[0]).toEqual([false])
    })

    it('emits both cancel and update:visible events', async () => {
      const cancelBtn = wrapper.find('.btn-cancel')
      await cancelBtn.trigger('click')
      expect(wrapper.emitted('cancel')).toBeTruthy()
      expect(wrapper.emitted('update:visible')).toBeTruthy()
    })
  })

  describe('Keyboard Interaction', () => {
    it('emits cancel event when Escape key is pressed', async () => {
      const overlay = wrapper.find('.dialog-overlay')
      await overlay.trigger('keydown.escape')
      expect(wrapper.emitted('cancel')).toBeTruthy()
    })

    it('emits update:visible with false when Escape is pressed', async () => {
      const overlay = wrapper.find('.dialog-overlay')
      await overlay.trigger('keydown.escape')
      expect(wrapper.emitted('update:visible')).toBeTruthy()
      expect(wrapper.emitted('update:visible')[0]).toEqual([false])
    })

    it('handles Escape key press on dialog overlay', async () => {
      const overlay = wrapper.find('.dialog-overlay')
      await overlay.trigger('keydown.escape')
      expect(wrapper.emitted('cancel')).toBeTruthy()
      expect(wrapper.emitted('update:visible')).toBeTruthy()
    })
  })

  describe('Overlay Click Behavior', () => {
    it('emits cancel when clicking overlay background', async () => {
      const overlay = wrapper.find('.dialog-overlay')
      await overlay.trigger('click.self')
      expect(wrapper.emitted('cancel')).toBeTruthy()
    })

    it('emits update:visible with false when clicking overlay', async () => {
      const overlay = wrapper.find('.dialog-overlay')
      await overlay.trigger('click.self')
      expect(wrapper.emitted('update:visible')).toBeTruthy()
      expect(wrapper.emitted('update:visible')[0]).toEqual([false])
    })

    it('does not close when clicking dialog content', async () => {
      const content = wrapper.find('.dialog-content')
      await content.trigger('click')
      expect(wrapper.emitted('cancel')).toBeFalsy()
    })
  })

  describe('Accessibility (ARIA)', () => {
    it('has role="alertdialog" on overlay', () => {
      const overlay = wrapper.find('.dialog-overlay')
      expect(overlay.attributes('role')).toBe('alertdialog')
    })

    it('has aria-modal="true" attribute', () => {
      const overlay = wrapper.find('.dialog-overlay')
      expect(overlay.attributes('aria-modal')).toBe('true')
    })

    it('has aria-label matching title prop', () => {
      const overlay = wrapper.find('.dialog-overlay')
      expect(overlay.attributes('aria-label')).toBe('Delete Item')
    })

    it('updates aria-label when title changes', async () => {
      const overlay = wrapper.find('.dialog-overlay')
      expect(overlay.attributes('aria-label')).toBe('Delete Item')

      await wrapper.setProps({
        title: 'Confirm Action',
      })

      expect(overlay.attributes('aria-label')).toBe('Confirm Action')
    })

    it('uses default title for aria-label when title not provided', () => {
      const wrapper2 = mount(ConfirmDialog, {
        props: {
          visible: true,
          message: 'Test message',
        },
      })
      const overlay = wrapper2.find('.dialog-overlay')
      expect(overlay.attributes('aria-label')).toBe('Confirm')
    })
  })

  describe('Props Reactivity', () => {
    it('updates visibility when visible prop changes', async () => {
      expect(wrapper.find('.dialog-overlay').exists()).toBe(true)

      await wrapper.setProps({
        visible: false,
      })

      expect(wrapper.find('.dialog-overlay').exists()).toBe(false)
    })

    it('updates title text when prop changes', async () => {
      expect(wrapper.find('.dialog-title').text()).toBe('Delete Item')

      await wrapper.setProps({
        title: 'Update Item',
      })

      expect(wrapper.find('.dialog-title').text()).toBe('Update Item')
    })

    it('updates message text when prop changes', async () => {
      expect(wrapper.find('.dialog-message').text()).toBe('Are you sure you want to delete this item?')

      await wrapper.setProps({
        message: 'This action cannot be undone.',
      })

      expect(wrapper.find('.dialog-message').text()).toBe('This action cannot be undone.')
    })

    it('updates button text when confirmText changes', async () => {
      let confirmBtn = wrapper.findAll('.btn')[1]
      expect(confirmBtn.text()).toBe('Delete')

      await wrapper.setProps({
        confirmText: 'Proceed',
      })

      confirmBtn = wrapper.findAll('.btn')[1]
      expect(confirmBtn.text()).toBe('Proceed')
    })

    it('updates button text when cancelText changes', async () => {
      let cancelBtn = wrapper.find('.btn-cancel')
      expect(cancelBtn.text()).toBe('Cancel')

      await wrapper.setProps({
        cancelText: 'Go Back',
      })

      cancelBtn = wrapper.find('.btn-cancel')
      expect(cancelBtn.text()).toBe('Go Back')
    })

    it('toggles destructive class when destructive prop changes', async () => {
      let confirmBtn = wrapper.findAll('.btn')[1]
      expect(confirmBtn.classes()).toContain('btn-confirm')
      expect(confirmBtn.classes()).not.toContain('btn-destructive')

      await wrapper.setProps({
        destructive: true,
      })

      confirmBtn = wrapper.findAll('.btn')[1]
      expect(confirmBtn.classes()).toContain('btn-destructive')
      expect(confirmBtn.classes()).not.toContain('btn-confirm')
    })
  })

  describe('Button Layout', () => {
    it('has actions container', () => {
      expect(wrapper.find('.dialog-actions').exists()).toBe(true)
    })

    it('renders both cancel and confirm buttons', () => {
      const buttons = wrapper.findAll('.btn')
      expect(buttons.length).toBe(2)
    })

    it('cancel button comes before confirm button', () => {
      const buttons = wrapper.findAll('.btn')
      expect(buttons[0].classes()).toContain('btn-cancel')
      expect(buttons[1].classes()).toContain('btn-confirm')
    })

    it('has proper button structure', () => {
      const cancelBtn = wrapper.find('.btn-cancel')
      const confirmBtn = wrapper.findAll('.btn')[1]
      expect(cancelBtn.element.tagName).toBe('BUTTON')
      expect(confirmBtn.element.tagName).toBe('BUTTON')
    })
  })

  describe('Component Props Validation', () => {
    it('accepts all props correctly', () => {
      expect(wrapper.props('visible')).toBe(true)
      expect(wrapper.props('title')).toBe('Delete Item')
      expect(wrapper.props('message')).toBe('Are you sure you want to delete this item?')
      expect(wrapper.props('confirmText')).toBe('Delete')
      expect(wrapper.props('cancelText')).toBe('Cancel')
      expect(wrapper.props('destructive')).toBe(false)
    })

    it('handles minimal props (only required)', () => {
      const wrapper2 = mount(ConfirmDialog, {
        props: {
          visible: true,
          message: 'Simple message',
        },
      })
      expect(wrapper2.props('visible')).toBe(true)
      expect(wrapper2.props('message')).toBe('Simple message')
      expect(wrapper2.props('title')).toBe('Confirm')
      expect(wrapper2.props('confirmText')).toBe('Confirm')
      expect(wrapper2.props('cancelText')).toBe('Cancel')
      expect(wrapper2.props('destructive')).toBe(false)
    })
  })

  describe('Focus Management', () => {
    it('has cancel button ref for focus management', () => {
      const cancelBtn = wrapper.find('.btn-cancel')
      expect(cancelBtn.exists()).toBe(true)
    })

    it('has dialog content ref', () => {
      const dialogContent = wrapper.find('.dialog-content')
      expect(dialogContent.exists()).toBe(true)
    })
  })

  describe('Transition States', () => {
    it('has Transition component with "dialog" name', () => {
      const transition = wrapper.findComponent({ name: 'Transition' })
      expect(transition.exists()).toBe(true)
      expect(transition.attributes('name')).toBe('dialog')
    })

    it('wraps dialog overlay in Transition', () => {
      const transition = wrapper.findComponent({ name: 'Transition' })
      const overlay = wrapper.find('.dialog-overlay')
      expect(transition.exists()).toBe(true)
      expect(overlay.exists()).toBe(true)
    })
  })
})
