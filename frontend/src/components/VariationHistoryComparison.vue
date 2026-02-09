<template>
  <div class="variation-history-container">
    <!-- Header -->
    <div class="history-header">
      <h2>Variation History & Comparison</h2>
      <div class="header-actions">
        <button
          @click="clearHistory"
          class="btn btn-secondary"
          :disabled="isLoading || variationHistory.length === 0"
        >
          <span class="icon">🗑️</span> Clear History
        </button>
        <button
          @click="exportComparison"
          class="btn btn-secondary"
          :disabled="isLoading || selectedVariations.length === 0"
        >
          <span class="icon">📥</span> Export Selected
        </button>
        <button
          @click="toggleSelectAll"
          class="btn btn-secondary"
          :disabled="isLoading || variationHistory.length === 0"
        >
          {{ allSelected ? 'Deselect All' : 'Select All' }}
        </button>
      </div>
    </div>

    <!-- Timeline/Filter View -->
    <div class="history-controls">
      <div class="filter-group">
        <label>Filter by Model:</label>
        <select v-model="filterModel" class="filter-select">
          <option value="">All Models</option>
          <option value="dall-e-3">DALL-E 3</option>
          <option value="midjourney">Midjourney</option>
          <option value="stable-diffusion">Stable Diffusion</option>
          <option value="flux">Flux</option>
        </select>
      </div>

      <div class="filter-group">
        <label>Filter by Date:</label>
        <select v-model="filterDate" class="filter-select">
          <option value="">All Time</option>
          <option value="today">Today</option>
          <option value="week">This Week</option>
          <option value="month">This Month</option>
        </select>
      </div>

      <div class="filter-group">
        <label>Sort by:</label>
        <select v-model="sortBy" class="filter-select">
          <option value="newest">Newest First</option>
          <option value="oldest">Oldest First</option>
          <option value="model">Model Name</option>
          <option value="rating">Rating</option>
        </select>
      </div>

      <div class="search-group">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by prompt or notes..."
          class="search-input"
        />
      </div>
    </div>

    <!-- Skeleton Loading -->
    <div v-if="isLoading" class="skeleton-timeline">
      <SkeletonLoader v-for="n in 4" :key="n" variant="row" />
    </div>

    <!-- Empty State -->
    <div v-else-if="filteredVariations.length === 0" class="empty-state">
      <div class="empty-icon">📊</div>
      <h3>No Variations Found</h3>
      <p>Generate variations to see your history here</p>
    </div>

    <!-- Comparison View (when variations selected) -->
    <div v-else-if="selectedVariations.length > 0" class="comparison-view">
      <!-- Comparison Controls -->
      <div class="comparison-controls">
        <h3>Comparing {{ selectedVariations.length }} Variations</h3>
        <button @click="exitComparison" class="btn btn-secondary btn-sm">
          ← Back to History
        </button>
      </div>

      <!-- Side-by-Side Comparison -->
      <div class="comparison-grid">
        <div
          v-for="(variation, index) in selectedVariations"
          :key="variation.id"
          class="comparison-card"
        >
          <!-- Close Button -->
          <button
            @click="deselectVariation(variation.id)"
            class="close-btn"
            title="Remove from comparison"
          >
            ✕
          </button>

          <!-- Image Preview -->
          <div class="image-container">
            <img
              :src="variation.imageUrl"
              :alt="`Variation ${index + 1}`"
              class="variation-image"
              @click="viewFullImage(variation)"
            />
            <div class="image-overlay">
              <button @click="viewFullImage(variation)" class="btn btn-primary btn-sm">
                View Full
              </button>
            </div>
          </div>

          <!-- Metadata -->
          <div class="comparison-meta">
            <div class="meta-item">
              <span class="label">Model:</span>
              <span class="value">{{ variation.model }}</span>
            </div>
            <div class="meta-item">
              <span class="label">Generated:</span>
              <span class="value">{{ formatDateTime(variation.createdAt) }}</span>
            </div>
            <div class="meta-item">
              <span class="label">Seed:</span>
              <span class="value mono">{{ variation.seed }}</span>
            </div>
            <div class="meta-item">
              <span class="label">Resolution:</span>
              <span class="value">{{ variation.width }}×{{ variation.height }}</span>
            </div>
          </div>

          <!-- Rating -->
          <div class="rating-section">
            <label>Rating:</label>
            <div class="star-rating">
              <button
                v-for="star in 5"
                :key="star"
                @click="rateVariation(variation.id, star)"
                class="star"
                :class="{ active: star <= (variation.rating || 0) }"
                title="`Rate ${star} stars`"
              >
                ★
              </button>
            </div>
            <span v-if="variation.rating" class="rating-value">
              {{ variation.rating }}/5
            </span>
          </div>

          <!-- Prompt & Notes -->
          <div class="prompt-section">
            <h4>Prompt</h4>
            <p class="prompt-text">{{ variation.prompt }}</p>
          </div>

          <div class="notes-section">
            <label>Notes:</label>
            <textarea
              :value="variation.notes || ''"
              @input="updateNotes(variation.id, $event.target.value)"
              placeholder="Add notes about this variation..."
              class="notes-input"
              rows="3"
            />
          </div>

          <!-- Actions -->
          <div class="comparison-actions">
            <button @click="downloadVariation(variation)" class="btn btn-primary btn-sm">
              📥 Download
            </button>
            <button @click="duplicateVariation(variation)" class="btn btn-secondary btn-sm">
              📋 Duplicate
            </button>
            <button @click="shareVariation(variation)" class="btn btn-secondary btn-sm">
              🔗 Share
            </button>
            <button
              @click="deleteVariation(variation.id)"
              class="btn btn-danger btn-sm"
            >
              🗑️ Delete
            </button>
          </div>
        </div>
      </div>

      <!-- Detailed Analysis Section -->
      <div class="analysis-section">
        <h3>Comparative Analysis</h3>
        <div class="analysis-grid">
          <!-- Model Comparison -->
          <div class="analysis-card">
            <h4>Models Used</h4>
            <div class="analysis-content">
              <div v-for="model in getUniqueModels()" :key="model" class="analysis-item">
                <span class="model-badge">{{ model }}</span>
                <span class="count">
                  {{ selectedVariations.filter(v => v.model === model).length }}
                </span>
              </div>
            </div>
          </div>

          <!-- Rating Comparison -->
          <div class="analysis-card">
            <h4>Rating Statistics</h4>
            <div class="analysis-content">
              <div class="stat-item">
                <span class="stat-label">Average Rating:</span>
                <span class="stat-value">{{ averageRating.toFixed(1) }}/5</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Highest Rated:</span>
                <span class="stat-value">{{ highestRated }}/5</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Lowest Rated:</span>
                <span class="stat-value">{{ lowestRated }}/5</span>
              </div>
            </div>
          </div>

          <!-- Generation Details -->
          <div class="analysis-card">
            <h4>Generation Timeline</h4>
            <div class="analysis-content">
              <div class="stat-item">
                <span class="stat-label">Latest:</span>
                <span class="stat-value">{{ formatDate(latestGeneration) }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Earliest:</span>
                <span class="stat-value">{{ formatDate(earliestGeneration) }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Span:</span>
                <span class="stat-value">{{ generationSpan }}</span>
              </div>
            </div>
          </div>

          <!-- Resolution Analysis -->
          <div class="analysis-card">
            <h4>Resolutions</h4>
            <div class="analysis-content">
              <div v-for="res in getUniqueResolutions()" :key="res" class="analysis-item">
                <span class="resolution-badge">{{ res }}</span>
                <span class="count">
                  {{ selectedVariations.filter(v => `${v.width}×${v.height}` === res).length }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Timeline/List View -->
    <div v-else class="history-timeline">
      <div class="timeline-items">
        <div
          v-for="variation in filteredVariations"
          :key="variation.id"
          class="timeline-item"
          :class="{ selected: isVariationSelected(variation.id) }"
        >
          <!-- Selection Checkbox -->
          <div class="item-select">
            <input
              type="checkbox"
              :checked="isVariationSelected(variation.id)"
              @change="toggleVariationSelect(variation.id)"
              class="checkbox"
            />
          </div>

          <!-- Thumbnail -->
          <div class="item-thumbnail">
            <img
              :src="variation.imageUrl"
              :alt="variation.model"
              class="thumbnail"
            />
          </div>

          <!-- Content -->
          <div class="item-content">
            <div class="content-header">
              <h4>{{ variation.model }}</h4>
              <span class="time-badge">{{ formatTime(variation.createdAt) }}</span>
            </div>

            <div class="content-details">
              <p class="prompt-preview">{{ variation.prompt.substring(0, 120) }}...</p>

              <div class="item-badges">
                <span v-if="variation.rating" class="badge rating">
                  ⭐ {{ variation.rating }}/5
                </span>
                <span class="badge seed">
                  Seed: {{ variation.seed }}
                </span>
                <span class="badge resolution">
                  {{ variation.width }}×{{ variation.height }}
                </span>
              </div>

              <div v-if="variation.notes" class="notes-preview">
                {{ variation.notes.substring(0, 80) }}...
              </div>
            </div>
          </div>

          <!-- Quick Actions -->
          <div class="item-actions">
            <button
              @click="selectVariationForComparison(variation)"
              class="btn btn-primary btn-sm"
              title="Add to comparison"
            >
              Compare
            </button>
            <button
              @click="downloadVariation(variation)"
              class="btn btn-secondary btn-sm"
              title="Download"
            >
              📥
            </button>
            <button
              @click="shareVariation(variation)"
              class="btn btn-secondary btn-sm"
              title="Share"
            >
              🔗
            </button>
            <button
              @click="deleteVariation(variation.id)"
              class="btn btn-danger btn-sm"
              title="Delete"
            >
              🗑️
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Full Image Modal -->
    <div v-if="fullImageVariation" class="modal-overlay" @click.self="fullImageVariation = null">
      <div class="modal-content image-modal">
        <button @click="fullImageVariation = null" class="modal-close">✕</button>
        <div class="modal-image-container">
          <img :src="fullImageVariation.imageUrl" :alt="fullImageVariation.model" />
        </div>
        <div class="modal-image-info">
          <h4>{{ fullImageVariation.model }}</h4>
          <p>{{ fullImageVariation.prompt }}</p>
          <button @click="downloadVariation(fullImageVariation)" class="btn btn-primary">
            Download Full Resolution
          </button>
        </div>
      </div>
    </div>

    <!-- Toast Notifications -->
    <div v-if="notification" class="toast" :class="notification.type">
      {{ notification.message }}
    </div>

    <!-- Confirm Dialog -->
    <ConfirmDialog
      :visible="showConfirmDialog"
      :title="confirmDialogConfig.title"
      :message="confirmDialogConfig.message"
      :confirmText="confirmDialogConfig.confirmText"
      :cancelText="confirmDialogConfig.cancelText"
      :destructive="confirmDialogConfig.destructive"
      @update:visible="showConfirmDialog = $event"
      @confirm="confirmDialogConfig.onConfirm()"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiService } from '../services/api'
import { sampleVariations } from '@/data/mock-data'
import ConfirmDialog from './ConfirmDialog.vue'
import SkeletonLoader from './SkeletonLoader.vue'

const variationHistory = ref([])
const selectedVariations = ref([])
const filterModel = ref('')
const filterDate = ref('')
const sortBy = ref('newest')
const searchQuery = ref('')
const isLoading = ref(false)
const fullImageVariation = ref(null)
const notification = ref(null)

const showConfirmDialog = ref(false)
const confirmDialogConfig = ref({
  title: '',
  message: '',
  confirmText: 'Confirm',
  cancelText: 'Cancel',
  destructive: false,
  onConfirm: () => {},
})

// Computed properties
const filteredVariations = computed(() => {
  let results = [...variationHistory.value]

  // Apply model filter
  if (filterModel.value) {
    results = results.filter(v => v.model === filterModel.value)
  }

  // Apply date filter
  if (filterDate.value) {
    const now = new Date()
    const item = results.filter(v => {
      const itemDate = new Date(v.createdAt)
      if (filterDate.value === 'today') {
        return itemDate.toDateString() === now.toDateString()
      } else if (filterDate.value === 'week') {
        const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
        return itemDate >= weekAgo
      } else if (filterDate.value === 'month') {
        const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
        return itemDate >= monthAgo
      }
      return true
    })
    results = item
  }

  // Apply search filter
  if (searchQuery.value) {
    results = results.filter(v =>
      v.prompt.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      (v.notes && v.notes.toLowerCase().includes(searchQuery.value.toLowerCase()))
    )
  }

  // Apply sorting
  results.sort((a, b) => {
    switch (sortBy.value) {
      case 'newest':
        return new Date(b.createdAt) - new Date(a.createdAt)
      case 'oldest':
        return new Date(a.createdAt) - new Date(b.createdAt)
      case 'model':
        return a.model.localeCompare(b.model)
      case 'rating':
        return (b.rating || 0) - (a.rating || 0)
      default:
        return 0
    }
  })

  return results
})

const allSelected = computed(() => {
  return filteredVariations.value.length > 0 &&
    filteredVariations.value.every(v => isVariationSelected(v.id))
})

const averageRating = computed(() => {
  if (selectedVariations.value.length === 0) return 0
  const sum = selectedVariations.value.reduce((acc, v) => acc + (v.rating || 0), 0)
  return sum / selectedVariations.value.length
})

const highestRated = computed(() => {
  if (selectedVariations.value.length === 0) return 0
  return Math.max(...selectedVariations.value.map(v => v.rating || 0))
})

const lowestRated = computed(() => {
  if (selectedVariations.value.length === 0) return 0
  const ratings = selectedVariations.value.map(v => v.rating || 0).filter(r => r > 0)
  return ratings.length > 0 ? Math.min(...ratings) : 0
})

const latestGeneration = computed(() => {
  if (selectedVariations.value.length === 0) return ''
  return new Date(Math.max(...selectedVariations.value.map(v => new Date(v.createdAt))))
})

const earliestGeneration = computed(() => {
  if (selectedVariations.value.length === 0) return ''
  return new Date(Math.min(...selectedVariations.value.map(v => new Date(v.createdAt))))
})

const generationSpan = computed(() => {
  if (selectedVariations.value.length < 2) return 'N/A'
  const latest = new Date(latestGeneration.value)
  const earliest = new Date(earliestGeneration.value)
  const diffMs = latest - earliest
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  if (diffDays === 0) return 'Same day'
  return `${diffDays} day${diffDays > 1 ? 's' : ''}`
})

// Methods
const loadHistory = async () => {
  isLoading.value = true
  try {
    const response = await apiService.get('/variations/history')
    variationHistory.value = response.data || []
  } catch (error) {
    console.warn('API unavailable, using sample data')
    variationHistory.value = sampleVariations
    showNotification('Showing sample variations (API offline)', 'info')
  } finally {
    isLoading.value = false
  }
}

const isVariationSelected = (variationId) => {
  return selectedVariations.value.some(v => v.id === variationId)
}

const toggleVariationSelect = (variationId) => {
  const variation = variationHistory.value.find(v => v.id === variationId)
  if (!variation) return

  const index = selectedVariations.value.findIndex(v => v.id === variationId)
  if (index > -1) {
    selectedVariations.value.splice(index, 1)
  } else {
    selectedVariations.value.push(variation)
  }
}

const selectVariationForComparison = (variation) => {
  if (!isVariationSelected(variation.id)) {
    selectedVariations.value.push(variation)
  }
}

const deselectVariation = (variationId) => {
  selectedVariations.value = selectedVariations.value.filter(v => v.id !== variationId)
}

const toggleSelectAll = () => {
  if (allSelected.value) {
    selectedVariations.value = []
  } else {
    selectedVariations.value = [...filteredVariations.value]
  }
}

const exitComparison = () => {
  selectedVariations.value = []
}

const rateVariation = async (variationId, rating) => {
  const variation = variationHistory.value.find(v => v.id === variationId)
  if (!variation) return

  try {
    await apiService.patch(`/variations/${variationId}`, { rating })
    variation.rating = rating
    showNotification(`Rated ${rating} stars`, 'success')
  } catch (error) {
    showNotification('Failed to save rating', 'error')
    console.error(error)
  }
}

const updateNotes = async (variationId, notes) => {
  const variation = variationHistory.value.find(v => v.id === variationId)
  if (!variation) return

  try {
    await apiService.patch(`/variations/${variationId}`, { notes })
    variation.notes = notes
  } catch (error) {
    showNotification('Failed to save notes', 'error')
    console.error(error)
  }
}

const downloadVariation = (variation) => {
  const link = document.createElement('a')
  link.href = variation.imageUrl
  link.download = `variation-${variation.id}-${variation.model}.png`
  link.click()
  showNotification('Download started', 'success')
}

const duplicateVariation = (variation) => {
  const event = new CustomEvent('variation-selected', {
    detail: { variation },
    bubbles: true,
  })
  window.dispatchEvent(event)
  showNotification('Variation ready to regenerate', 'success')
}

const shareVariation = (variation) => {
  const shareUrl = `${window.location.origin}/share/variation/${variation.id}`
  navigator.clipboard.writeText(shareUrl)
  showNotification('Share link copied to clipboard', 'success')
}

const deleteVariation = (variationId) => {
  confirmDialogConfig.value = {
    title: 'Delete Variation',
    message: 'This variation will be permanently deleted.',
    confirmText: 'Delete',
    cancelText: 'Keep',
    destructive: true,
    onConfirm: async () => {
      try {
        await apiService.delete(`/variations/${variationId}`)
        variationHistory.value = variationHistory.value.filter(v => v.id !== variationId)
        selectedVariations.value = selectedVariations.value.filter(v => v.id !== variationId)
        showNotification('Variation deleted', 'success')
      } catch (error) {
        showNotification('Failed to delete variation', 'error')
        console.error(error)
      }
    },
  }
  showConfirmDialog.value = true
}

const clearHistory = () => {
  confirmDialogConfig.value = {
    title: 'Clear All History',
    message: 'All variation history, ratings, and notes will be permanently deleted. This cannot be undone.',
    confirmText: 'Clear Everything',
    cancelText: 'Cancel',
    destructive: true,
    onConfirm: async () => {
      try {
        await apiService.delete('/variations/history')
        variationHistory.value = []
        selectedVariations.value = []
        showNotification('History cleared', 'success')
      } catch (error) {
        showNotification('Failed to clear history', 'error')
        console.error(error)
      }
    },
  }
  showConfirmDialog.value = true
}

const exportComparison = () => {
  const dataStr = JSON.stringify(selectedVariations.value, null, 2)
  const dataBlob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(dataBlob)
  const link = document.createElement('a')
  link.href = url
  link.download = `comparison-${new Date().toISOString().split('T')[0]}.json`
  link.click()
  URL.revokeObjectURL(url)
  showNotification('Comparison exported', 'success')
}

const viewFullImage = (variation) => {
  fullImageVariation.value = variation
}

const getUniqueModels = () => {
  const models = new Set(selectedVariations.value.map(v => v.model))
  return Array.from(models)
}

const getUniqueResolutions = () => {
  const resolutions = new Set(selectedVariations.value.map(v => `${v.width}×${v.height}`))
  return Array.from(resolutions)
}

const formatDateTime = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const formatDate = (date) => {
  if (!date) return ''
  return new Date(date).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

const formatTime = (date) => {
  if (!date) return ''
  const now = new Date()
  const itemDate = new Date(date)
  const diffMs = now - itemDate
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return itemDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

const showNotification = (message, type = 'info') => {
  notification.value = { message, type }
  setTimeout(() => {
    notification.value = null
  }, 3000)
}

// Lifecycle
onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.variation-history-container {
  padding: var(--space-8);
  max-width: 1400px;
  margin: 0 auto;
  background: linear-gradient(135deg, var(--color-content-bg-start) 0%, var(--color-content-bg-end) 100%);
  min-height: 100vh;
}

/* Header */
.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-8);
  background: var(--color-surface-primary);
  padding: var(--space-6);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
}

.history-header h2 {
  margin: 0;
  font-size: 1.8rem;
  color: var(--color-text-primary);
}

.header-actions {
  display: flex;
  gap: var(--space-4);
}

/* Controls */
.history-controls {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-8);
  background: var(--color-surface-primary);
  padding: var(--space-6);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
}

.filter-group,
.search-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.filter-group label,
.search-group label {
  font-weight: 500;
  color: var(--color-text-primary);
  font-size: 0.9rem;
}

.filter-select,
.search-input {
  padding: 0.625rem;
  border: 2px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  font-size: 0.95rem;
  transition: all var(--transition-slow) ease;
}

.filter-select:focus,
.search-input:focus {
  outline: none;
  border-color: var(--color-success);
  box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.1);
}

