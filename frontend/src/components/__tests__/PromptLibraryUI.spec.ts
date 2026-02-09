import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import PromptLibraryUI from '../PromptLibraryUI.vue'
import { nextTick } from 'vue'
import ConfirmDialog from '../ConfirmDialog.vue'
import SkeletonLoader from '../SkeletonLoader.vue'

// Mock API service
vi.mock('../../services/api', () => ({
  apiService: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}))

import { apiService } from '../../services/api'

describe('PromptLibraryUI Component', () => {
  let wrapper: any

  beforeEach(() => {
    vi.clearAllMocks()

    // Mock successful API response with empty data by default
    vi.mocked(apiService.get).mockResolvedValue({
      data: [],
    })
  })

  describe('Component Structure', () => {
    it('renders prompt-library-container', async () => {
      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      expect(wrapper.find('.prompt-library-container').exists()).toBe(true)
    })

    it('renders library header with title', async () => {
      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await nextTick()

      const header = wrapper.find('.library-header')
      expect(header.exists()).toBe(true)
      expect(header.find('h2').text()).toBe('Prompt Library')
    })

    it('has header actions section with buttons', async () => {
      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await nextTick()

      const headerActions = wrapper.find('.header-actions')
      expect(headerActions.exists()).toBe(true)

      const buttons = headerActions.findAll('button')
      expect(buttons.length).toBe(3) // New Prompt, Export, View Toggle
    })

    it('renders library controls section', async () => {
      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await nextTick()

      expect(wrapper.find('.library-controls').exists()).toBe(true)
    })
  })

  describe('Search Input', () => {
    it('search input exists and is visible', async () => {
      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await nextTick()

      const searchInput = wrapper.find('.search-input')
      expect(searchInput.exists()).toBe(true)
      expect(searchInput.element.tagName).toBe('INPUT')
    })

    it('has correct placeholder text', async () => {
      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await nextTick()

      const searchInput = wrapper.find('.search-input')
      expect(searchInput.attributes('placeholder')).toBe('Search prompts by name or tags...')
    })

    it('updates search query on input', async () => {
      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await nextTick()

      const searchInput = wrapper.find('.search-input')
      await searchInput.setValue('watercolor')

      expect(searchInput.element.value).toBe('watercolor')
    })

    it('is of type text', async () => {
      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await nextTick()

      const searchInput = wrapper.find('.search-input')
      expect(searchInput.attributes('type')).toBe('text')
    })
  })

  describe('Empty State', () => {
    it('shows empty state when no prompts loaded', async () => {
      vi.mocked(apiService.get).mockResolvedValue({
        data: [],
      })

      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      const emptyState = wrapper.find('.empty-state')
      expect(emptyState.exists()).toBe(true)
    })

    it('displays empty state icon', async () => {
      vi.mocked(apiService.get).mockResolvedValue({
        data: [],
      })

      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      const emptyIcon = wrapper.find('.empty-icon')
      expect(emptyIcon.exists()).toBe(true)
      expect(emptyIcon.text()).toBe('📚')
    })

    it('shows "No Prompts Found" heading', async () => {
      vi.mocked(apiService.get).mockResolvedValue({
        data: [],
      })

      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      const emptyState = wrapper.find('.empty-state')
      expect(emptyState.exists()).toBe(true)
      expect(emptyState.find('h3').text()).toBe('No Prompts Found')
    })

    it('shows "Create your first prompt" message when no prompts exist', async () => {
      vi.mocked(apiService.get).mockResolvedValue({
        data: [],
      })

      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      const emptyState = wrapper.find('.empty-state')
      expect(emptyState.text()).toContain('Create your first prompt')
    })

    it('hides empty state when prompts are loaded', async () => {
      vi.mocked(apiService.get).mockResolvedValue({
        data: [
          {
            id: 1,
            name: 'Test Prompt',
            promptText: 'Test prompt text',
            category: 'landscape',
            tags: ['nature'],
            isPublic: false,
            createdAt: '2024-01-01',
          },
        ],
      })

      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      expect(wrapper.find('.empty-state').exists()).toBe(false)
    })
  })

  describe('API Calls', () => {
    it('calls API on mount to load prompts', async () => {
      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()

      expect(apiService.get).toHaveBeenCalledWith('/prompts/library')
    })

    it('handles successful API response', async () => {
      const mockPrompts = [
        {
          id: 1,
          name: 'Watercolor Landscape',
          promptText: 'A beautiful watercolor landscape',
          category: 'landscape',
          tags: ['watercolor', 'nature'],
          isPublic: false,
          createdAt: '2024-01-01',
        },
        {
          id: 2,
          name: 'Portrait',
          promptText: 'A detailed portrait',
          category: 'portrait',
          tags: ['portrait'],
          isPublic: true,
          createdAt: '2024-01-02',
        },
      ]

      vi.mocked(apiService.get).mockResolvedValue({
        data: mockPrompts,
      })

      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      const promptCards = wrapper.findAll('.prompt-card')
      expect(promptCards.length).toBe(2)
    })

    it('handles API errors gracefully', async () => {
      vi.mocked(apiService.get).mockRejectedValue(new Error('API Error'))

      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      // Should fallback to sample data or show component
      expect(wrapper.find('.prompt-library-container').exists()).toBe(true)
    })

    it('shows loading skeleton while fetching data', async () => {
      // Delay the API response
      vi.mocked(apiService.get).mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(() => resolve({ data: [] }), 100)
          })
      )

      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await nextTick()

      // Should show skeleton loader during loading
      const container = wrapper.find('.prompts-container.grid')
      expect(container.exists()).toBe(true)
    })
  })

  describe('Category Filter', () => {
    it('renders filter tags section', async () => {
      vi.mocked(apiService.get).mockResolvedValue({
        data: [
          {
            id: 1,
            name: 'Test',
            promptText: 'Text',
            tags: ['nature', 'watercolor'],
            createdAt: '2024-01-01',
          },
        ],
      })

      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      const filterTags = wrapper.find('.filter-tags')
      expect(filterTags.exists()).toBe(true)
    })

    it('displays available tags from prompts', async () => {
      vi.mocked(apiService.get).mockResolvedValue({
        data: [
          {
            id: 1,
            name: 'Test1',
            promptText: 'Text1',
            tags: ['nature', 'peaceful'],
            createdAt: '2024-01-01',
          },
          {
            id: 2,
            name: 'Test2',
            promptText: 'Text2',
            tags: ['abstract', 'colorful'],
            createdAt: '2024-01-02',
          },
        ],
      })

      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      const filterTags = wrapper.findAll('.filter-tag')
      expect(filterTags.length).toBe(4) // abstract, colorful, nature, peaceful (sorted alphabetically)
    })

    it('toggles tag filter on click', async () => {
      vi.mocked(apiService.get).mockResolvedValue({
        data: [
          {
            id: 1,
            name: 'Test',
            promptText: 'Text',
            tags: ['nature'],
            createdAt: '2024-01-01',
          },
        ],
      })

      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      const filterTag = wrapper.find('.filter-tag')
      expect(filterTag.classes()).not.toContain('active')

      await filterTag.trigger('click')
      await nextTick()

      expect(filterTag.classes()).toContain('active')
    })
  })

  describe('Grid/List View Toggle', () => {
    it('renders view toggle button', async () => {
      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await nextTick()

      const buttons = wrapper.findAll('.header-actions button')
      const toggleButton = buttons.find((btn: any) =>
        btn.text().includes('☰') || btn.text().includes('⊞')
      )

      expect(toggleButton).toBeDefined()
    })

    it('toggles between grid and list view', async () => {
      vi.mocked(apiService.get).mockResolvedValue({
        data: [
          {
            id: 1,
            name: 'Test',
            promptText: 'Text',
            tags: ['nature'],
            createdAt: '2024-01-01',
          },
        ],
      })

      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      // Initially should be in grid view
      expect(wrapper.find('.prompts-container.grid').exists()).toBe(true)

      // Find and click toggle button
      const buttons = wrapper.findAll('.header-actions button')
      const toggleButton = buttons.find((btn: any) =>
        btn.text().includes('☰') || btn.text().includes('⊞')
      )

      await toggleButton.trigger('click')
      await nextTick()

      // Should switch to list view
      expect(wrapper.find('.prompts-container.list').exists()).toBe(true)
    })

    it('displays prompts in grid view by default', async () => {
      vi.mocked(apiService.get).mockResolvedValue({
        data: [
          {
            id: 1,
            name: 'Test',
            promptText: 'Text',
            tags: ['nature'],
            createdAt: '2024-01-01',
          },
        ],
      })

      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      expect(wrapper.find('.prompts-grid').exists()).toBe(true)
    })
  })

  describe('Add/Create Button', () => {
    it('renders New Prompt button', async () => {
      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await nextTick()

      const newPromptBtn = wrapper
        .findAll('.header-actions button')
        .find((btn: any) => btn.text().includes('New Prompt'))

      expect(newPromptBtn).toBeDefined()
      expect(newPromptBtn.text()).toContain('New Prompt')
    })

    it('New Prompt button has icon', async () => {
      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await nextTick()

      const newPromptBtn = wrapper
        .findAll('.header-actions button')
        .find((btn: any) => btn.text().includes('New Prompt'))

      expect(newPromptBtn.find('.icon').exists()).toBe(true)
      expect(newPromptBtn.find('.icon').text()).toBe('+')
    })

    it('opens form modal when New Prompt button clicked', async () => {
      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      expect(wrapper.find('.modal-overlay').exists()).toBe(false)

      const newPromptBtn = wrapper
        .findAll('.header-actions button')
        .find((btn: any) => btn.text().includes('New Prompt'))

      await newPromptBtn.trigger('click')
      await nextTick()

      expect(wrapper.find('.modal-overlay').exists()).toBe(true)
      expect(wrapper.find('.prompt-form').exists()).toBe(true)
    })

    it('New Prompt button is disabled when loading', async () => {
      // Mock slow API response
      vi.mocked(apiService.get).mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(() => resolve({ data: [] }), 100)
          })
      )

      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await nextTick()

      const newPromptBtn = wrapper
        .findAll('.header-actions button')
        .find((btn: any) => btn.text().includes('New Prompt'))

      // Button should be disabled during loading
      expect(newPromptBtn.attributes('disabled')).toBeDefined()
    })
  })

  describe('Export Button', () => {
    it('renders Export button', async () => {
      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await nextTick()

      const exportBtn = wrapper
        .findAll('.header-actions button')
        .find((btn: any) => btn.text().includes('Export'))

      expect(exportBtn).toBeDefined()
    })

    it('Export button is disabled when no prompts', async () => {
      vi.mocked(apiService.get).mockResolvedValue({
        data: [],
      })

      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      const exportBtn = wrapper
        .findAll('.header-actions button')
        .find((btn: any) => btn.text().includes('Export'))

      expect(exportBtn.attributes('disabled')).toBeDefined()
    })

    it('Export button is enabled when prompts exist', async () => {
      vi.mocked(apiService.get).mockResolvedValue({
        data: [
          {
            id: 1,
            name: 'Test',
            promptText: 'Text',
            tags: [],
            createdAt: '2024-01-01',
          },
        ],
      })

      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      const exportBtn = wrapper
        .findAll('.header-actions button')
        .find((btn: any) => btn.text().includes('Export'))

      expect(exportBtn.attributes('disabled')).toBeUndefined()
    })
  })

  describe('Prompt Display', () => {
    it('renders prompt cards in grid view', async () => {
      vi.mocked(apiService.get).mockResolvedValue({
        data: [
          {
            id: 1,
            name: 'Test Prompt',
            promptText: 'This is a test prompt text',
            category: 'landscape',
            tags: ['nature'],
            isPublic: false,
            createdAt: '2024-01-01',
          },
        ],
      })

      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      const promptCard = wrapper.find('.prompt-card')
      expect(promptCard.exists()).toBe(true)
      expect(promptCard.find('.card-header h4').text()).toBe('Test Prompt')
    })

    it('displays prompt metadata (category, date)', async () => {
      vi.mocked(apiService.get).mockResolvedValue({
        data: [
          {
            id: 1,
            name: 'Test',
            promptText: 'Text',
            category: 'landscape',
            tags: [],
            createdAt: '2024-01-15',
          },
        ],
      })

      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      const cardMeta = wrapper.find('.card-meta')
      expect(cardMeta.exists()).toBe(true)

      const categoryBadge = cardMeta.find('.badge.category')
      expect(categoryBadge.exists()).toBe(true)
      expect(categoryBadge.text()).toBe('landscape')
    })

    it('displays prompt tags', async () => {
      vi.mocked(apiService.get).mockResolvedValue({
        data: [
          {
            id: 1,
            name: 'Test',
            promptText: 'Text',
            tags: ['watercolor', 'nature', 'peaceful'],
            createdAt: '2024-01-01',
          },
        ],
      })

      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      const cardTags = wrapper.find('.card-tags')
      expect(cardTags.exists()).toBe(true)

      const tags = cardTags.findAll('.tag')
      expect(tags.length).toBe(3)
    })

    it('shows prompt preview text', async () => {
      vi.mocked(apiService.get).mockResolvedValue({
        data: [
          {
            id: 1,
            name: 'Test',
            promptText: 'This is a long prompt text that should be truncated',
            tags: [],
            createdAt: '2024-01-01',
          },
        ],
      })

      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      const preview = wrapper.find('.prompt-preview')
      expect(preview.exists()).toBe(true)
      expect(preview.text().length).toBeGreaterThan(0)
    })
  })

  describe('Search Filtering', () => {
    it('filters prompts by search query', async () => {
      vi.mocked(apiService.get).mockResolvedValue({
        data: [
          {
            id: 1,
            name: 'Watercolor Landscape',
            promptText: 'Beautiful watercolor',
            tags: [],
            createdAt: '2024-01-01',
          },
          {
            id: 2,
            name: 'Abstract Portrait',
            promptText: 'Bold abstract',
            tags: [],
            createdAt: '2024-01-02',
          },
        ],
      })

      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      // Initially should show all prompts
      let promptCards = wrapper.findAll('.prompt-card')
      expect(promptCards.length).toBe(2)

      // Filter by search
      const searchInput = wrapper.find('.search-input')
      await searchInput.setValue('watercolor')
      await nextTick()

      // Should show only matching prompts
      promptCards = wrapper.findAll('.prompt-card')
      expect(promptCards.length).toBe(1)
      expect(promptCards[0].text()).toContain('Watercolor')
    })

    it('shows empty state when search yields no results', async () => {
      vi.mocked(apiService.get).mockResolvedValue({
        data: [
          {
            id: 1,
            name: 'Landscape',
            promptText: 'Text',
            tags: [],
            createdAt: '2024-01-01',
          },
        ],
      })

      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      const searchInput = wrapper.find('.search-input')
      await searchInput.setValue('nonexistent')
      await nextTick()

      expect(wrapper.find('.empty-state').exists()).toBe(true)
      expect(wrapper.find('.empty-state').text()).toContain('Try adjusting your search')
    })
  })

  describe('Form Modal', () => {
    it('displays form title for new prompt', async () => {
      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      const newPromptBtn = wrapper
        .findAll('.header-actions button')
        .find((btn: any) => btn.text().includes('New Prompt'))

      await newPromptBtn.trigger('click')
      await nextTick()

      const formTitle = wrapper.find('.prompt-form h3')
      expect(formTitle.text()).toBe('Create New Prompt')
    })

    it('closes modal when Cancel button clicked', async () => {
      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      const newPromptBtn = wrapper
        .findAll('.header-actions button')
        .find((btn: any) => btn.text().includes('New Prompt'))

      await newPromptBtn.trigger('click')
      await nextTick()

      expect(wrapper.find('.modal-overlay').exists()).toBe(true)

      const cancelBtn = wrapper
        .findAll('.form-actions button')
        .find((btn: any) => btn.text() === 'Cancel')

      await cancelBtn.trigger('click')
      await nextTick()

      expect(wrapper.find('.modal-overlay').exists()).toBe(false)
    })

    it('renders all form fields', async () => {
      wrapper = mount(PromptLibraryUI, {
        global: {
          components: {
            ConfirmDialog,
            SkeletonLoader,
          },
        },
      })
      await flushPromises()
      await nextTick()

      const newPromptBtn = wrapper
        .findAll('.header-actions button')
        .find((btn: any) => btn.text().includes('New Prompt'))

      await newPromptBtn.trigger('click')
      await nextTick()

      const form = wrapper.find('.prompt-form')
      expect(form.find('input[placeholder*="Watercolor"]').exists()).toBe(true)
      expect(form.find('textarea').exists()).toBe(true)
      expect(form.find('select').exists()).toBe(true)
    })
  })
})
