<template>
  <div class="app-container">
    <!-- Navigation Header -->
    <header class="app-header">
      <div class="header-brand">
        <h1>Coloring Book Generator</h1>
        <span class="header-subtitle">AI-Powered Image Generation Studio</span>
      </div>
      <nav class="header-nav">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id"
          :class="['nav-tab', { active: activeTab === tab.id }]"
        >
          <span class="tab-icon">{{ tab.icon }}</span>
          <span class="tab-label">{{ tab.label }}</span>
        </button>
      </nav>
      <button
        class="theme-toggle"
        :aria-label="isDark ? 'Switch to light mode' : 'Switch to dark mode'"
        @click="toggleTheme"
      >
        {{ isDark ? '\u2600\uFE0F' : '\uD83C\uDF19' }}
      </button>
    </header>

    <!-- Main Content Area -->
    <main class="app-main">
      <!-- Workbook Builder Tab -->
      <div v-show="activeTab === 'workbook'" class="tab-content">
        <WorkbookBuilder />
      </div>

      <!-- Prompt Library Tab -->
      <div v-show="activeTab === 'library'" class="tab-content">
        <PromptLibraryUI />
      </div>

      <!-- Variation History Tab -->
      <div v-show="activeTab === 'history'" class="tab-content">
        <VariationHistoryComparison />
      </div>

      <!-- Model Comparison Tab -->
      <div v-show="activeTab === 'comparison'" class="tab-content">
        <div class="comparison-wrapper">
          <div class="comparison-controls-header">
            <h2>Multi-Model Comparison</h2>
            <p class="description">Compare outputs from different AI models side by side</p>
          </div>
          <ComparisonLayout ref="comparisonRef" />

          <!-- Demo Controls -->
          <div class="demo-section">
            <h3>Demo Controls</h3>
            <div class="demo-buttons">
              <button @click="simulateOutput('claude')" class="demo-btn">
                Simulate Claude Output
              </button>
              <button @click="simulateOutput('gpt4')" class="demo-btn">
                Simulate GPT-4 Output
              </button>
              <button @click="simulateOutput('gemini')" class="demo-btn">
                Simulate Gemini Output
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Customization Tab -->
      <div v-show="activeTab === 'customize'" class="tab-content">
        <div class="customize-wrapper">
          <PromptCustomizationForm
            :templates="promptTemplates"
            @generate="handleGenerate"
            @reset="handleReset"
            @copy="handleCopy"
          />
          <div class="output-section">
            <ModelOutputPanel
              v-if="generatedOutput"
              :modelName="generatedOutput.modelName"
              :imageUrl="generatedOutput.imageUrl"
              :generationTime="generatedOutput.generationTime"
              :qualityScore="generatedOutput.qualityScore"
              @select="handleOutputSelect"
            />
            <div v-else-if="isGenerating" class="output-loading">
              <div class="loading-spinner"></div>
              <p>Generating image...</p>
            </div>
            <div v-else class="output-placeholder">
              <div class="placeholder-icon">&#127912;</div>
              <p>Submit a customization to see the output</p>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- Footer -->
    <footer class="app-footer">
      <p>Coloring Book Generator v0.1.0 | Powered by Genesis AI Platform</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useTheme } from '@/composables/useTheme'
import WorkbookBuilder from '@/components/WorkbookBuilder.vue'
import PromptLibraryUI from '@/components/PromptLibraryUI.vue'
import VariationHistoryComparison from '@/components/VariationHistoryComparison.vue'
import ComparisonLayout from '@/components/ComparisonLayout.vue'
import PromptCustomizationForm from '@/components/PromptCustomizationForm.vue'
import ModelOutputPanel from '@/components/ModelOutputPanel.vue'
import { apiService } from '@/services/api'

interface Tab {
  id: string
  label: string
  icon: string
}

interface Template {
  id: string
  name: string
  description: string
  template: string
}

interface GeneratedOutput {
  modelName: string
  imageUrl: string
  generationTime: number
  qualityScore: number
}

interface GeneratePayload {
  prompt: string
  variables: Record<string, string>
  selectedTemplate: string | null
}

const tabs: Tab[] = [
  { id: 'workbook', label: 'Workbook Builder', icon: '\u{1F4D6}' },
  { id: 'library', label: 'Prompt Library', icon: '\u{1F4DA}' },
  { id: 'history', label: 'Variation History', icon: '\u{1F4C5}' },
  { id: 'comparison', label: 'Model Comparison', icon: '\u{1F4C8}' },
  { id: 'customize', label: 'Customize', icon: '\u{2699}' },
]