.search-group {
  grid-column: 1 / -1;
}

/* Buttons */
.btn {
  padding: 0.625rem var(--space-5);
  border: none;
  border-radius: var(--radius-lg);
  font-size: var(--text-base);
  cursor: pointer;
  transition: all var(--transition-slow) ease;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--color-success);
  color: var(--color-surface-primary);
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-success-hover);
  box-shadow: 0 4px 8px rgba(76, 175, 80, 0.3);
}

.btn-secondary {
  background: var(--color-surface-subtle);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border-light);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--color-border-light);
}

.btn-danger {
  background: var(--color-danger);
  color: var(--color-surface-primary);
}

.btn-danger:hover:not(:disabled) {
  background: var(--color-danger-hover);
}

.btn-sm {
  padding: var(--space-2) 0.875rem;
  font-size: 0.85rem;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 4rem var(--space-8);
  background: var(--color-surface-primary);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
}

.empty-icon {
  font-size: var(--text-3xl);
  margin-bottom: var(--space-4);
}

.empty-state h3 {
  margin: 0 0 var(--space-2) 0;
  color: var(--color-text-primary);
}

.empty-state p {
  margin: 0;
  color: var(--color-text-tertiary);
}

/* Timeline/List View */
.history-timeline {
  display: flex;
  flex-direction: column;
}

