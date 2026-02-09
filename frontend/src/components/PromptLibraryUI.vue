<template>
  <div class="prompt-library-container">
    <!-- Header with title and actions -->
    <div class="library-header">
      <h2>Prompt Library</h2>
      <div class="header-actions">
        <button 
          @click="showNewPromptForm = true" 
          class="btn btn-primary"
          :disabled="isLoading"
        >
          <span class="icon">+</span> New Prompt
        </button>
        <button 
          @click="exportLibrary" 
          class="btn btn-secondary"
          :disabled="isLoading || savedPrompts.length === 0"
        >
          <span class="icon">📥</span> Export
        </button>
        <button 
          @click="toggleView" 
          class="btn btn-secondary"
          :title="`Switch to ${viewMode === 'grid' ? 'list' : 'grid'} view`"
        >
          <span class="icon">{{ viewMode === 'grid' ? '☰' : '⊞' }}</span>
        </button>
      </div>
    </div>

    <!-- Search and Filter -->
    <div class="library-controls">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search prompts by name or tags..."
        class="search-input"
      />
      <div class="filter-tags">
        <span 
          v-for="tag in availableTags" 
          :key="tag"
          @click="toggleTagFilter(tag)"
          class="filter-tag"
          :class="{ active: selectedTags.includes(tag) }"
        >
          {{ tag }}
        </span>
      </div>
    </div>

    <!-- New/Edit Prompt Form (Modal) -->
    <div v-if="showNewPromptForm" class="modal-overlay" @click.self="closeForm">
      <div class="modal-content prompt-form">
        <h3>{{ editingPrompt ? 'Edit Prompt' : 'Create New Prompt' }}</h3>
        
        <div class="form-group">
          <label>Prompt Name *</label>
          <input
            v-model="formData.name"
            type="text"
            placeholder="e.g., Watercolor Landscape"
            class="form-input"
          />
          <span v-if="formErrors.name" class="error-text">{{ formErrors.name }}</span>
        </div>

        <div class="form-group">
          <label>Prompt Text *</label>
          <textarea
            v-model="formData.promptText"
            placeholder="Enter your detailed prompt here..."
            class="form-textarea"
            rows="6"
          />
          <div class="char-count">{{ formData.promptText.length }}/2000</div>
          <span v-if="formErrors.promptText" class="error-text">{{ formErrors.promptText }}</span>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>Category</label>
            <select v-model="formData.category" class="form-select">
              <option value="">-- Select Category --</option>
              <option value="landscape">Landscape</option>
              <option value="portrait">Portrait</option>
              <option value="abstract">Abstract</option>
              <option value="animals">Animals</option>
              <option value="patterns">Patterns</option>
              <option value="other">Other</option>
            </select>
          </div>

          <div class="form-group">
            <label>Tags (comma-separated)</label>
            <input
              v-model="formData.tags"
              type="text"
              placeholder="e.g., watercolor, nature, peaceful"
              class="form-input"
            />
          </div>
        </div>

        <div class="form-group">
          <label>
            <input type="checkbox" v-model="formData.isPublic" />
            Make Public (shareable)
          </label>
          <p class="help-text">Public prompts can be shared with other users</p>
        </div>

        <div class="form-actions">
          <button @click="closeForm" class="btn btn-secondary">Cancel</button>
          <button @click="savePrompt" class="btn btn-primary" :disabled="isSaving">
            {{ isSaving ? 'Saving...' : (editingPrompt ? 'Update Prompt' : 'Create Prompt') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Skeleton Loading -->
    <div v-if="isLoading" class="prompts-container grid">
      <SkeletonLoader v-for="n in 6" :key="n" variant="card" />
    </div>

    <!-- Empty State -->
    <div v-else-if="filteredPrompts.length === 0" class="empty-state">
      <div class="empty-icon">📚</div>
      <h3>No Prompts Found</h3>
      <p v-if="savedPrompts.length === 0">Create your first prompt to get started</p>
      <p v-else>Try adjusting your search or filters</p>
    </div>

    <!-- Prompts Display -->
    <div v-else :class="['prompts-container', viewMode]">
      <!-- Grid View -->
      <div v-if="viewMode === 'grid'" class="prompts-grid">
        <div
          v-for="prompt in filteredPrompts"
          :key="prompt.id"
          class="prompt-card"
        >
          <div class="card-header">
            <h4>{{ prompt.name }}</h4>
            <div class="card-actions">
              <button
                @click="duplicatePrompt(prompt)"
                class="action-btn"
                title="Duplicate"
              >
                📋
              </button>
              <button
                @click="sharePrompt(prompt)"
                class="action-btn"
                :class="{ shared: prompt.isPublic }"
                title="Share"
              >
                🔗
              </button>
              <button
                @click="editPrompt(prompt)"
                class="action-btn"
                title="Edit"
              >
                ✏️
              </button>
              <button
                @click="deletePrompt(prompt.id)"
                class="action-btn delete"
                title="Delete"
              >
                🗑️
              </button>
            </div>
          </div>

          <div class="card-body">
            <p class="prompt-preview">{{ prompt.promptText.substring(0, 150) }}...</p>
            <div class="card-meta">
              <span v-if="prompt.category" class="badge category">
                {{ prompt.category }}
              </span>
              <span class="badge date">
                {{ formatDate(prompt.createdAt) }}
              </span>
            </div>
            <div v-if="prompt.tags && prompt.tags.length" class="card-tags">
              <span v-for="tag in prompt.tags" :key="tag" class="tag">
                #{{ tag }}
              </span>
            </div>
          </div>

          <div class="card-footer">
            <button
              @click="usePrompt(prompt)"
              class="btn btn-primary btn-sm"
            >
              Use This Prompt
            </button>
          </div>
        </div>
      </div>

      <!-- List View -->
      <div v-else class="prompts-list">
        <div
          v-for="prompt in filteredPrompts"
          :key="prompt.id"
          class="prompt-item"
        >
          <div class="item-header">
            <div class="item-info">
              <h4>{{ prompt.name }}</h4>
              <p class="item-preview">{{ prompt.promptText.substring(0, 100) }}...</p>
            </div>
            <div class="item-meta">
              <span v-if="prompt.category" class="badge category">
                {{ prompt.category }}
              </span>
              <span class="badge date">
                {{ formatDate(prompt.createdAt) }}
              </span>
            </div>
          </div>

          <div class="item-actions">
            <button @click="usePrompt(prompt)" class="btn btn-primary btn-sm">
              Use
            </button>
            <button @click="duplicatePrompt(prompt)" class="btn btn-secondary btn-sm">
              Duplicate
            </button>
            <button
              @click="sharePrompt(prompt)"
              class="btn btn-secondary btn-sm"
              :class="{ shared: prompt.isPublic }"
            >
              {{ prompt.isPublic ? 'Public' : 'Share' }}
            </button>
            <button @click="editPrompt(prompt)" class="btn btn-secondary btn-sm">
              Edit
            </button>
            <button
              @click="deletePrompt(prompt.id)"
              class="btn btn-danger btn-sm"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Share Modal -->
    <div v-if="showShareModal && sharingPrompt" class="modal-overlay" @click.self="showShareModal = false">
      <div class="modal-content share-modal">
        <h3>Share Prompt</h3>
        <p class="share-info">{{ sharingPrompt.name }}</p>

        <div class="share-options">
          <div class="share-option">
            <label>
              <input
                type="radio"
                v-model="shareMode"
                value="public"
              />
              Public - Anyone can view and use
            </label>
          </div>
          <div class="share-option">
            <label>
              <input
                type="radio"
                v-model="shareMode"
                value="link"
              />
              Link - Share a direct link
            </label>
          </div>
        </div>

        <div v-if="shareMode === 'link'" class="share-link-box">
          <input
            type="text"
            :value="getShareLink()"
            readonly
            class="share-link-input"
          />
          <button @click="copyShareLink" class="btn btn-secondary btn-sm">
            {{ copiedLink ? '✓ Copied' : 'Copy' }}
          </button>
        </div>

        <div class="form-actions">
          <button @click="showShareModal = false" class="btn btn-secondary">
            Cancel
          </button>
          <button @click="confirmShare" class="btn btn-primary">
            {{ shareMode === 'public' ? 'Make Public' : 'Generate Link' }}
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

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { apiService } from '../services/api'
import { samplePrompts } from '@/data/mock-data'
import type { MockPrompt } from '@/data/mock-data'
import ConfirmDialog from './ConfirmDialog.vue'
import SkeletonLoader from './SkeletonLoader.vue'
import type { Prompt, ConfirmDialogConfig, Notification } from '@/types'

interface FormData {
  name: string
  promptText: string
  category: string
  tags: string
  isPublic: boolean
}

interface FormErrors {
  name?: string
  promptText?: string
}

const savedPrompts = ref<Prompt[]>([])
const searchQuery = ref<string>('')
const selectedTags = ref<string[]>([])
const viewMode = ref<'grid' | 'list'>('grid')
const isLoading = ref<boolean>(false)
const isSaving = ref<boolean>(false)
const showNewPromptForm = ref<boolean>(false)
const showShareModal = ref<boolean>(false)
const sharingPrompt = ref<Prompt | null>(null)
const shareMode = ref<'public' | 'link'>('public')
const copiedLink = ref<boolean>(false)
const editingPrompt = ref<Prompt | null>(null)

const showConfirmDialog = ref<boolean>(false)
const confirmDialogConfig = ref<ConfirmDialogConfig>({
  title: '',
  message: '',
  confirmText: 'Confirm',
  cancelText: 'Cancel',
  destructive: false,
  onConfirm: () => {},
})

const formData = ref<FormData>({
  name: '',
  promptText: '',
  category: '',
  tags: '',
  isPublic: false,
})

const formErrors = ref<FormErrors>({})

const notification = ref<Notification | null>(null)

// Computed properties
const availableTags = computed((): string[] => {
  const tags = new Set<string>()
  savedPrompts.value.forEach((prompt: Prompt) => {
    if (prompt.tags) {
      prompt.tags.forEach((tag: string) => tags.add(tag))
    }
  })
  return Array.from(tags).sort()
})

const filteredPrompts = computed((): Prompt[] => {
  return savedPrompts.value.filter((prompt: Prompt) => {
    const matchesSearch = !searchQuery.value ||
      prompt.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      prompt.promptText.toLowerCase().includes(searchQuery.value.toLowerCase())

    const matchesTags = selectedTags.value.length === 0 ||
      (prompt.tags && selectedTags.value.some((tag: string) => prompt.tags.includes(tag)))

    return matchesSearch && matchesTags
  })
})

// Methods
const loadPrompts = async (): Promise<void> => {
  isLoading.value = true
  try {
    const response = await apiService.get<{ data: Prompt[] }>('/prompts/library')
    savedPrompts.value = response.data || []
  } catch (error: unknown) {
    console.warn('API unavailable, using sample data')
    savedPrompts.value = samplePrompts as Prompt[]
    showNotification('Showing sample prompts (API offline)', 'info')
  } finally {
    isLoading.value = false
  }
}

const savePrompt = async (): Promise<void> => {
  // Validate form
  formErrors.value = {}
  if (!formData.value.name.trim()) {
    formErrors.value.name = 'Prompt name is required'
  }
  if (!formData.value.promptText.trim()) {
    formErrors.value.promptText = 'Prompt text is required'
  }
  if (formData.value.promptText.length > 2000) {
    formErrors.value.promptText = 'Prompt text must be less than 2000 characters'
  }

  if (Object.keys(formErrors.value).length > 0) return

  isSaving.value = true
  try {
    const payload: { name: string; promptText: string; category: string; tags: string[]; isPublic: boolean } = {
      name: formData.value.name,
      promptText: formData.value.promptText,
      category: formData.value.category,
      tags: formData.value.tags.split(',').map((t: string) => t.trim()).filter((t: string) => t),
      isPublic: formData.value.isPublic,
    }

    if (editingPrompt.value) {
      await apiService.put(`/prompts/library/${editingPrompt.value.id}`, payload)
      showNotification('Prompt updated successfully', 'success')
    } else {
      await apiService.post('/prompts/library', payload)
      showNotification('Prompt created successfully', 'success')
    }

    closeForm()
    await loadPrompts()
  } catch (error: unknown) {
    showNotification('Failed to save prompt', 'error')
    console.error(error)
  } finally {
    isSaving.value = false
  }
}

const editPrompt = (prompt: Prompt): void => {
  editingPrompt.value = prompt
  formData.value = {
    name: prompt.name,
    promptText: prompt.promptText,
    category: prompt.category || '',
    tags: (prompt.tags || []).join(', '),
    isPublic: prompt.isPublic,
  }
  showNewPromptForm.value = true
}

const deletePrompt = (promptId: string): void => {
  confirmDialogConfig.value = {
    title: 'Delete Prompt',
    message: 'This prompt will be permanently deleted. This action cannot be undone.',
    confirmText: 'Delete',
    cancelText: 'Keep',
    destructive: true,
    onConfirm: async (): Promise<void> => {
      try {
        await apiService.delete(`/prompts/library/${promptId}`)
        showNotification('Prompt deleted successfully', 'success')
        await loadPrompts()
      } catch (error: unknown) {
        showNotification('Failed to delete prompt', 'error')
        console.error(error)
      }
    },
  }
  showConfirmDialog.value = true
}

const duplicatePrompt = async (prompt: Prompt): Promise<void> => {
  editingPrompt.value = null
  formData.value = {
    name: `${prompt.name} (Copy)`,
    promptText: prompt.promptText,
    category: prompt.category || '',
    tags: (prompt.tags || []).join(', '),
    isPublic: false,
  }
  showNewPromptForm.value = true
}

const usePrompt = (prompt: Prompt): void => {
  // Emit event to parent component with the selected prompt
  const event = new CustomEvent('prompt-selected', {
    detail: { prompt },
    bubbles: true,
  })
  window.dispatchEvent(event)
  showNotification(`Using prompt: ${prompt.name}`, 'success')
}

const sharePrompt = (prompt: Prompt): void => {
  sharingPrompt.value = prompt
  shareMode.value = 'public'
  showShareModal.value = true
}

const confirmShare = async (): Promise<void> => {
  if (!sharingPrompt.value) return

  try {
    await apiService.put(`/prompts/library/${sharingPrompt.value.id}`, {
      isPublic: shareMode.value === 'public',
    })
    showNotification(
      shareMode.value === 'public' ? 'Prompt made public' : 'Share link generated',
      'success'
    )
    showShareModal.value = false
    await loadPrompts()
  } catch (error: unknown) {
    showNotification('Failed to share prompt', 'error')
    console.error(error)
  }
}

const getShareLink = (): string => {
  if (!sharingPrompt.value) return ''
  return `${window.location.origin}/share/prompt/${sharingPrompt.value.id}`
}

const copyShareLink = (): void => {
  const link: string = getShareLink()
  navigator.clipboard.writeText(link)
  copiedLink.value = true
  setTimeout(() => {
    copiedLink.value = false
  }, 2000)
}

const exportLibrary = (): void => {
  const dataStr: string = JSON.stringify(filteredPrompts.value, null, 2)
  const dataBlob: Blob = new Blob([dataStr], { type: 'application/json' })
  const url: string = URL.createObjectURL(dataBlob)
  const link: HTMLAnchorElement = document.createElement('a')
  link.href = url
  link.download = `prompt-library-${new Date().toISOString().split('T')[0]}.json`
  link.click()
  URL.revokeObjectURL(url)
  showNotification('Library exported successfully', 'success')
}

const closeForm = (): void => {
  showNewPromptForm.value = false
  editingPrompt.value = null
  formData.value = {
    name: '',
    promptText: '',
    category: '',
    tags: '',
    isPublic: false,
  }
  formErrors.value = {}
}

const toggleView = (): void => {
  viewMode.value = viewMode.value === 'grid' ? 'list' : 'grid'
}

const toggleTagFilter = (tag: string): void => {
  const index: number = selectedTags.value.indexOf(tag)
  if (index > -1) {
    selectedTags.value.splice(index, 1)
  } else {
    selectedTags.value.push(tag)
  }
}

const formatDate = (date: string | undefined): string => {
  if (!date) return ''
  return new Date(date).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

const showNotification = (message: string, type: string = 'info'): void => {
  notification.value = { message, type }
  setTimeout(() => {
    notification.value = null
  }, 3000)
}

// Lifecycle
onMounted(() => {
  loadPrompts()
})
</script>

<style scoped>
.prompt-library-container {
  padding: var(--space-8);
  max-width: 1400px;
  margin: 0 auto;
  background: linear-gradient(135deg, var(--color-content-container-bg-start) 0%, var(--color-content-container-bg-end) 100%);
  min-height: 100vh;
}

/* Header */
.library-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-8);
  background: var(--color-card-bg);
  padding: var(--space-6);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
  border: 1px solid var(--color-card-border);
}

.library-header h2 {
  margin: 0;
  font-size: 1.8rem;
  color: var(--color-card-heading);
}

.header-actions {
  display: flex;
  gap: var(--space-4);
}

/* Controls */
.library-controls {
  margin-bottom: var(--space-8);
  background: var(--color-card-bg);
  padding: var(--space-6);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
  border: 1px solid var(--color-card-border);
}

.search-input {
  width: 100%;
  padding: var(--space-3) var(--space-4);
  border: 2px solid var(--color-input-border);
  border-radius: var(--radius-lg);
  font-size: var(--text-base);
  margin-bottom: var(--space-4);
  transition: all var(--transition-slow) ease;
  background: var(--color-input-bg);
  color: var(--color-input-text);
}

.search-input:focus {
  outline: none;
  border-color: var(--color-success);
  box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.1);
}

