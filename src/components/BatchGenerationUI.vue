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
      <div class="batch-left-panel">
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
                ✕
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Panel: Settings & Controls -->
      <div class="batch-right-panel">
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

              <div class="setting-group">
                <label>
                  <input type="checkbox" v-model="generatePDF" />
                  Include PDF versions
                </label>
              </div>

              <div class="setting-group">
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
            <p class="success-message">✓ Batch completed successfully!</p>
          </div>

          <div v-else-if="batchStatus === 'failed'" class="status-failed">
            <p class="error-message">✕ {{ errorMessage }}</p>
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
            v-if="batchStatus === 'completed'"
            @click="downloadBatch"
            class="btn-success"
          >
            ⬇ Download ZIP ({{ totalFileSize }})
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
          • {{ msg }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'

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

  eventSource.value.addEventListener('progress', (event: Event) => {
    const customEvent = event as MessageEvent
    const data = JSON.parse(customEvent.data)

    processedItems.value = data.processed
    progress.value = (data.processed / batchItems.value.length) * 100
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

  eventSource.value.addEventListener('error', (event: Event) => {
    const customEvent = event as MessageEvent
    const data = JSON.parse(customEvent.data)
    batchStatus.value = 'failed'
    errorMessage.value = data.error || 'Batch processing failed'
    eventSource.value?.close()
  })
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

<style scoped lang="css">
.batch-generation-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 2rem;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  min-height: 100vh;
}

.batch-header {
  margin-bottom: 2rem;
  text-align: center;
}

.batch-header h2 {
  font-size: 2rem;
  color: #2c3e50;
  margin-bottom: 0.5rem;
}

.subtitle {
  color: #7f8c8d;
  font-size: 1rem;
}

.batch-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  margin-bottom: 2rem;
}

@media (max-width: 1024px) {
  .batch-content {
    grid-template-columns: 1fr;
  }
}

/* Left Panel */
.batch-left-panel {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.upload-section h3,
.batch-queue-section h3,
.settings-section h3,
.progress-section h3 {
  font-size: 1.25rem;
  color: #2c3e50;
  margin-bottom: 1rem;
}

.upload-drop-zone {
  border: 2px dashed #bdc3c7;
  border-radius: 8px;
  padding: 3rem 2rem;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #f8f9fa;
}

.upload-drop-zone:hover,
.upload-drop-zone.drag-active {
  border-color: #3498db;
  background: #e3f2fd;
}

.upload-icon {
  width: 3rem;
  height: 3rem;
  margin-bottom: 1rem;
  fill: #3498db;
}

.file-label {
  color: #3498db;
  text-decoration: underline;
  cursor: pointer;
}

.batch-queue-section {
  margin-top: 2rem;
}

.queue-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.empty-queue {
  padding: 2rem;
  text-align: center;
  color: #95a5a6;
  background: #ecf0f1;
  border-radius: 8px;
}

.batch-items-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-height: 400px;
  overflow-y: auto;
}

.batch-item {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
  align-items: flex-start;
}

.item-thumbnail {
  flex-shrink: 0;
}

.item-thumbnail img {
  width: 60px;
  height: 60px;
  object-fit: cover;
  border-radius: 4px;
}

.item-details {
  flex: 1;
  min-width: 0;
}

.item-name {
  font-size: 0.9rem;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 0.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.prompt-input {
  width: 100%;
  padding: 0.5rem;
  font-size: 0.85rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-family: monospace;
}

.btn-remove {
  background: #e74c3c;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0.5rem 0.75rem;
  cursor: pointer;
  font-weight: bold;
  transition: background 0.2s;
}

.btn-remove:hover {
  background: #c0392b;
}

/* Right Panel */
.batch-right-panel {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.settings-section {
  margin-bottom: 2rem;
}

.setting-group {
  margin-bottom: 1.5rem;
}

.setting-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #2c3e50;
}

.form-select,
.form-textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #bdc3c7;
  border-radius: 4px;
  font-size: 0.95rem;
  font-family: inherit;
}

.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: #3498db;
  box-shadow: 0 0 0 3px rgba(52, 152, 219, 0.1);
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.advanced-options {
  margin: 1.5rem 0;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 4px;
  cursor: pointer;
}

.advanced-options summary {
  font-weight: 600;
  color: #3498db;
  user-select: none;
}

.advanced-content {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #ddd;
}

.progress-section {
  margin-bottom: 2rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 8px;
}

.status-idle {
  color: #7f8c8d;
  padding: 1rem;
}

.status-processing {
  padding: 1rem;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #ecf0f1;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #3498db, #2ecc71);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.9rem;
  color: #2c3e50;
  font-weight: 600;
}

.status-completed {
  padding: 1rem;
}

.success-message {
  color: #27ae60;
  font-weight: 600;
  font-size: 1.1rem;
}

.status-failed {
  padding: 1rem;
}

.error-message {
  color: #e74c3c;
  font-weight: 600;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.btn-primary,
.btn-success,
.btn-secondary,
.btn-secondary-small {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: #3498db;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2980b9;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(52, 152, 219, 0.3);
}

.btn-primary:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

.btn-success {
  background: #27ae60;
  color: white;
}

.btn-success:hover {
  background: #229954;
  transform: translateY(-2px);
}

.btn-secondary {
  background: #95a5a6;
  color: white;
}

.btn-secondary:hover {
  background: #7f8c8d;
}

.btn-secondary-small {
  background: #95a5a6;
  color: white;
  padding: 0.5rem 1rem;
  font-size: 0.9rem;
}

.btn-secondary-small:hover {
  background: #7f8c8d;
}

/* Progress Ticker */
.progress-ticker {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.ticker-label {
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 0.75rem;
}

.ticker-messages {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 1rem;
  max-height: 150px;
  overflow-y: auto;
  font-size: 0.9rem;
  font-family: monospace;
}

.ticker-msg {
  color: #34495e;
  margin-bottom: 0.5rem;
  line-height: 1.4;
}

small {
  display: block;
  margin-top: 0.25rem;
  color: #7f8c8d;
  font-size: 0.85rem;
}
</style>