.timeline-items {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.timeline-item {
  display: grid;
  grid-template-columns: auto 120px 1fr auto;
  gap: var(--space-6);
  align-items: center;
  background: var(--color-surface-primary);
  padding: var(--space-6);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
  transition: all var(--transition-slow) ease;
}

.timeline-item:hover {
  box-shadow: var(--shadow-lg);
}

.timeline-item.selected {
  background: #f0f8f4;
  border-left: 4px solid var(--color-success);
}

.item-select {
  display: flex;
  align-items: center;
  justify-content: center;
}

.checkbox {
  width: 20px;
  height: 20px;
  cursor: pointer;
}

.item-thumbnail {
  position: relative;
  width: 120px;
  height: 120px;
  overflow: hidden;
  border-radius: var(--radius-lg);
}

.thumbnail {
  width: 100%;
  height: 100%;
  object-fit: cover;
  cursor: pointer;
  transition: transform var(--transition-slow) ease;
}

.thumbnail:hover {
  transform: scale(1.05);
}

.item-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.content-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.content-header h4 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: 1.1rem;
}

.time-badge {
  background: var(--color-surface-subtle);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-pill);
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.content-details {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.prompt-preview {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 0.95rem;
  line-height: 1.4;
}

.item-badges {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.badge {
  display: inline-block;
  padding: var(--space-1) var(--space-3);
  background: var(--color-surface-subtle);
  border-radius: var(--radius-xl);
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.badge.rating {
  background: var(--color-warning-surface);
  color: var(--color-warning-text);
}

.badge.seed {
  background: var(--color-primary-light);
  color: #1565c0;
  font-family: var(--font-mono);
  font-size: 0.8rem;
}

.badge.resolution {
  background: #f3e5f5;
  color: #6a1b9a;
}

.notes-preview {
  font-size: 0.9rem;
  color: var(--color-text-tertiary);
  font-style: italic;
  margin: 0;
}

.item-actions {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  justify-content: flex-end;
}

/* Comparison View */
.comparison-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-8);
  background: var(--color-surface-primary);
  padding: var(--space-6);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
}

.comparison-controls h3 {
  margin: 0;
  color: var(--color-text-primary);
}

.comparison-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--space-8);
  margin-bottom: var(--space-12);
}

