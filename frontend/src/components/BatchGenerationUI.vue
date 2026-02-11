<template>
  <div class="batch-generation-container">
    <!-- Header -->
    <div class="batch-header">
      <h2>Batch Generation Workflow</h2>
      <p class="subtitle">Generate multiple coloring pages in one batch</p>
    </div>

    <!-- Main Content Grid -->
    <div class="batch-content">
      <!-- Left Panel: Image Upload & Queue -->
      <div class="batch-panel">
        <div class="upload-section">
          <h3>1. Upload Images</h3>
          <div
            class="upload-drop-zone"
            @dragover.prevent="dragOver = true"
            @dragleave.prevent="dragOver = false"
            @drop.prevent="handleImageDrop"
            :class="{ 'drag-active': dragOver }"
          >
            <svg class="upload-icon" viewBox="0 0 24 24">
              <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" />
            </svg>
            <p>Drag images here or <label class="file-label">
              click to browse
              <input
                type="file"
                multiple
                accept="image/*"
                @change="handleImageSelect"
                style="display: none"
              />
            </label></p>
            <small>JPG, PNG, WebP (Max 10MB each)</small>
          </div>
        </div>

        <!-- Batch Queue -->
        <div class="batch-queue-section">
          <div class="queue-header">
            <h3>Batch Queue ({{ batchItems.length }}/{{ maxBatchSize }})</h3>
            <button
              v-if="batchItems.length > 0"
              @click="clearBatch"
              class="btn-secondary-small"
            >
              Clear All
            </button>
          </div>

          <div v-if="batchItems.length === 0" class="empty-queue">
            <p>No images in batch. Add images to get started.</p>
          </div>

          <div v-else class="batch-items-list">
            <div
              v-for="(item, idx) in batchItems"
              :key="item.id"
              class="batch-item"
            >
              <div class="item-thumbnail">
                <img :src="item.preview" :alt="`Image ${idx + 1}`" />
              </div>
              <div class="item-details">
                <p class="item-name">{{ item.file }}</p>
                <input
                  v-model="item.prompt"
                  type="text"
                  class="prompt-input"
                  placeholder="Enter custom prompt..."
                />
              </div>
              <button
                @click="removeFromBatch(item.id)"
                class="btn-remove"
                title="Remove from batch"
              >
                &times;
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Panel: Settings & Controls -->
      <div class="batch-panel">
        <div class="settings-section">
          <h3>2. Configure Batch</h3>

          <!-- Model Selection -->
          <div class="setting-group">
            <label for="model-select">AI Model</label>
            <select
              id="model-select"
              v-model="selectedModel"
              class="form-select"
              :disabled="batchStatus === 'processing'"
            >
              <option value="claude">Claude 3.5 Sonnet</option>
              <option value="gemini">Google Gemini 2.0</option>
              <option value="gpt4">GPT-4 Vision</option>
            </select>
            <small>Select model for all images in batch</small>
          </div>

          <!-- Prompt Template -->
          <div class="setting-group">
            <label for="default-prompt">Default Prompt</label>
            <textarea
              id="default-prompt"
              v-model="defaultPrompt"
              class="form-textarea"
              rows="3"
              placeholder="Enter default prompt template..."
            ></textarea>
            <small>Use {filename} placeholder for image name</small>
          </div>

          <!-- Advanced Options -->
          <details class="advanced-options">
            <summary>Advanced Options</summary>
            <div class="advanced-content">
              <div class="setting-group">
                <label for="quality">Output Quality</label>
                <select id="quality" v-model="outputQuality" class="form-select">
                  <option value="standard">Standard (1024x1024)</option>
                  <option value="high">High (2048x2048)</option>
                  <option value="print">Print Ready (4096x4096, 300 DPI)</option>
                </select>
              </div>

              <div class="setting-group checkbox-group">
                <label>
                  <input type="checkbox" v-model="generatePDF" />
                  Include PDF versions
                </label>
              </div>

              <div class="setting-group checkbox-group">
                <label>
                  <input type="checkbox" v-model="autoDownload" />
                  Auto-download when complete
                </label>
              </div>
            </div>
          </details>
        </div>

        <!-- Progress Section -->
        <div class="progress-section">
          <h3>3. Progress</h3>
          <div v-if="batchStatus === 'idle'" class="status-idle">
            <p>Ready to process {{ batchItems.length }} image(s)</p>
          </div>

          <div v-else-if="batchStatus === 'processing'" class="status-processing">
            <div class="progress-bar">
              <div
                class="progress-fill"
                :style="{ width: progress + '%' }"
              ></div>
            </div>
            <p class="progress-text">
              {{ processedItems }}/{{ batchItems.length }} images processed
              ({{ Math.round(progress) }}%)
            </p>
          </div>

          <div v-else-if="batchStatus === 'completed'" class="status-completed">
            <p class="success-message">Batch completed successfully!</p>
          </div>

          <div v-else-if="batchStatus === 'failed'" class="status-failed">
            <p class="error-message">{{ errorMessage }}</p>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="action-buttons">
          <button
            @click="submitBatch"
            :disabled="!canSubmit"
            class="btn-primary"
          >
            {{ batchStatus === 'processing' ? 'Processing...' : 'Start Batch' }}
          </button>

          <button
            v-if="batchStatus === 'processing'"
            @click="cancelBatch"
            class="btn-danger"
          >
            Cancel
          </button>

          <button
            v-if="batchStatus === 'completed'"
            @click="downloadBatch"
            class="btn-success"
          >
            Download ZIP ({{ totalFileSize }})
          </button>

          <button
            v-if="batchStatus === 'completed'"
            @click="newBatch"
            class="btn-secondary"
          >
            New Batch
          </button>
        </div>
      </div>
    </div>

    <!-- Real-time Progress Ticker (for SSE updates) -->
    <div v-if="batchStatus === 'processing'" class="progress-ticker">
      <p class="ticker-label">Live Updates:</p>
      <div class="ticker-messages">
        <p v-for="(msg, idx) in recentMessages" :key="idx" class="ticker-msg">
          {{ msg }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'

interface BatchItem {
  id: string
  file: string
  preview: string
  prompt: string
  model: string
}

interface BatchResponse {
  batch_id: string
  status: string
  total_items: number
}

// Constants
const maxBatchSize = 50
const maxFileSize = 10 * 1024 * 1024 // 10MB

// Reactive State
const batchItems = ref<BatchItem[]>([])
const selectedModel = ref<string>('claude')
const defaultPrompt = ref<string>('Create a beautiful coloring book page with {filename}')
const batchStatus = ref<'idle' | 'processing' | 'completed' | 'failed'>('idle')
const progress = ref<number>(0)
const processedItems = ref<number>(0)
const errorMessage = ref<string>('')
const dragOver = ref<boolean>(false)
const outputQuality = ref<string>('standard')
const generatePDF = ref<boolean>(false)
const autoDownload = ref<boolean>(false)
const recentMessages = ref<string[]>([])
const totalFileSize = ref<string>('0 MB')
const currentBatchId = ref<string>('')
const eventSource = ref<EventSource | null>(null)

// Computed Properties
const canSubmit = computed(() => {
  return (
    batchItems.value.length > 0 &&
    batchItems.value.length <= maxBatchSize &&
    batchItems.value.every((item) => item.prompt.trim().length > 0) &&
    selectedModel.value &&
    batchStatus.value !== 'processing'
  )
})

// Methods
const handleImageDrop = (event: DragEvent) => {
  dragOver.value = false
  const files = event.dataTransfer?.files
  if (files) {
    processFiles(files)
  }
}

const handleImageSelect = (event: Event) => {
  const input = event.target as HTMLInputElement
  if (input.files) {
    processFiles(input.files)
  }
}

const processFiles = (files: FileList) => {
  const remainingSlots = maxBatchSize - batchItems.value.length

  for (let i = 0; i < Math.min(files.length, remainingSlots); i++) {
    const file = files[i]

    // Validate file
    if (!file.type.startsWith('image/')) {
      console.warn(`Skipping non-image file: ${file.name}`)
      continue
    }

    if (file.size > maxFileSize) {
      console.warn(`Skipping oversized file: ${file.name}`)
      continue
    }

    // Create batch item
    const reader = new FileReader()
    reader.onload = (e) => {
      const batchItem: BatchItem = {
        id: `img_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        file: file.name,
        preview: (e.target?.result as string) || '',
        prompt: defaultPrompt.value,
        model: selectedModel.value,
      }

      if (batchItems.value.length < maxBatchSize) {
        batchItems.value.push(batchItem)
      }
    }
    reader.readAsDataURL(file)
  }
}

const removeFromBatch = (itemId: string) => {
  batchItems.value = batchItems.value.filter((item) => item.id !== itemId)
}

const clearBatch = () => {
  if (confirm('Clear all images from batch?')) {
    batchItems.value = []
    progress.value = 0
    processedItems.value = 0
    errorMessage.value = ''
  }
}

const submitBatch = async () => {
  if (!canSubmit.value) return

  batchStatus.value = 'processing'
  progress.value = 0
  processedItems.value = 0
  errorMessage.value = ''
  recentMessages.value = []

  try {
    // Prepare payload
    const payload = {
      items: batchItems.value.map((item) => ({
        file: item.file,
        prompt: item.prompt,
      })),
      model: selectedModel.value,
      options: {
        quality: outputQuality.value,
        include_pdf: generatePDF.value,
      },
    }

    // Submit batch
    const response = await fetch('/api/v1/batch/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    if (!response.ok) {
      throw new Error(`API error: ${response.statusText}`)
    }

    const data: BatchResponse = await response.json()
    currentBatchId.value = data.batch_id

    // Connect to SSE for real-time updates
    connectProgressStream(data.batch_id)
  } catch (error) {
    batchStatus.value = 'failed'
    errorMessage.value = error instanceof Error ? error.message : 'Unknown error'
    recentMessages.value.push(`Error: ${errorMessage.value}`)
  }
}

const connectProgressStream = (batchId: string) => {
  eventSource.value = new EventSource(`/api/v1/batch/${batchId}/progress`)

  eventSource.value.addEventListener('processing', (event: Event) => {
    const customEvent = event as MessageEvent
    const data = JSON.parse(customEvent.data)

    processedItems.value = data.processed
    progress.value = data.total > 0
      ? (data.processed / data.total) * 100
      : 0
    totalFileSize.value = formatFileSize(data.total_size || 0)

    if (data.message) {
      recentMessages.value.unshift(data.message)
      if (recentMessages.value.length > 5) {
        recentMessages.value.pop()
      }
    }
  })

  eventSource.value.addEventListener('completed', (event: Event) => {
    const customEvent = event as MessageEvent
    const data = JSON.parse(customEvent.data)

    batchStatus.value = 'completed'
    progress.value = 100
    processedItems.value = batchItems.value.length
    totalFileSize.value = formatFileSize(data.total_size)

    if (autoDownload.value) {
      downloadBatch()
    }

    eventSource.value?.close()
  })

  eventSource.value.addEventListener('failed', (event: Event) => {
    const customEvent = event as MessageEvent
    const data = JSON.parse(customEvent.data)
    batchStatus.value = 'failed'
    errorMessage.value = data.error || 'Batch processing failed'
    eventSource.value?.close()
  })

  eventSource.value.onerror = () => {
    if (batchStatus.value === 'processing') {
      recentMessages.value.unshift('Connection lost, retrying...')
    }
  }
}

const cancelBatch = async () => {
  if (!currentBatchId.value) return
  try {
    await fetch(`/api/v1/batch/${currentBatchId.value}/cancel`, { method: 'POST' })
    eventSource.value?.close()
    batchStatus.value = 'failed'
    errorMessage.value = 'Batch cancelled by user'
  } catch {
    // Ignore cancel errors
  }
}

const downloadBatch = async () => {
  try {
    const response = await fetch(`/api/v1/batch/${currentBatchId.value}/download`)
    if (!response.ok) throw new Error('Download failed')

    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `batch_${currentBatchId.value}.zip`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Download failed'
  }
}

const newBatch = () => {
  batchItems.value = []
  batchStatus.value = 'idle'
  progress.value = 0
  processedItems.value = 0
  errorMessage.value = ''
  currentBatchId.value = ''
  recentMessages.value = []
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

onUnmounted(() => {
  eventSource.value?.close()
})
</script>

<style scoped>
.batch-generation-container {
  max-width: 1400px;
  margin: 0 auto;
}

.batch-header {
  margin-bottom: var(--space-8);
  text-align: center;
}

.batch-header h2 {
  font-size: var(--text-3xl);
  color: var(--color-heading-on-shell);
  margin-bottom: var(--space-2);
}

.subtitle {
  color: var(--color-shell-text-subtle);
  font-size: var(--text-base);
}

.batch-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-8);
  margin-bottom: var(--space-8);
}

@media (max-width: 1024px) {
  .batch-content {
    grid-template-columns: 1fr;
  }
}

/* Panels */
.batch-panel {
  background: var(--color-card-bg);
  border-radius: var(--radius-xl);
  padding: var(--space-8);
  border: 1px solid var(--color-card-border);
  box-shadow: var(--shadow-md);
}

.batch-panel h3 {
  font-size: var(--text-lg);
  color: var(--color-card-heading);
  margin-bottom: var(--space-4);
}

/* Upload Zone */
.upload-drop-zone {
  border: 2px dashed var(--color-input-border);
  border-radius: var(--radius-lg);
  padding: var(--space-12) var(--space-8);
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-slow) ease;
  background: var(--color-card-bg-secondary);
  color: var(--color-card-text-secondary);
}

.upload-drop-zone:hover,
.upload-drop-zone.drag-active {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
}

.upload-icon {
  width: var(--space-12);
  height: var(--space-12);
  margin-bottom: var(--space-4);
  fill: var(--color-primary);
}

.file-label {
  color: var(--color-primary);
  text-decoration: underline;
  cursor: pointer;
}

/* Batch Queue */
.batch-queue-section {
  margin-top: var(--space-8);
}

.queue-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
}

.empty-queue {
  padding: var(--space-8);
  text-align: center;
  color: var(--color-card-text-muted);
  background: var(--color-card-bg-secondary);
  border-radius: var(--radius-lg);
}

.batch-items-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  max-height: 400px;
  overflow-y: auto;
}

.batch-item {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--color-card-bg-secondary);
  border-radius: var(--radius-lg);
  align-items: flex-start;
  border: 1px solid var(--color-card-border);
}

.item-thumbnail {
  flex-shrink: 0;
}

.item-thumbnail img {
  width: 60px;
  height: 60px;
  object-fit: cover;
  border-radius: var(--radius-md);
}

.item-details {
  flex: 1;
  min-width: 0;
}

.item-name {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-card-text);
  margin-bottom: var(--space-2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.prompt-input {
  width: 100%;
  padding: var(--space-2);
  font-size: var(--text-sm);
  border: 1px solid var(--color-input-border);
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  background: var(--color-input-bg);
  color: var(--color-input-text);
}

.prompt-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: var(--focus-ring);
}

.btn-remove {
  background: var(--color-danger);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  cursor: pointer;
  font-weight: bold;
  font-size: var(--text-lg);
  line-height: 1;
  transition: background var(--transition-fast);
}

.btn-remove:hover {
  background: var(--color-danger-hover);
}

/* Settings */
.settings-section {
  margin-bottom: var(--space-8);
}

.setting-group {
  margin-bottom: var(--space-6);
}

.setting-group label {
  display: block;
  margin-bottom: var(--space-2);
  font-weight: 600;
  color: var(--color-card-text);
  font-size: var(--text-sm);
}

.checkbox-group label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-weight: 500;
  cursor: pointer;
}

.form-select,
.form-textarea {
  width: 100%;
  padding: var(--space-3);
  border: 1px solid var(--color-input-border);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-family: inherit;
  background: var(--color-input-bg);
  color: var(--color-input-text);
}

.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: var(--focus-ring);
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.advanced-options {
  margin: var(--space-6) 0;
  padding: var(--space-4);
  background: var(--color-card-bg-secondary);
  border-radius: var(--radius-md);
  border: 1px solid var(--color-card-border);
  cursor: pointer;
}

.advanced-options summary {
  font-weight: 600;
  color: var(--color-primary);
  user-select: none;
  font-size: var(--text-sm);
}

.advanced-content {
  margin-top: var(--space-4);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-card-divider);
}

/* Progress */
.progress-section {
  margin-bottom: var(--space-8);
  padding: var(--space-4);
  background: var(--color-card-bg-secondary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-card-border);
}

.status-idle {
  color: var(--color-card-text-muted);
  padding: var(--space-4);
}

.status-processing {
  padding: var(--space-4);
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: var(--color-card-bg);
  border-radius: var(--radius-full);
  overflow: hidden;
  margin-bottom: var(--space-2);
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-brand-start), var(--color-success));
  transition: width var(--transition-slow) ease;
}

.progress-text {
  font-size: var(--text-sm);
  color: var(--color-card-text);
  font-weight: 600;
}

.status-completed {
  padding: var(--space-4);
}

.success-message {
  color: var(--color-success);
  font-weight: 600;
  font-size: var(--text-lg);
}

.status-failed {
  padding: var(--space-4);
}

.error-message {
  color: var(--color-danger);
  font-weight: 600;
}

/* Buttons */
.action-buttons {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.btn-primary,
.btn-success,
.btn-secondary,
.btn-danger,
.btn-secondary-small {
  padding: var(--space-3) var(--space-6);
  border: none;
  border-radius: var(--radius-lg);
  font-size: var(--text-base);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-slow) ease;
  font-family: inherit;
}

.btn-primary {
  background: linear-gradient(135deg, var(--color-brand-start) 0%, var(--color-brand-end) 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: var(--shadow-brand);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.btn-success {
  background: var(--color-success);
  color: white;
}

.btn-success:hover {
  background: var(--color-success-hover);
  transform: translateY(-2px);
}

.btn-secondary {
  background: var(--color-btn-secondary-bg);
  color: var(--color-btn-secondary-text);
  border: 1px solid var(--color-btn-secondary-border);
}

.btn-secondary:hover {
  background: var(--color-btn-secondary-hover-bg);
}

.btn-danger {
  background: var(--color-danger);
  color: white;
}

.btn-danger:hover {
  background: var(--color-danger-hover);
}

.btn-secondary-small {
  background: var(--color-btn-secondary-bg);
  color: var(--color-btn-secondary-text);
  border: 1px solid var(--color-btn-secondary-border);
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
}

.btn-secondary-small:hover {
  background: var(--color-btn-secondary-hover-bg);
}

/* Progress Ticker */
.progress-ticker {
  background: var(--color-card-bg);
  border-radius: var(--radius-xl);
  padding: var(--space-6);
  border: 1px solid var(--color-card-border);
  box-shadow: var(--shadow-md);
}

.ticker-label {
  font-weight: 600;
  color: var(--color-card-heading);
  margin-bottom: var(--space-3);
}

.ticker-messages {
  background: var(--color-card-bg-secondary);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  max-height: 150px;
  overflow-y: auto;
  font-size: var(--text-sm);
  font-family: var(--font-mono);
}

.ticker-msg {
  color: var(--color-card-text-secondary);
  margin-bottom: var(--space-2);
  line-height: 1.4;
}

small {
  display: block;
  margin-top: var(--space-1);
  color: var(--color-card-text-muted);
  font-size: var(--text-sm);
}
</style>
