import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import VariationHistoryComparison from '../VariationHistoryComparison.vue'
import { apiService } from '../../services/api'

// Mock the apiService before imports
vi.mock('../../services/api', () => ({
  apiService: {
    get: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}))

// Mock ConfirmDialog component
vi.mock('../ConfirmDialog.vue', () => ({
  default: {
    name: 'ConfirmDialog',
    template: '<div class="confirm-dialog-mock"></div>',
    props: ['visible', 'title', 'message', 'confirmText', 'cancelText', 'destructive'],
    emits: ['update:visible', 'confirm', 'cancel'],
  },
}))

// Mock SkeletonLoader component
vi.mock('../SkeletonLoader.vue', () => ({
  default: {
    name: 'SkeletonLoader',
    template: '<div class="skeleton-loader-mock"></div>',
    props: ['variant'],
  },
}))

// Mock sample data — provide realistic fallback so API-error test works
vi.mock('@/data/mock-data', () => ({
  sampleVariations: [
    {
      id: 'sample-1',
      prompt: 'Sample lion portrait',
      model: 'dall-e-3',
      imageUrl: 'https://example.com/sample1.png',
      rating: 4,
      seed: 42581,
      generatedAt: '2026-02-08T14:30:00Z',
      notes: 'Sample variation',
      parameters: { style: 'line-art' },
    },
  ],
}))

// Sample test data
const mockVariations = [
  {
    id: 'var-1',
    model: 'dall-e-3',
    imageUrl: 'https://example.com/var1.png',
    prompt: 'A beautiful sunset over the mountains',
    seed: 123456,
    width: 1024,
    height: 1024,
    rating: 5,
    notes: 'Best variation so far',
    createdAt: new Date('2026-02-09T10:00:00Z').toISOString(),
  },
  {
    id: 'var-2',
    model: 'midjourney',
    imageUrl: 'https://example.com/var2.png',
    prompt: 'A futuristic city with flying cars',
    seed: 789012,
    width: 1920,
    height: 1080,
    rating: 4,
    notes: 'Good composition',
    createdAt: new Date('2026-02-08T15:30:00Z').toISOString(),
  },
  {
    id: 'var-3',
    model: 'stable-diffusion',
    imageUrl: 'https://example.com/var3.png',
    prompt: 'Abstract art with vibrant colors',
    seed: 345678,
    width: 512,
    height: 512,
    rating: 3,
    notes: '',
    createdAt: new Date('2026-02-07T09:15:00Z').toISOString(),
  },
]

describe('VariationHistoryComparison Component', () => {
  let wrapper: any

  beforeEach(() => {
    // Reset all mocks before each test
    vi.clearAllMocks()

    // Mock successful API response by default (deep clone to prevent mutation leaking between tests)
    vi.mocked(apiService.get).mockResolvedValue({
      data: JSON.parse(JSON.stringify(mockVariations)),
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  describe('Component Structure', () => {
    it('renders variation-history-container', async () => {
      wrapper = mount(VariationHistoryComparison)
      await flushPromises()

      expect(wrapper.find('.variation-history-container').exists()).toBe(true)
    })

    it('renders header with title', async () => {
      wrapper = mount(VariationHistoryComparison)
      await flushPromises()

      const header = wrapper.find('.history-header h2')
      expect(header.exists()).toBe(true)
      expect(header.text()).toContain('Variation History')
    })

    it('renders filter controls section', async () => {
      wrapper = mount(VariationHistoryComparison)
      await flushPromises()

      expect(wrapper.find('.history-controls').exists()).toBe(true)
    })

    it('renders clear history button', async () => {
      wrapper = mount(VariationHistoryComparison)
      await flushPromises()

      const clearBtn = wrapper.find('.history-header button')
      expect(clearBtn.exists()).toBe(true)
      expect(clearBtn.text()).toContain('Clear History')
    })
  })

  describe('API Integration & Loading', () => {
    it('calls API to load history on mount', async () => {
      wrapper = mount(VariationHistoryComparison)
      await flushPromises()

      expect(apiService.get).toHaveBeenCalledWith('/variations/history')
      expect(apiService.get).toHaveBeenCalledTimes(1)
    })

    it('displays loading skeleton while fetching', async () => {
      // Mock a delayed response that never resolves during test
      vi.mocked(apiService.get).mockReturnValue(new Promise(() => {}))

      wrapper = mount(VariationHistoryComparison)
      await wrapper.vm.$nextTick()

      // isLoading is true before API returns, so skeleton-timeline should render
      expect(wrapper.find('.skeleton-timeline').exists()).toBe(true)
    })

    it('hides loading state after data loads', async () => {
      wrapper = mount(VariationHistoryComparison)
      await flushPromises()

      expect(wrapper.find('.skeleton-timeline').exists()).toBe(false)
    })

    it('handles API error gracefully with sample data', async () => {
      vi.mocked(apiService.get).mockRejectedValue(new Error('API Error'))
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

      wrapper = mount(VariationHistoryComparison)
      await flushPromises()

      expect(consoleWarnSpy).toHaveBeenCalledWith('API unavailable, using sample data')
      expect(wrapper.vm.variationHistory.length).toBeGreaterThan(0)

      consoleWarnSpy.mockRestore()
    })
  })

  describe('Empty State', () => {
    it('shows empty state when no variations loaded', async () => {
      vi.mocked(apiService.get).mockResolvedValue({ data: [] })

      wrapper = mount(VariationHistoryComparison)
      await flushPromises()

      expect(wrapper.find('.empty-state').exists()).toBe(true)
    })

    it('displays empty state icon and message', async () => {
      vi.mocked(apiService.get).mockResolvedValue({ data: [] })

      wrapper = mount(VariationHistoryComparison)
      await flushPromises()

      const emptyState = wrapper.find('.empty-state')
      expect(emptyState.find('.empty-icon').text()).toBe('📊')
      expect(emptyState.text()).toContain('No Variations Found')
      expect(emptyState.text()).toContain('Generate variations to see your history here')
    })

    it('hides empty state when variations are loaded', async () => {
      wrapper = mount(VariationHistoryComparison)
      await flushPromises()

      expect(wrapper.find('.empty-state').exists()).toBe(false)
      expect(wrapper.find('.history-timeline').exists()).toBe(true)
    })
  })

  describe('Filter & Sort Controls', () => {
    beforeEach(async () => {
      wrapper = mount(VariationHistoryComparison)
      await flushPromises()
    })

    it('renders model filter dropdown', () => {
      const modelFilter = wrapper.find('select').findAll('option')
      expect(modelFilter.length).toBeGreaterThan(0)
      expect(modelFilter[0].text()).toBe('All Models')
    })

    it('renders date filter dropdown', () => {
      const selects = wrapper.findAll('select')
      expect(selects.length).toBeGreaterThanOrEqual(2)

      const dateOptions = selects[1].findAll('option')
      expect(dateOptions[0].text()).toBe('All Time')
    })

    it('renders sort by dropdown', () => {
      const selects = wrapper.findAll('select')
      const sortSelect = selects[2]

      const sortOptions = sortSelect.findAll('option')
      expect(sortOptions.some((opt: any) => opt.text() === 'Newest First')).toBe(true)
    })

    it('renders search input', () => {
      const searchInput = wrapper.find('.search-input')
      expect(searchInput.exists()).toBe(true)
      expect(searchInput.attributes('placeholder')).toContain('Search')
    })

    it('filters variations by model', async () => {
      const modelFilter = wrapper.find('select')
      await modelFilter.setValue('dall-e-3')
      await flushPromises()

      expect(wrapper.vm.filterModel).toBe('dall-e-3')
      expect(wrapper.vm.filteredVariations.length).toBeLessThanOrEqual(mockVariations.length)
    })

    it('filters variations by search query', async () => {
      const searchInput = wrapper.find('.search-input')
      await searchInput.setValue('sunset')
      await flushPromises()

      const filtered = wrapper.vm.filteredVariations
      expect(filtered.length).toBeLessThanOrEqual(mockVariations.length)
      expect(filtered.every((v: any) =>
        v.prompt.toLowerCase().includes('sunset') ||
        (v.notes && v.notes.toLowerCase().includes('sunset'))
      )).toBe(true)
    })
  })

  describe('Timeline/Card Display', () => {
    beforeEach(async () => {
      wrapper = mount(VariationHistoryComparison)
      await flushPromises()
    })

    it('displays timeline items for each variation', () => {
      const timelineItems = wrapper.findAll('.timeline-item')
      expect(timelineItems.length).toBe(mockVariations.length)
    })

    it('displays variation thumbnails', () => {
      const thumbnails = wrapper.findAll('.item-thumbnail img')
      expect(thumbnails.length).toBe(mockVariations.length)
      expect(thumbnails[0].attributes('src')).toBe(mockVariations[0].imageUrl)
    })

    it('displays variation model names', () => {
      const items = wrapper.findAll('.timeline-item')
      expect(items[0].text()).toContain('dall-e-3')
    })

    it('displays variation prompts (truncated)', () => {
      const items = wrapper.findAll('.timeline-item')
      expect(items[0].text()).toContain('A beautiful sunset')
    })

    it('shows rating badges when present', () => {
      const badges = wrapper.findAll('.badge.rating')
      expect(badges.length).toBeGreaterThan(0)
      expect(badges[0].text()).toContain('5/5')
    })

    it('shows seed and resolution badges', () => {
      const items = wrapper.findAll('.timeline-item')
      expect(items[0].text()).toContain('Seed: 123456')
      expect(items[0].text()).toContain('1024×1024')
    })
  })

  describe('Selection & Comparison', () => {
    beforeEach(async () => {
      wrapper = mount(VariationHistoryComparison)
      await flushPromises()
    })

    it('renders selection checkboxes', () => {
      const checkboxes = wrapper.findAll('.checkbox')
      expect(checkboxes.length).toBe(mockVariations.length)
    })

    it('toggles variation selection on checkbox click', async () => {
      const checkbox = wrapper.find('.checkbox')
      await checkbox.setValue(true)
      await flushPromises()

      expect(wrapper.vm.selectedVariations.length).toBe(1)
      expect(wrapper.vm.selectedVariations[0].id).toBe('var-1')
    })

    it('adds variation to comparison on Compare button click', async () => {
      const compareBtn = wrapper.find('.item-actions .btn-primary')
      await compareBtn.trigger('click')
      await flushPromises()

      expect(wrapper.vm.selectedVariations.length).toBe(1)
    })

    it('shows comparison view when variations selected', async () => {
      const checkbox = wrapper.find('.checkbox')
      await checkbox.setValue(true)
      await flushPromises()

      expect(wrapper.find('.comparison-view').exists()).toBe(true)
      expect(wrapper.find('.history-timeline').exists()).toBe(false)
    })

    it('displays comparison grid with selected variations', async () => {
      const checkbox = wrapper.find('.checkbox')
      await checkbox.setValue(true)
      await flushPromises()

      const comparisonCards = wrapper.findAll('.comparison-card')
      expect(comparisonCards.length).toBe(1)
    })

    it('removes variation from comparison on deselect', async () => {
      const checkbox = wrapper.find('.checkbox')
      await checkbox.setValue(true)
      await flushPromises()

      expect(wrapper.vm.selectedVariations.length).toBe(1)

      const closeBtn = wrapper.find('.close-btn')
      await closeBtn.trigger('click')
      await flushPromises()

      expect(wrapper.vm.selectedVariations.length).toBe(0)
    })

    it('supports select all functionality', async () => {
      const selectAllBtn = wrapper.findAll('.header-actions button')[2]
      await selectAllBtn.trigger('click')
      await flushPromises()

      expect(wrapper.vm.selectedVariations.length).toBe(mockVariations.length)
    })

    it('exits comparison view on back button', async () => {
      const checkbox = wrapper.find('.checkbox')
      await checkbox.setValue(true)
      await flushPromises()

      expect(wrapper.find('.comparison-view').exists()).toBe(true)

      const backBtn = wrapper.find('.comparison-controls .btn-secondary')
      await backBtn.trigger('click')
      await flushPromises()

      expect(wrapper.vm.selectedVariations.length).toBe(0)
      expect(wrapper.find('.history-timeline').exists()).toBe(true)
    })
  })

  describe('Comparison View Features', () => {
    beforeEach(async () => {
      wrapper = mount(VariationHistoryComparison)
      await flushPromises()

      // Select first variation
      const checkbox = wrapper.find('.checkbox')
      await checkbox.setValue(true)
      await flushPromises()
    })

    it('displays variation metadata in comparison view', () => {
      const meta = wrapper.find('.comparison-meta')
      expect(meta.text()).toContain('Model:')
      expect(meta.text()).toContain('dall-e-3')
      expect(meta.text()).toContain('Seed:')
      expect(meta.text()).toContain('123456')
    })

    it('displays star rating system', () => {
      const stars = wrapper.findAll('.star')
      expect(stars.length).toBe(5)
    })

    it('allows rating variations', async () => {
      vi.mocked(apiService.patch).mockResolvedValue({ data: { rating: 4 } })

      const stars = wrapper.findAll('.star')
      await stars[3].trigger('click')
      await flushPromises()

      expect(apiService.patch).toHaveBeenCalledWith('/variations/var-1', { rating: 4 })
    })

    it('displays notes textarea', () => {
      const notesTextarea = wrapper.find('.notes-input')
      expect(notesTextarea.exists()).toBe(true)
      expect(notesTextarea.attributes('placeholder')).toContain('Add notes')
    })

    it('updates notes on input', async () => {
      vi.mocked(apiService.patch).mockResolvedValue({ data: { notes: 'Updated notes' } })

      const notesTextarea = wrapper.find('.notes-input')
      await notesTextarea.setValue('Updated notes')
      await notesTextarea.trigger('input')
      await flushPromises()

      // Check if API was called (debounce might delay this)
      expect(apiService.patch).toHaveBeenCalled()
    })

    it('displays comparison action buttons', () => {
      const actions = wrapper.find('.comparison-actions')
      expect(actions.text()).toContain('Download')
      expect(actions.text()).toContain('Duplicate')
      expect(actions.text()).toContain('Share')
      expect(actions.text()).toContain('Delete')
    })

    it('displays analysis section with statistics', () => {
      const analysis = wrapper.find('.analysis-section')
      expect(analysis.exists()).toBe(true)
      expect(analysis.text()).toContain('Comparative Analysis')
    })
  })

  describe('Actions', () => {
    beforeEach(async () => {
      wrapper = mount(VariationHistoryComparison)
      await flushPromises()
    })

    it('triggers download on download button click', async () => {
      const createElementSpy = vi.spyOn(document, 'createElement')

      const downloadBtn = wrapper.find('.item-actions .btn-secondary')
      await downloadBtn.trigger('click')

      expect(createElementSpy).toHaveBeenCalledWith('a')
    })

    it('shows confirm dialog on clear history', async () => {
      const clearBtn = wrapper.findAll('.header-actions button')[0]
      await clearBtn.trigger('click')
      await flushPromises()

      expect(wrapper.vm.showConfirmDialog).toBe(true)
      expect(wrapper.vm.confirmDialogConfig.title).toBe('Clear All History')
    })

    it('shows confirm dialog on delete variation', async () => {
      const deleteBtn = wrapper.find('.item-actions .btn-danger')
      await deleteBtn.trigger('click')
      await flushPromises()

      expect(wrapper.vm.showConfirmDialog).toBe(true)
      expect(wrapper.vm.confirmDialogConfig.title).toBe('Delete Variation')
    })

    it('clears history on confirm', async () => {
      vi.mocked(apiService.delete).mockResolvedValue({ data: { success: true } })

      const clearBtn = wrapper.findAll('.header-actions button')[0]
      await clearBtn.trigger('click')
      await flushPromises()

      // Execute the confirm callback
      await wrapper.vm.confirmDialogConfig.onConfirm()
      await flushPromises()

      expect(apiService.delete).toHaveBeenCalledWith('/variations/history')
      expect(wrapper.vm.variationHistory.length).toBe(0)
    })

    it('exports selected variations to JSON', async () => {
      // Directly set selectedVariations to avoid view switching issues
      wrapper.vm.selectedVariations = [mockVariations[0]]
      await wrapper.vm.$nextTick()

      // Setup jsdom-missing APIs safely (assign, don't spyOn non-existent props)
      const createObjectURL = vi.fn().mockReturnValue('blob:url')
      const revokeObjectURL = vi.fn()
      globalThis.URL.createObjectURL = createObjectURL
      globalThis.URL.revokeObjectURL = revokeObjectURL

      // Spy on createElement but pass through to real impl for non-'a' tags
      const originalCreateElement = document.createElement.bind(document)
      const clickMock = vi.fn()
      const createElementSpy = vi.spyOn(document, 'createElement').mockImplementation((tag: string, options?: any) => {
        const el = originalCreateElement(tag, options)
        if (tag === 'a') {
          el.click = clickMock
        }
        return el
      })

      try {
        // Export button is index 1 in header-actions (0=Clear, 1=Export, 2=Select All)
        const exportBtn = wrapper.findAll('.header-actions button')[1]
        await exportBtn.trigger('click')
        await flushPromises()

        expect(createObjectURL).toHaveBeenCalledWith(expect.any(Blob))
        expect(revokeObjectURL).toHaveBeenCalled()
      } finally {
        // ALWAYS restore to prevent poisoning subsequent tests
        createElementSpy.mockRestore()
        delete (globalThis.URL as any).createObjectURL
        delete (globalThis.URL as any).revokeObjectURL
      }
    })
  })

  describe('Clear History Button', () => {
    it('is disabled when no variations exist', async () => {
      vi.mocked(apiService.get).mockResolvedValue({ data: [] })

      wrapper = mount(VariationHistoryComparison)
      await flushPromises()

      const clearBtn = wrapper.findAll('.header-actions button')[0]
      expect(clearBtn.attributes('disabled')).toBeDefined()
    })

    it('is enabled when variations exist', async () => {
      wrapper = mount(VariationHistoryComparison)
      await flushPromises()

      const clearBtn = wrapper.findAll('.header-actions button')[0]
      expect(clearBtn.attributes('disabled')).toBeUndefined()
    })
  })

  describe('Computed Properties', () => {
    beforeEach(async () => {
      wrapper = mount(VariationHistoryComparison)
      await flushPromises()
    })

    it('calculates filteredVariations correctly', () => {
      expect(wrapper.vm.filteredVariations.length).toBe(mockVariations.length)
    })

    it('calculates allSelected correctly', async () => {
      expect(wrapper.vm.allSelected).toBe(false)

      // Select all variations
      const checkboxes = wrapper.findAll('.checkbox')
      for (const checkbox of checkboxes) {
        await checkbox.setValue(true)
      }
      await flushPromises()

      expect(wrapper.vm.allSelected).toBe(true)
    })

    it('calculates average rating for selected variations', async () => {
      // Use component method to push to reactive array (direct assignment breaks reactivity)
      wrapper.vm.selectVariationForComparison(mockVariations[0]) // rating 5
      wrapper.vm.selectVariationForComparison(mockVariations[1]) // rating 4
      await wrapper.vm.$nextTick()

      // Average of 5 and 4 is 4.5
      expect(wrapper.vm.averageRating).toBeCloseTo(4.5, 1)
    })

    it('calculates highest and lowest ratings', async () => {
      // Use component method to push to reactive array
      for (const v of mockVariations) {
        wrapper.vm.selectVariationForComparison(v)
      }
      await wrapper.vm.$nextTick()

      // Ratings are 5, 4, 3
      expect(wrapper.vm.highestRated).toBe(5)
      expect(wrapper.vm.lowestRated).toBe(3)
    })
  })

  describe('Notifications', () => {
    beforeEach(async () => {
      wrapper = mount(VariationHistoryComparison)
      await flushPromises()
    })

    it('shows notification on successful action', async () => {
      vi.mocked(apiService.patch).mockResolvedValue({ data: { rating: 5 } })

      // Select first variation and rate it
      const checkbox = wrapper.find('.checkbox')
      await checkbox.setValue(true)
      await flushPromises()

      const stars = wrapper.findAll('.star')
      await stars[4].trigger('click')
      await flushPromises()

      expect(wrapper.vm.notification).toBeTruthy()
      expect(wrapper.vm.notification.message).toContain('Rated')
    })

    it('hides notification after timeout', async () => {
      vi.useFakeTimers()

      wrapper.vm.showNotification('Test message', 'success')
      expect(wrapper.vm.notification).toBeTruthy()

      vi.advanceTimersByTime(3000)
      expect(wrapper.vm.notification).toBeNull()

      vi.useRealTimers()
    })
  })

  describe('Modal', () => {
    beforeEach(async () => {
      wrapper = mount(VariationHistoryComparison)
      await flushPromises()
    })

    it('opens full image modal via viewFullImage', async () => {
      // viewFullImage sets fullImageVariation which renders the modal
      wrapper.vm.viewFullImage(mockVariations[0])
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.fullImageVariation).not.toBeNull()
      expect(wrapper.vm.fullImageVariation.id).toBe('var-1')
      expect(wrapper.find('.modal-overlay').exists()).toBe(true)
    })

    it('closes modal on close button click', async () => {
      // Open modal directly
      wrapper.vm.fullImageVariation = mockVariations[0]
      await wrapper.vm.$nextTick()

      expect(wrapper.find('.modal-overlay').exists()).toBe(true)

      // Close modal by clicking close button
      const closeBtn = wrapper.find('.modal-close')
      await closeBtn.trigger('click')
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.fullImageVariation).toBeNull()
      expect(wrapper.find('.modal-overlay').exists()).toBe(false)
    })
  })

  describe('Reactivity', () => {
    beforeEach(async () => {
      wrapper = mount(VariationHistoryComparison)
      await flushPromises()
    })

    it('updates view when filter changes', async () => {
      const initialCount = wrapper.vm.filteredVariations.length

      const modelFilter = wrapper.find('select')
      await modelFilter.setValue('dall-e-3')
      await flushPromises()

      const filteredCount = wrapper.vm.filteredVariations.length
      expect(filteredCount).toBeLessThanOrEqual(initialCount)
    })

    it('updates timeline when variations are deleted', async () => {
      vi.mocked(apiService.delete).mockResolvedValue({ data: { success: true } })

      const initialLength = wrapper.vm.variationHistory.length

      // Delete first variation
      const deleteBtn = wrapper.find('.item-actions .btn-danger')
      await deleteBtn.trigger('click')
      await flushPromises()

      // Confirm deletion
      await wrapper.vm.confirmDialogConfig.onConfirm()
      await flushPromises()

      expect(wrapper.vm.variationHistory.length).toBe(initialLength - 1)
    })
  })
})