// Demo prompt templates
const promptTemplates: Template[] = [
  {
    id: 'animal-simple',
    name: 'Simple Animal',
    description: 'Clean line art of animals for coloring',
    template: 'A simple coloring book outline of a {{animal}}, black and white line art, no shading, kid-friendly design'
  },
  {
    id: 'nature-scene',
    name: 'Nature Scene',
    description: 'Beautiful nature landscapes',
    template: 'A coloring book page featuring a {{scene}} with {{elements}}, detailed line work, suitable for all ages'
  },
  {
    id: 'mandala',
    name: 'Mandala Pattern',
    description: 'Intricate mandala designs',
    template: 'A {{complexity}} mandala pattern with {{theme}} motifs, symmetrical design, clear outlines for coloring'
  },
  {
    id: 'custom',
    name: 'Custom Prompt',
    description: 'Start from scratch',
    template: ''
  }
]

const { isDark, toggleTheme } = useTheme()
const activeTab = ref('workbook')
const comparisonRef = ref<InstanceType<typeof ComparisonLayout> | null>(null)
const generatedOutput = ref<GeneratedOutput | null>(null)
const isGenerating = ref(false)

// Demo function to simulate model output
const simulateOutput = (modelId: string) => {
  if (comparisonRef.value) {
    // Using a placeholder image URL for demo
    const demoImageUrl = `https://picsum.photos/seed/${modelId}-${Date.now()}/400/300`
    comparisonRef.value.setModelOutput(modelId, demoImageUrl)
  }
}

const handleGenerate = async (payload: GeneratePayload) => {
  console.log('Generation requested:', payload)
  isGenerating.value = true
  generatedOutput.value = null

  const startTime = performance.now()

  try {
    const result = await apiService.post<{
      id: string
      prompt: string
      model: string
      imageUrl: string
      seed: number
      generatedAt: string
    }>('/generate', {
      prompt: payload.prompt,
      model: 'dalle3',
      style: 'coloring_book',
    })

    const elapsed = (performance.now() - startTime) / 1000

    generatedOutput.value = {
      modelName: result.model || 'DALL-E 3',
      imageUrl: result.imageUrl || '',
      generationTime: elapsed,
      qualityScore: 0.92,
    }
  } catch (error) {
    console.error('Generation failed:', error)
    // Fallback to placeholder on error so UI doesn't break
    generatedOutput.value = {
      modelName: 'DALL-E 3 (offline)',
      imageUrl: `https://picsum.photos/seed/fallback-${Date.now()}/600/400`,
      generationTime: 0,
      qualityScore: 0,
    }
  } finally {
    isGenerating.value = false
  }
}

const handleReset = () => {
  console.log('Form reset')
  generatedOutput.value = null
}

const handleCopy = () => {
  console.log('Prompt copied to clipboard')
}

const handleOutputSelect = (modelName: string) => {
  console.log('Output selected:', modelName)
}
</script>

<style>
/* Global Reset */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  height: 100%;
  font-family: var(--font-sans);
  background: linear-gradient(135deg, var(--color-shell-bg-start) 0%, var(--color-shell-bg-mid) 50%, var(--color-shell-bg-end) 100%);
  color: var(--color-shell-text);
  min-height: 100vh;
}

#app {
  min-height: 100vh;
}
</style>

<style scoped>
.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* Header */
.app-header {
  background: var(--color-shell-surface);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--color-shell-border);
  padding: var(--space-4) var(--space-8);
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: var(--z-header);
}

.header-brand h1 {
  font-size: var(--text-2xl);
  font-weight: 700;
  background: linear-gradient(135deg, var(--color-brand-start) 0%, var(--color-brand-end) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
}

.header-subtitle {
  font-size: 0.85rem;
  color: var(--color-shell-text-subtle);
  display: block;
  margin-top: var(--space-1);
}

.header-nav {
  display: flex;
  gap: var(--space-2);
}

.nav-tab {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-5);
  background: transparent;
  border: 1px solid var(--color-shell-border);
  border-radius: var(--radius-lg);
  color: var(--color-shell-text-muted);
  cursor: pointer;
  transition: all var(--transition-slow) ease;
  font-family: inherit;
  font-size: 0.95rem;
}

.nav-tab:hover {
  background: var(--color-shell-surface-hover);
  border-color: var(--color-shell-border-hover);
  color: var(--color-shell-text);
}

