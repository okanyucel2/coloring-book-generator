<template>
  <div class="workbook-builder">
    <!-- Toast Notification -->
    <Transition name="toast-fade">
      <div v-if="toastMessage" :class="['toast', `toast-${toastType}`]">
        <span class="toast-icon">{{ toastType === 'success' ? '&#10003;' : toastType === 'error' ? '&#10007;' : '&#9432;' }}</span>
        <span class="toast-text">{{ toastMessage }}</span>
        <button class="toast-close" @click="toastMessage = ''">&times;</button>
      </div>
    </Transition>

    <!-- Step Indicator -->
    <div class="steps-indicator">
      <button
        v-for="(s, idx) in steps"
        :key="s.id"
        :class="['step', { active: currentStep === idx, completed: idx < currentStep }]"
        @click="goToStep(idx)"
        :disabled="idx > maxReachedStep"
      >
        <span class="step-number">{{ idx + 1 }}</span>
        <span class="step-label">{{ s.label }}</span>
      </button>
    </div>

    <!-- Step 1: Theme Selection -->
    <div v-show="currentStep === 0" class="step-content">
      <h2>Choose a Theme</h2>
      <p class="step-description">Select the theme for your activity workbook</p>

      <!-- Loading State -->
      <div v-if="themesLoading" class="loading-container">
        <div class="spinner"></div>
        <p class="loading-text">Loading themes...</p>
      </div>

      <!-- Error State -->
      <div v-else-if="themesError" class="error-container">
        <div class="error-icon">!</div>
        <p class="error-title">Failed to load themes</p>
        <p class="error-detail">{{ themesError }}</p>
        <button class="retry-btn" @click="loadThemes">Try Again</button>
      </div>

      <!-- Themes Grid -->
      <div v-else class="themes-grid">
        <ThemeCard
          v-for="theme in themes"
          :key="theme.slug"
          :theme="theme"
          :is-selected="selectedTheme === theme.slug"
          @select="selectTheme"
        />
      </div>
    </div>

    <!-- Step 2: Configuration -->
    <div v-show="currentStep === 1" class="step-content">
      <h2>Configure Your Workbook</h2>
      <p class="step-description">Set the title, age range, and select items</p>
      <div class="config-form">
        <div class="form-group">
          <label>Title</label>
          <input v-model="config.title" type="text" placeholder="e.g. Vehicles Tracing Workbook" />
        </div>
        <div class="form-group">
          <label>Subtitle</label>
          <input v-model="config.subtitle" type="text" placeholder="e.g. For Boys Ages 3-5" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>Age Min</label>
            <input v-model.number="config.age_min" type="number" min="0" max="18" />
          </div>
          <div class="form-group">
            <label>Age Max</label>
            <input v-model.number="config.age_max" type="number" min="0" max="18" />
          </div>
          <div class="form-group">
            <label>Page Count</label>
            <input v-model.number="config.page_count" type="number" min="5" max="100" />
          </div>
          <div class="form-group">
            <label>Page Size</label>
            <select v-model="config.page_size">
              <option value="letter">US Letter</option>
              <option value="a4">A4</option>
            </select>
          </div>
        </div>
        <div class="form-group">
          <label>Items ({{ selectedItems.length }} selected)</label>
          <div class="items-grid">
            <button
              v-for="item in availableItems"
              :key="item"
              :class="['item-chip', { selected: selectedItems.includes(item) }]"
              @click="toggleItem(item)"
            >
              {{ formatItemName(item) }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Step 3: Activity Mix -->
    <div v-show="currentStep === 2" class="step-content">
      <h2>Activity Mix</h2>
      <p class="step-description">Choose how many pages of each activity type</p>
      <ActivityMixer v-model="config.activity_mix" />
    </div>

    <!-- Step 4: Preview & Generate -->
    <div v-show="currentStep === 3" class="step-content">
      <h2>Preview & Generate</h2>
      <p class="step-description">Review your workbook and generate the PDF</p>

      <div class="preview-generate-layout">
        <div class="preview-section">
          <WorkbookPreview :workbook-id="createdWorkbookId" />
        </div>
        <div class="generate-section">
          <div class="summary-card">
            <h3>Summary</h3>
            <div class="summary-row"><span>Theme</span><strong>{{ selectedThemeDisplay }}</strong></div>
            <div class="summary-row"><span>Title</span><strong>{{ config.title }}</strong></div>
            <div class="summary-row"><span>Age Range</span><strong>{{ config.age_min }}-{{ config.age_max }}</strong></div>
            <div class="summary-row"><span>Items</span><strong>{{ selectedItems.length }}</strong></div>
            <div class="summary-row"><span>Activity Pages</span><strong>{{ totalActivityPages }}</strong></div>
            <div class="summary-row"><span>Page Size</span><strong>{{ config.page_size.toUpperCase() }}</strong></div>
          </div>

          <div v-if="generationStatus === 'generating'" class="generation-progress">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: `${generationProgress * 100}%` }"></div>
            </div>
            <p class="progress-text">Generating PDF... {{ Math.round(generationProgress * 100) }}%</p>
          </div>

          <!-- Generation Error State -->
          <div v-if="generationStatus === 'failed'" class="generation-error">
            <div class="error-icon-small">!</div>
            <p class="error-text">{{ generationError || 'PDF generation failed. Please try again.' }}</p>
            <button class="retry-btn-small" @click="generateWorkbook">Retry</button>
          </div>

          <div v-if="generationStatus === 'ready'" class="generation-ready">
            <p>PDF generated successfully!</p>
            <a :href="downloadUrl" class="download-btn" download @click="onDownloadClick">Download PDF</a>
          </div>

          <button
            v-if="generationStatus !== 'generating'"
            class="generate-btn"
            @click="generateWorkbook"
            :disabled="!canGenerate || generationStatus === 'generating'"
          >
            <span v-if="generationStatus === 'generating'" class="btn-spinner"></span>
            {{ generationStatus === 'ready' ? 'Regenerate' : generationStatus === 'generating' ? 'Generating...' : 'Generate PDF' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Navigation -->
    <div class="step-navigation">
      <button
        v-if="currentStep > 0"
        class="nav-btn secondary"
        @click="currentStep--"
      >Back</button>
      <div class="nav-spacer"></div>
      <button
        v-if="currentStep < steps.length - 1"
        class="nav-btn primary"
        @click="nextStep"
        :disabled="!canProceed"
      >Next</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { apiService } from '@/services/api'
import ThemeCard from './ThemeCard.vue'
import ActivityMixer from './ActivityMixer.vue'
import WorkbookPreview from './WorkbookPreview.vue'

interface Theme {
  slug: string
  display_name: string
  category: string
  items: string[]
  item_count: number
  age_groups: string[]
  etsy_tags: string[]
}

const steps = [
  { id: 'theme', label: 'Theme' },
  { id: 'config', label: 'Configure' },
  { id: 'mix', label: 'Activities' },
  { id: 'generate', label: 'Generate' },
]

const currentStep = ref(0)
const maxReachedStep = ref(0)
const themes = ref<Theme[]>([])
const themesLoading = ref(false)
const themesError = ref('')
const selectedTheme = ref('')
const selectedItems = ref<string[]>([])
const createdWorkbookId = ref<string | null>(null)
const generationStatus = ref<string>('draft')
const generationProgress = ref(0)
const generationError = ref('')
const downloadUrl = ref('')

// Toast notification state
const toastMessage = ref('')
const toastType = ref<'success' | 'error' | 'info'>('info')
let toastTimeout: ReturnType<typeof setTimeout> | null = null

const config = ref({
  title: '',
  subtitle: '',
  age_min: 3,
  age_max: 5,
  page_count: 30,
  page_size: 'letter',
  activity_mix: {
    trace_and_color: 18,
    which_different: 2,
    count_circle: 2,
    match: 2,
    word_to_image: 1,
    find_circle: 2,
  } as Record<string, number>,
})

const selectedThemeDisplay = computed(() => {
  const t = themes.value.find(th => th.slug === selectedTheme.value)
  return t?.display_name || selectedTheme.value
})

const availableItems = computed(() => {
  const t = themes.value.find(th => th.slug === selectedTheme.value)
  return t?.items || []
})

const totalActivityPages = computed(() =>
  Object.values(config.value.activity_mix).reduce((sum, v) => sum + (v || 0), 0)
)

const canProceed = computed(() => {
  if (currentStep.value === 0) return !!selectedTheme.value
  if (currentStep.value === 1) return config.value.title.length > 0 && selectedItems.value.length > 0
  if (currentStep.value === 2) return totalActivityPages.value > 0
  return true
})

const canGenerate = computed(() =>
  selectedTheme.value && config.value.title && selectedItems.value.length > 0 && totalActivityPages.value > 0
)

function showToast(message: string, type: 'success' | 'error' | 'info' = 'info', duration = 4000) {
  if (toastTimeout) {
    clearTimeout(toastTimeout)
  }
  toastMessage.value = message
  toastType.value = type
  toastTimeout = setTimeout(() => {
    toastMessage.value = ''
  }, duration)
}

async function loadThemes() {
  themesLoading.value = true
  themesError.value = ''
  try {
    const resp = await apiService.get<{ data: Theme[] }>('/themes')
    themes.value = resp.data
  } catch (e) {
    const errorMsg = e instanceof Error ? e.message : 'Unable to connect to the server'
    themesError.value = errorMsg
    console.error('Failed to load themes:', e)
  } finally {
    themesLoading.value = false
  }
}

onMounted(() => {
  loadThemes()
})

function selectTheme(slug: string) {
  selectedTheme.value = slug
  const theme = themes.value.find(t => t.slug === slug)
  if (theme) {
    selectedItems.value = [...theme.items]
    if (!config.value.title) {
      config.value.title = `${theme.display_name} Activity Workbook`
    }
  }
}

function toggleItem(item: string) {
  const idx = selectedItems.value.indexOf(item)
  if (idx >= 0) {
    selectedItems.value.splice(idx, 1)
  } else {
    selectedItems.value.push(item)
  }
}

function formatItemName(name: string): string {
  return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function goToStep(idx: number) {
  if (idx <= maxReachedStep.value) {
    currentStep.value = idx
  }
}

function nextStep() {
  if (canProceed.value && currentStep.value < steps.length - 1) {
    currentStep.value++
    if (currentStep.value > maxReachedStep.value) {
      maxReachedStep.value = currentStep.value
    }
    // Auto-create workbook when reaching step 4
    if (currentStep.value === 3 && !createdWorkbookId.value) {
      createWorkbook()
    }
  }
}

async function createWorkbook() {
  try {
    const resp = await apiService.post<{ id: string }>('/workbooks', {
      theme: selectedTheme.value,
      title: config.value.title,
      subtitle: config.value.subtitle || undefined,
      age_min: config.value.age_min,
      age_max: config.value.age_max,
      page_count: config.value.page_count,
      items: selectedItems.value,
      activity_mix: config.value.activity_mix,
      page_size: config.value.page_size,
    })
    createdWorkbookId.value = resp.id
  } catch (e) {
    const errorMsg = e instanceof Error ? e.message : 'Failed to create workbook'
    showToast(errorMsg, 'error')
    console.error('Failed to create workbook:', e)
  }
}

async function generateWorkbook() {
  if (!createdWorkbookId.value) {
    await createWorkbook()
  }
  if (!createdWorkbookId.value) return

  generationStatus.value = 'generating'
  generationProgress.value = 0
  generationError.value = ''

  try {
    await apiService.post(`/workbooks/${createdWorkbookId.value}/generate`)

    // Poll for status
    const pollInterval = setInterval(async () => {
      try {
        const status = await apiService.get<{ status: string; progress: number | null }>(
          `/workbooks/${createdWorkbookId.value}/status`
        )
        generationProgress.value = status.progress || 0

        if (status.status === 'ready') {
          generationStatus.value = 'ready'
          const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api/v1'
          downloadUrl.value = `${baseUrl}/workbooks/${createdWorkbookId.value}/download`
          clearInterval(pollInterval)
          showToast('PDF generated successfully! Click Download to save.', 'success', 5000)
        } else if (status.status === 'failed') {
          generationStatus.value = 'failed'
          generationError.value = 'The server encountered an error while generating your PDF.'
          clearInterval(pollInterval)
          showToast('PDF generation failed. Please try again.', 'error')
        }
      } catch {
        clearInterval(pollInterval)
        generationStatus.value = 'failed'
        generationError.value = 'Lost connection to the server during generation.'
        showToast('Connection lost during PDF generation.', 'error')
      }
    }, 500)
  } catch (e) {
    const errorMsg = e instanceof Error ? e.message : 'Generation request failed'
    generationError.value = errorMsg
    generationStatus.value = 'failed'
    showToast(`Generation failed: ${errorMsg}`, 'error')
    console.error('Generation failed:', e)
  }
}

function onDownloadClick() {
  showToast('Download started! Check your downloads folder.', 'success')
}
</script>

<style scoped>
.workbook-builder {
  max-width: 900px;
  margin: 0 auto;
  background: linear-gradient(135deg, var(--color-content-container-bg-start) 0%, var(--color-content-container-bg-end) 100%);
  padding: var(--space-8);
  border-radius: var(--radius-xl);
  min-height: 60vh;
  position: relative;
}

/* Toast Notification */
.toast {
  position: fixed;
  top: 24px;
  right: 24px;
  z-index: 9999;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-5);
  border-radius: var(--radius-lg);
  font-size: var(--text-sm);
  font-weight: 500;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  max-width: 420px;
}

.toast-success {
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #065f46;
}

.toast-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
}

.toast-info {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1e40af;
}

.toast-icon {
  font-size: 1.1rem;
  flex-shrink: 0;
}

.toast-text {
  flex: 1;
}

.toast-close {
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  opacity: 0.6;
  padding: 0 var(--space-1);
  color: inherit;
}

.toast-close:hover {
  opacity: 1;
}

.toast-fade-enter-active,
.toast-fade-leave-active {
  transition: all 0.3s ease;
}

.toast-fade-enter-from {
  opacity: 0;
  transform: translateX(40px);
}

.toast-fade-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}