.comparison-card {
  background: var(--color-surface-primary);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-md);
  display: flex;
  flex-direction: column;
  position: relative;
}

.close-btn {
  position: absolute;
  top: var(--space-2);
  right: var(--space-2);
  background: var(--color-surface-overlay);
  color: var(--color-surface-primary);
  border: none;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  cursor: pointer;
  font-size: 1.2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-slow) ease;
  z-index: 10;
}

.close-btn:hover {
  background: rgba(0, 0, 0, 0.7);
}

.image-container {
  position: relative;
  width: 100%;
  aspect-ratio: 1;
  overflow: hidden;
}

.variation-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  cursor: pointer;
}

.image-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background var(--transition-slow) ease;
  opacity: 0;
}

.image-container:hover .image-overlay {
  background: var(--color-surface-overlay);
  opacity: 1;
}

.comparison-meta {
  padding: var(--space-6) var(--space-6) 0 var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.meta-item {
  display: flex;
  justify-content: space-between;
  font-size: 0.95rem;
}

.meta-item .label {
  font-weight: 500;
  color: var(--color-text-secondary);
}

.meta-item .value {
  color: var(--color-text-primary);
}

.meta-item .value.mono {
  font-family: var(--font-mono);
  font-size: 0.85rem;
}

.rating-section {
  padding: var(--space-4) var(--space-6);
  border-top: 1px solid var(--color-surface-subtle);
  border-bottom: 1px solid var(--color-surface-subtle);
}

.rating-section label {
  display: block;
  font-weight: 500;
  margin-bottom: var(--space-2);
  color: var(--color-text-primary);
  font-size: 0.9rem;
}

.star-rating {
  display: flex;
  gap: var(--space-1);
  margin-bottom: var(--space-2);
}

.star {
  background: none;
  border: none;
  font-size: var(--text-2xl);
  cursor: pointer;
  opacity: 0.3;
  transition: all var(--transition-slow) ease;
  padding: 0;
}

.star:hover,
.star.active {
  opacity: 1;
  color: var(--color-star);
}

.rating-value {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.prompt-section,
.notes-section {
  padding: 0 var(--space-6);
}

.prompt-section {
  padding-top: var(--space-4);
}

.notes-section {
  padding-bottom: var(--space-4);
}

.prompt-section h4,
.notes-section label {
  margin: 0 0 var(--space-2) 0;
  font-weight: 500;
  color: var(--color-text-primary);
  font-size: 0.9rem;
}

.prompt-text {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 0.95rem;
  line-height: 1.4;
  background: var(--color-surface-tertiary);
  padding: var(--space-3);
  border-radius: var(--radius-md);
}

.notes-input {
  width: 100%;
  padding: var(--space-3);
  border: 2px solid var(--color-border-light);
  border-radius: var(--radius-md);
  font-size: 0.95rem;
  font-family: inherit;
  resize: vertical;
  transition: all var(--transition-slow) ease;
}

.notes-input:focus {
  outline: none;
  border-color: var(--color-success);
  box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.1);
}

.comparison-actions {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-6);
  border-top: 1px solid var(--color-surface-subtle);
  flex-wrap: wrap;
}