.filter-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.filter-tag {
  padding: var(--space-2) var(--space-4);
  background: var(--color-filter-tag-bg);
  border: 2px solid var(--color-filter-tag-border);
  border-radius: var(--radius-pill);
  cursor: pointer;
  transition: all var(--transition-slow) ease;
  font-size: 0.9rem;
  color: var(--color-filter-tag-text);
}

.filter-tag:hover {
  border-color: var(--color-success);
  background: var(--color-tag-bg);
  color: var(--color-tag-text);
}

.filter-tag.active {
  background: var(--color-filter-tag-active-bg);
  color: var(--color-filter-tag-active-text);
  border-color: var(--color-success);
}

/* Grid View */
.prompts-container.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: var(--space-6);
}

/* List View */
.prompts-container.list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

/* Prompt Cards */
.prompt-card {
  background: var(--color-card-bg);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
  overflow: hidden;
  transition: all var(--transition-slow) ease;
  display: flex;
  flex-direction: column;
}

.prompt-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-xl);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-card-divider);
}

.card-header h4 {
  margin: 0;
  font-size: 1.1rem;
  color: var(--color-card-heading);
  flex: 1;
}

.card-actions {
  display: flex;
  gap: var(--space-2);
}

.action-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
  padding: var(--space-1);
  transition: all var(--transition-slow) ease;
  opacity: 0.7;
}