/* Loading Container */
.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-12) var(--space-8);
  gap: var(--space-4);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-card-divider);
  border-top-color: var(--color-brand-start);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  color: var(--color-card-text-muted);
  font-size: var(--text-sm);
}

/* Error Container */
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-10) var(--space-8);
  gap: var(--space-3);
  background: rgba(239, 68, 68, 0.05);
  border: 1px solid rgba(239, 68, 68, 0.15);
  border-radius: var(--radius-xl);
}

.error-icon {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
  font-weight: 700;
}

.error-title {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-card-heading);
}

.error-detail {
  font-size: var(--text-sm);
  color: var(--color-card-text-muted);
  text-align: center;
  max-width: 400px;
}

.retry-btn {
  margin-top: var(--space-2);
  padding: var(--space-2) var(--space-5);
  background: var(--color-brand-start);
  color: white;
  border: none;
  border-radius: var(--radius-lg);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.2s ease;
}

.retry-btn:hover {
  background: #5a6fd6;
}

/* Generation Error */
.generation-error {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: var(--radius-lg);
  margin-bottom: var(--space-4);
}

.error-icon-small {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.9rem;
  font-weight: 700;
  flex-shrink: 0;
}

.error-text {
  flex: 1;
  font-size: var(--text-sm);
  color: #991b1b;
}