.comparison-actions .btn {
  flex: 1;
  min-width: 100px;
  justify-content: center;
}

/* Analysis Section */
.analysis-section {
  background: var(--color-surface-primary);
  padding: var(--space-8);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
}

.analysis-section h3 {
  margin-top: 0;
  color: var(--color-text-primary);
}

.analysis-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--space-6);
  margin-top: var(--space-6);
}

.analysis-card {
  background: var(--color-surface-tertiary);
  padding: var(--space-6);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
}

.analysis-card h4 {
  margin-top: 0;
  color: var(--color-text-primary);
  margin-bottom: var(--space-4);
}

.analysis-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.analysis-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.model-badge,
.resolution-badge {
  background: var(--color-primary-light);
  color: #1565c0;
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
  font-weight: 500;
}

.count {
  background: var(--color-warning-surface);
  color: var(--color-warning-text);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-sm);
  font-weight: 600;
  font-size: 0.9rem;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--color-border-light);
}

.stat-item:last-child {
  border-bottom: none;
}

.stat-label {
  color: var(--color-text-secondary);
  font-weight: 500;
}

.stat-value {
  color: var(--color-text-primary);
  font-weight: 600;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--color-surface-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal-backdrop);
}

.modal-content {
  background: var(--color-surface-primary);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-2xl);
}