.action-btn:hover {
  opacity: 1;
  transform: scale(1.2);
}

.action-btn.shared {
  opacity: 1;
  color: var(--color-success);
}

.action-btn.delete:hover {
  color: var(--color-danger);
}

.card-body {
  padding: var(--space-4);
  flex: 1;
}

.prompt-preview {
  margin: 0 0 var(--space-3) 0;
  color: var(--color-card-text-secondary);
  line-height: 1.5;
  font-size: 0.95rem;
}

.card-meta {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  flex-wrap: wrap;
}

.badge {
  display: inline-block;
  padding: var(--space-1) var(--space-3);
  background: var(--color-badge-bg);
  border-radius: var(--radius-xl);
  font-size: 0.85rem;
  color: var(--color-badge-text);
}

.badge.category {
  background: var(--color-badge-category-bg);
  color: var(--color-badge-category-text);
}

.badge.date {
  background: var(--color-badge-date-bg);
  color: var(--color-badge-date-text);
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.tag {
  font-size: 0.85rem;
  color: var(--color-tag-text);
  background: var(--color-tag-bg);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-tag-border);
}

.card-footer {
  padding: var(--space-4);
  border-top: 1px solid var(--color-card-divider);
  background: var(--color-card-footer-bg);
}

/* Prompt Items (List View) */
.prompt-item {
  background: var(--color-card-bg);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-slow) ease;
}