.retry-btn-small {
  padding: var(--space-1) var(--space-3);
  background: #ef4444;
  color: white;
  border: none;
  border-radius: var(--radius-md, 8px);
  font-size: var(--text-xs, 0.75rem);
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  flex-shrink: 0;
}

.retry-btn-small:hover {
  background: #dc2626;
}

/* Button spinner */
.btn-spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  margin-right: var(--space-2);
  vertical-align: middle;
}

/* Steps Indicator */
.steps-indicator {
  display: flex;
  justify-content: center;
  gap: var(--space-2);
  margin-bottom: var(--space-8);
}

.step {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background: var(--color-card-bg);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-full);
  color: var(--color-card-text-muted);
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
  font-size: var(--text-sm);
}

.step:disabled { cursor: not-allowed; opacity: 0.5; }
.step.active { border-color: var(--color-brand-start); color: var(--color-brand-start); background: rgba(102, 126, 234, 0.1); }
.step.completed { border-color: var(--color-success); color: var(--color-success); }

.step-number {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.75rem;
  font-weight: 700;
  border: 2px solid currentColor;
}

/* Step Content */
.step-content h2 {
  font-size: var(--text-2xl);
  color: var(--color-card-heading);
  margin-bottom: var(--space-2);
}

.step-description {
  color: var(--color-card-text-muted);
  margin-bottom: var(--space-6);
}