.image-modal {
  max-width: 800px;
  width: 90%;
  position: relative;
}

.modal-close {
  position: absolute;
  top: var(--space-4);
  right: var(--space-4);
  background: var(--color-surface-overlay);
  color: var(--color-surface-primary);
  border: none;
  width: 40px;
  height: 40px;
  border-radius: var(--radius-full);
  cursor: pointer;
  font-size: var(--text-2xl);
  z-index: var(--z-modal);
  transition: all var(--transition-slow) ease;
}

.modal-close:hover {
  background: rgba(0, 0, 0, 0.7);
}

.modal-image-container {
  width: 100%;
  max-height: 60vh;
  overflow: hidden;
  background: #000;
}

.modal-image-container img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.modal-image-info {
  padding: var(--space-8);
}

.modal-image-info h4 {
  margin-top: 0;
  color: var(--color-text-primary);
}

.modal-image-info p {
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: var(--space-6);
}

/* Toast */
.toast {
  position: fixed;
  bottom: var(--space-8);
  right: var(--space-8);
  padding: var(--space-4) var(--space-6);
  background: var(--color-text-primary);
  color: var(--color-surface-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-toast);
  animation: slideIn var(--transition-slow) ease;
  z-index: var(--z-toast);
}

.toast.success {
  background: var(--color-success);
}

