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
        <div v-if="model.output" class="model-output">
          <img 
            :src="model.output" 
            :alt="`${model.name} output`"
            class="output-image"
          />
        </div>
        <div v-else class="model-placeholder">
          Waiting for output...
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Model {
  id: string
  name: string
  output?: string
}

const models = ref<Model[]>([
  { id: 'claude', name: 'Claude 3.5', output: undefined },
  { id: 'gpt4', name: 'GPT-4', output: undefined },
  { id: 'gemini', name: 'Gemini 2.0', output: undefined },
])

const setModelOutput = (modelId: string, output: string) => {
  const model = models.value.find(m => m.id === modelId)
  if (model) {
    model.output = output
  }
}

defineExpose({ setModelOutput, models })
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
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--color-surface-tertiary);
}

.model-header {
  background: #2c3e50;
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
}

.output-image {
  max-width: 100%;
  max-height: 400px;
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-md);
}

.model-placeholder {
  color: var(--color-text-tertiary);
  text-align: center;
  padding: var(--space-8);
  font-style: italic;
}

h1 {
  color: #2c3e50;
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
