<template>
  <div class="comparison-layout">
    <h1>Multi-Model Comparison</h1>
    <div class="comparison-grid">
      <div
        v-for="model in models"
        :key="model.id"
        class="model-column"
        :data-model="model.id"
      >
        <div class="model-header">
          <h2>{{ model.name }}</h2>
        </div>

        <!-- Loading State -->
        <div v-if="model.loading" class="model-loading">
          <div class="spinner"></div>
          <span>Generating...</span>
        </div>

        <!-- Image Output -->
        <div v-else-if="model.output" class="model-output">
          <img
            :src="model.output"
            :alt="`${model.name} output`"
            class="output-image"
          />
        </div>

        <!-- Placeholder -->
        <div v-else class="model-placeholder">
          Waiting for output...
        </div>

        <!-- Metadata Footer -->
        <div v-if="model.meta" class="model-meta">
          <div class="meta-row">
            <span class="meta-label">Duration</span>
            <span class="meta-value">{{ model.meta.duration }}s</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">Cost</span>
            <span class="meta-value cost">${{ model.meta.cost }}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">Size</span>
            <span class="meta-value">{{ model.meta.size }}</span>
          </div>
          <div v-if="model.meta.cached" class="meta-badge cached">Cached</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface ModelMeta {
  duration: string
  cost: string
  size: string
  cached: boolean
}

interface Model {
  id: string
  name: string
  output?: string
  loading?: boolean
  meta?: ModelMeta
}

const models = ref<Model[]>([
  { id: 'gemini', name: 'Gemini Flash', output: undefined },
  { id: 'imagen', name: 'Imagen 4.0', output: undefined },
  { id: 'imagen-ultra', name: 'Imagen 4.0 Ultra', output: undefined },
])

const setModelOutput = (modelId: string, output: string, meta?: ModelMeta) => {
  const model = models.value.find(m => m.id === modelId)
  if (model) {
    model.output = output
    model.loading = false
    if (meta) {
      model.meta = meta
    }
  }
}

const setModelLoading = (modelId: string, loading: boolean) => {
  const model = models.value.find(m => m.id === modelId)
  if (model) {
    model.loading = loading
    if (loading) {
      model.output = undefined
      model.meta = undefined
    }
  }
}

defineExpose({ setModelOutput, setModelLoading, models })
</script>

<style scoped>
.comparison-layout {
  padding: var(--space-8);
  max-width: 1400px;
  margin: 0 auto;
}

.comparison-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-8);
  margin-top: var(--space-8);
}

.model-column {
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--color-card-bg);
  display: flex;
  flex-direction: column;
}

.model-header {
  background: var(--color-header-accent);
  color: white;
  padding: var(--space-4);
  text-align: center;
}

.model-header h2 {
  margin: 0;
  font-size: 1.1rem;
}

.model-output {
  padding: var(--space-4);
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
}

.output-image {
  max-width: 100%;
  max-height: 400px;
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-md);
}

.model-placeholder {
  color: var(--color-card-text-muted);
  text-align: center;
  padding: var(--space-8);
  font-style: italic;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.model-loading {
  text-align: center;
  padding: var(--space-8);
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  color: var(--color-card-text-muted);
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(102, 126, 234, 0.2);
  border-top-color: var(--color-brand-start);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Metadata Footer */
.model-meta {
  border-top: 1px solid var(--color-card-border);
  padding: var(--space-3) var(--space-4);
  background: var(--color-card-bg);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.meta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.85rem;
}

.meta-label {
  color: var(--color-card-text-muted);
  font-weight: 500;
}

.meta-value {
  color: var(--color-card-text);
  font-family: var(--font-mono, monospace);
  font-size: 0.85rem;
}

.meta-value.cost {
  color: var(--color-success, #4caf50);
  font-weight: 600;
}

.meta-badge.cached {
  align-self: flex-start;
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: rgba(102, 126, 234, 0.15);
  color: var(--color-brand-start);
  font-weight: 600;
}

h1 {
  color: var(--color-heading-on-shell);
  margin: 0 0 var(--space-4) 0;
}

@media (max-width: 1024px) {
  .comparison-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .comparison-grid {
    grid-template-columns: 1fr;
  }
}
</style>