.prompt-item:hover {
  box-shadow: var(--shadow-lg);
}

.item-header {
  flex: 1;
}

.item-header h4 {
  margin: 0 0 var(--space-2) 0;
  color: var(--color-card-heading);
}

.item-preview {
  margin: 0;
  color: var(--color-card-text-muted);
  font-size: 0.9rem;
}

.item-meta {
  display: flex;
  gap: var(--space-2);
  margin: var(--space-2) 0;
}

.item-actions {
  display: flex;
  gap: var(--space-3);
  margin-left: var(--space-6);
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 4rem var(--space-8);
  background: var(--color-card-bg);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-md);
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: var(--space-4);
}

.empty-state h3 {
  margin: 0 0 var(--space-2) 0;
  color: var(--color-card-heading);
}

.empty-state p {
  margin: 0;
  color: var(--color-card-text-muted);
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
  background: var(--color-btn-secondary-bg);
  color: var(--color-btn-secondary-text);
  border: 1px solid var(--color-btn-secondary-border);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--color-btn-secondary-hover-bg);
}

.btn-danger {
  background: var(--color-danger);
  color: var(--color-surface-primary);
}

.btn-danger:hover:not(:disabled) {
  background: var(--color-danger-hover);
}

.btn-sm {
  padding: var(--space-2) var(--space-4);
  font-size: 0.9rem;
}