.nav-tab.active {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(118, 75, 162, 0.2) 100%);
  border-color: var(--color-brand-start);
  color: var(--color-tab-active-text);
}

.tab-icon {
  font-size: var(--text-lg);
}

.tab-label {
  font-weight: 500;
}

/* Theme Toggle */
.theme-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background: transparent;
  border: 1px solid var(--color-shell-border);
  border-radius: var(--radius-full);
  color: var(--color-shell-text);
  cursor: pointer;
  font-size: var(--text-xl);
  transition: all var(--transition-slow) ease;
  margin-left: var(--space-4);
  flex-shrink: 0;
}

.theme-toggle:hover {
  background: var(--color-shell-surface-hover);
  border-color: var(--color-shell-border-hover);
  transform: rotate(15deg);
}

/* Main Content */
.app-main {
  flex: 1;
  padding: var(--space-8);
  overflow-y: auto;
}

.tab-content {
  animation: fadeIn var(--transition-slow) ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Comparison Tab */
.comparison-wrapper {
  max-width: 1400px;
  margin: 0 auto;
}

.comparison-controls-header {
  text-align: center;
  margin-bottom: var(--space-8);
}

.comparison-controls-header h2 {
  font-size: 1.8rem;
  color: var(--color-heading-on-shell);
  margin-bottom: var(--space-2);
}

.comparison-controls-header .description {
  color: var(--color-shell-text-subtle);
  font-size: var(--text-base);
}

.demo-section {
  margin-top: var(--space-8);
  padding: var(--space-6);
  background: var(--color-shell-surface);
  border-radius: var(--radius-xl);
  border: 1px solid var(--color-shell-border);
}

.demo-section h3 {
  font-size: var(--text-lg);
  color: var(--color-shell-text);
  margin-bottom: var(--space-4);
}

.demo-buttons {
  display: flex;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.demo-btn {
  padding: var(--space-3) var(--space-6);
  background: linear-gradient(135deg, var(--color-brand-start) 0%, var(--color-brand-end) 100%);
  border: none;
  border-radius: var(--radius-lg);
  color: white;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-slow) ease;
  font-family: inherit;
}

.demo-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-brand);
}

/* Customize Tab */
.customize-wrapper {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-8);
}

.output-section {
  display: flex;
  align-items: flex-start;
  justify-content: center;
}

.output-placeholder {
  background: var(--color-shell-surface);
  border: 2px dashed var(--color-shell-border-hover);
  border-radius: var(--radius-xl);
  padding: 4rem var(--space-8);
  text-align: center;
  width: 100%;
  max-width: 500px;
}

.placeholder-icon {
  font-size: 4rem;
  margin-bottom: var(--space-4);
  opacity: 0.5;
}

.output-placeholder p {
  color: var(--color-shell-text-subtle);
  font-size: var(--text-base);
}

.output-loading {
  background: var(--color-shell-surface);
  border: 2px solid rgba(102, 126, 234, 0.3);
  border-radius: var(--radius-xl);
  padding: 4rem var(--space-8);
  text-align: center;
  width: 100%;
  max-width: 500px;
}

.output-loading p {
  color: var(--color-shell-text-muted);
  font-size: var(--text-base);
  margin-top: var(--space-4);
}

.loading-spinner {
  width: 48px;
  height: 48px;
  border: 4px solid rgba(102, 126, 234, 0.2);
  border-top-color: var(--color-brand-start);
  border-radius: var(--radius-full);
  margin: 0 auto;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Footer */
.app-footer {
  padding: var(--space-6) var(--space-8);
  text-align: center;
  border-top: 1px solid var(--color-shell-border);
  background: var(--color-footer-bg);
}

.app-footer p {
  color: var(--color-shell-text-dim);
  font-size: var(--text-sm);
}

/* Responsive */
@media (max-width: 1024px) {
  .app-header {
    flex-direction: column;
    gap: var(--space-4);
    padding: var(--space-4);
  }

  .header-nav {
    flex-wrap: wrap;
    justify-content: center;
  }

  .nav-tab {
    padding: 0.625rem var(--space-4);
    font-size: var(--text-sm);
  }

  .customize-wrapper {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .app-main {
    padding: var(--space-4);
  }

  .tab-label {
    display: none;
  }

  .nav-tab {
    padding: var(--space-3);
  }

  .tab-icon {
    font-size: var(--text-xl);
  }

  .demo-buttons {
    flex-direction: column;
  }
}
</style>