/* Theme Grid */
.themes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--space-5);
}

/* Config Form */
.config-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.form-group label {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-card-text);
}

.form-group input,
.form-group select {
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-input-border);
  border-radius: var(--radius-lg);
  background: var(--color-input-bg);
  color: var(--color-input-text);
  font-size: var(--text-base);
  font-family: inherit;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--color-brand-start);
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15);
}

.form-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
}

/* Items Grid */
.items-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.item-chip {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-full);
  background: var(--color-card-bg);
  color: var(--color-card-text);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.item-chip:hover { border-color: var(--color-brand-start); }
.item-chip.selected {
  background: var(--color-brand-start);
  color: white;
  border-color: var(--color-brand-start);
}

/* Preview & Generate Layout */
.preview-generate-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-6);
}

.summary-card {
  background: var(--color-card-bg);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-xl);
  padding: var(--space-5);
  margin-bottom: var(--space-5);
}

.summary-card h3 {
  font-size: var(--text-base);
  margin-bottom: var(--space-4);
  color: var(--color-card-heading);
}

.summary-row {
  display: flex;
  justify-content: space-between;
  padding: var(--space-2) 0;
  font-size: var(--text-sm);
  border-bottom: 1px solid var(--color-card-divider);
}

.summary-row span { color: var(--color-card-text-muted); }
.summary-row strong { color: var(--color-card-text); }