.btn .icon {
  font-size: 1.2rem;
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
  background: var(--color-card-bg);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-xl);
  padding: var(--space-8);
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: var(--shadow-2xl);
  z-index: var(--z-modal);
}

.prompt-form h3,
.share-modal h3 {
  margin-top: 0;
  color: var(--color-card-heading);
}

/* Form */
.form-group {
  margin-bottom: var(--space-6);
}

.form-group label {
  display: block;
  margin-bottom: var(--space-2);
  font-weight: 500;
  color: var(--color-card-text);
}

.form-input,
.form-textarea,
.form-select {
  width: 100%;
  padding: var(--space-3);
  border: 2px solid var(--color-input-border);
  border-radius: var(--radius-lg);
  font-size: var(--text-base);
  font-family: inherit;
  transition: all var(--transition-slow) ease;
  background: var(--color-input-bg);
  color: var(--color-input-text);
}

.form-input:focus,
.form-textarea:focus,
.form-select:focus {
  outline: none;
  border-color: var(--color-success);
  box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.1);
}

.form-textarea {
  resize: vertical;
  min-height: 150px;
}

.char-count {
  font-size: 0.85rem;
  color: var(--color-card-text-muted);
  margin-top: var(--space-2);
}

.error-text {
  color: var(--color-danger);
  font-size: 0.85rem;
  margin-top: var(--space-2);
  display: block;
}

