<template>
  <div
    class="model-output-panel panel"
    :class="[qualityClass, { selected: isSelected }]"
    tabindex="0"
    @click="toggleSelection"
    @keydown.enter="toggleSelection"
    @keydown.space="toggleSelection"
  >
    <!-- Header with Model Name -->
    <div class="model-header">
      {{ modelName }}
    </div>

    <!-- Image Display -->
    <div class="image-container">
      <img
        v-if="!imageError"
        class="model-image"
        :src="imageUrl"
        :alt="`${modelName} output`"
        @error="handleImageError"
      />
      <div v-else class="image-placeholder">
        <span>Failed to load image</span>
      </div>
      <div v-if="imageError" class="error-message">
        Failed to load image from {{ modelName }}
      </div>
    </div>

    <!-- Metadata Section -->
    <div class="metadata-section">
      <div class="metric">
        <span class="metric-label">Time:</span>
        <span class="metric-generation-time">{{ generationTime }}s</span>
      </div>
      <div class="metric">
        <span class="metric-label">Quality:</span>
        <span class="metric-quality-score">{{ Math.round(qualityScore * 100) }}%</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

interface Props {
  modelName: string
  imageUrl: string
  generationTime: number
  qualityScore: number
  selected?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  selected: false,
})

const emit = defineEmits<{
  select: [modelName: string]
}>()

const imageError = ref(false)
const isSelected = ref(props.selected)

// Watch prop changes and sync local state
watch(
  () => props.selected,
  (newVal) => {
    isSelected.value = newVal
  }
)

const qualityClass = computed(() => {
  if (props.qualityScore > 0.85) {
    return 'quality-premium'
  } else if (props.qualityScore >= 0.7) {
    return 'quality-medium'
  } else {
    return 'quality-low'
  }
})

const handleImageError = () => {
  imageError.value = true
}

const toggleSelection = () => {
  isSelected.value = !isSelected.value
  emit('select', props.modelName)
}
</script>

<style scoped>
.model-output-panel {
  display: flex;
  flex-direction: column;
  border: 2px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: 16px;
  background-color: var(--color-surface-primary);
  cursor: pointer;
  transition: all var(--transition-slow) ease;
  user-select: none;
}

.model-output-panel:hover {
  border-color: var(--color-text-tertiary);
  box-shadow: var(--shadow-md);
}

.model-output-panel:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.1);
}

.model-output-panel.selected {
  border-color: var(--color-primary);
  background-color: var(--color-primary-surface);
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.3);
}

.model-output-panel.quality-premium {
  border-left: 4px solid var(--color-success);
}

.model-output-panel.quality-medium {
  border-left: 4px solid var(--color-warning);
}

.model-output-panel.quality-low {
  border-left: 4px solid var(--color-danger);
}

.model-header {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 12px;
  text-align: center;
}

.image-container {
  position: relative;
  width: 100%;
  margin-bottom: 12px;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-surface-muted);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.model-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  max-height: 300px;
}

.image-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 200px;
  background-color: #eeeeee;
  color: var(--color-text-tertiary);
  font-size: 14px;
  border-radius: var(--radius-md);
}

.error-message {
  position: absolute;
  bottom: 8px;
  left: 8px;
  right: 8px;
  background-color: var(--color-danger-light);
  color: var(--color-danger-text);
  padding: 8px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  text-align: center;
}

.metadata-section {
  display: flex;
  gap: 16px;
  justify-content: space-around;
  padding: 8px 0;
  border-top: 1px solid var(--color-border-light);
}

.metric {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.metric-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  font-weight: 500;
}

.metric-generation-time,
.metric-quality-score {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

@media (max-width: 768px) {
  .model-output-panel {
    padding: 12px;
  }

  .model-header {
    font-size: 14px;
    margin-bottom: 8px;
  }

  .image-container {
    min-height: 150px;
  }

  .model-image {
    max-height: 200px;
  }

  .metadata-section {
    gap: 12px;
  }
}
</style>