/* Generation Progress */
.generation-progress {
  margin-bottom: var(--space-4);
}

.progress-bar {
  height: 8px;
  background: var(--color-card-divider);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-brand-start), var(--color-brand-end));
  border-radius: 4px;
  transition: width 0.3s ease;
}

.progress-text {
  font-size: var(--text-sm);
  color: var(--color-card-text-muted);
  text-align: center;
  margin-top: var(--space-2);
}

.generation-ready {
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  text-align: center;
  margin-bottom: var(--space-4);
}

.generation-ready p { color: var(--color-success); font-weight: 500; margin-bottom: var(--space-3); }

.download-btn {
  display: inline-block;
  padding: var(--space-2) var(--space-5);
  background: var(--color-success);
  color: white;
  border-radius: var(--radius-lg);
  text-decoration: none;
  font-weight: 500;
  font-size: var(--text-sm);
}

.download-btn:hover { background: var(--color-success-dark); }

.generate-btn {
  width: 100%;
  padding: var(--space-4);
  background: linear-gradient(135deg, var(--color-brand-start), var(--color-brand-end));
  color: white;
  border: none;
  border-radius: var(--radius-lg);
  font-size: var(--text-base);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
  display: flex;
  align-items: center;
  justify-content: center;
}

.generate-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.generate-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Navigation */
.step-navigation {
  display: flex;
  justify-content: space-between;
  margin-top: var(--space-8);
  padding-top: var(--space-6);
  border-top: 1px solid var(--color-card-divider);
}

.nav-spacer { flex: 1; }

.nav-btn {
  padding: var(--space-3) var(--space-6);
  border-radius: var(--radius-lg);
  font-size: var(--text-base);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.nav-btn.secondary {
  background: var(--color-btn-secondary-bg);
  border: 1px solid var(--color-btn-secondary-border);
  color: var(--color-btn-secondary-text);
}

.nav-btn.secondary:hover { background: var(--color-btn-secondary-hover-bg); }

.nav-btn.primary {
  background: var(--color-brand-start);
  border: none;
  color: white;
}

.nav-btn.primary:hover:not(:disabled) { background: #5a6fd6; }
.nav-btn:disabled { opacity: 0.5; cursor: not-allowed; }

@media (max-width: 768px) {
  .form-row { grid-template-columns: repeat(2, 1fr); }
  .preview-generate-layout { grid-template-columns: 1fr; }
  .step-label { display: none; }
  .toast { right: 12px; left: 12px; max-width: none; }
}
</style>
