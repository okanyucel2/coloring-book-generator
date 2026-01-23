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
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.comparison-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
  margin-top: 2rem;
}

.model-column {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
  background: #f9f9f9;
}

.model-header {
  background: #2c3e50;
  color: white;
  padding: 1rem;
  text-align: center;
}

.model-header h2 {
  margin: 0;
  font-size: 1.1rem;
}

.model-output {
  padding: 1rem;
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.output-image {
  max-width: 100%;
  max-height: 400px;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.model-placeholder {
  color: #999;
  text-align: center;
  padding: 2rem;
  font-style: italic;
}

h1 {
  color: #2c3e50;
  margin: 0 0 1rem 0;
}
</style>