.help-text {
  margin: var(--space-2) 0 0 0;
  font-size: 0.85rem;
  color: var(--color-card-text-muted);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
}

.form-actions {
  display: flex;
  gap: var(--space-4);
  justify-content: flex-end;
  margin-top: var(--space-8);
  padding-top: var(--space-6);
  border-top: 1px solid var(--color-card-divider);
}

/* Share Modal */
.share-info {
  font-weight: 600;
  color: var(--color-success);
  margin: var(--space-2) 0 var(--space-6) 0;
}

.share-options {
  margin-bottom: var(--space-6);
}

.share-option {
  margin-bottom: var(--space-4);
}

.share-option label {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  cursor: pointer;
  font-weight: normal;
  margin-bottom: 0;
}

.share-option input[type="radio"] {
  cursor: pointer;
}

.share-link-box {
  display: flex;
  gap: var(--space-3);
  margin-bottom: var(--space-6);
}

.share-link-input {
  flex: 1;
  padding: var(--space-3);
  border: 2px solid var(--color-input-border);
  border-radius: var(--radius-lg);
  font-size: 0.9rem;
  background: var(--color-input-bg);
  color: var(--color-input-text);
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

/* Responsive */
@media (max-width: 768px) {
  .prompt-library-container {
    padding: var(--space-4);
  }

  .library-header {
    flex-direction: column;
    gap: var(--space-4);
    text-align: center;
  }

  .library-header h2 {
    font-size: var(--text-2xl);
  }

  .header-actions {
    width: 100%;
    justify-content: center;
  }

  .prompts-container.grid {
    grid-template-columns: 1fr;
  }

  .item-actions {
    margin-left: 0;
    flex-wrap: wrap;
  }

  .modal-content {
    padding: var(--space-6);
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .share-link-box {
    flex-direction: column;
  }

  @media (max-width: 480px) {
    .filter-tags {
      justify-content: center;
    }

    .action-btn {
      font-size: var(--text-base);
    }

    .btn {
      padding: var(--space-2) var(--space-4);
      font-size: 0.9rem;
    }

    .toast {
      left: var(--space-4);
      right: var(--space-4);
      bottom: var(--space-4);
    }
  }
}
</style>