.toast.error {
  background: var(--color-danger);
}

.toast.info {
  background: var(--color-primary);
}

@keyframes slideIn {
  from {
    transform: translateX(400px);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

/* Skeleton Loading */
.skeleton-timeline {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding: var(--space-4);
}

/* Responsive */
@media (max-width: 1024px) {
  .comparison-grid {
    grid-template-columns: 1fr;
  }

  .timeline-item {
    grid-template-columns: auto 100px 1fr;
    gap: var(--space-4);
  }

  .item-actions {
    grid-column: 1 / -1;
    margin-top: var(--space-4);
  }
}

@media (max-width: 768px) {
  .variation-history-container {
    padding: var(--space-4);
  }

  .history-header {
    flex-direction: column;
    gap: var(--space-4);
    text-align: center;
  }

  .history-header h2 {
    font-size: var(--text-2xl);
  }

  .header-actions {
    width: 100%;
    justify-content: center;
    flex-wrap: wrap;
  }

  .history-controls {
    grid-template-columns: 1fr;
  }

  .search-group {
    grid-column: auto;
  }

  .timeline-item {
    grid-template-columns: auto 80px 1fr;
  }

  .item-thumbnail {
    width: 80px;
    height: 80px;
  }

  .item-actions {
    gap: var(--space-1);
  }

  .item-actions .btn {
    flex: 1;
    min-width: 50px;
    padding: var(--space-2);
    font-size: 0.8rem;
  }

  .analysis-grid {
    grid-template-columns: 1fr;
  }

  @media (max-width: 480px) {
    .history-controls {
      gap: var(--space-3);
    }

    .timeline-item {
      gap: var(--space-3);
      padding: var(--space-4);
    }

    .item-content {
      gap: var(--space-2);
    }

    .item-badges {
      gap: var(--space-1);
    }

    .badge {
      font-size: var(--text-xs);
      padding: 0.2rem var(--space-2);
    }

    .item-actions {
      gap: var(--space-1);
    }

    .toast {
      left: var(--space-4);
      right: var(--space-4);
      bottom: var(--space-4);
    }
  }
}
</style>
