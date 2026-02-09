<template>
  <div class="activity-mixer">
    <h3 class="mixer-title">Activity Distribution</h3>
    <p class="mixer-description">Adjust how many pages of each activity type to include</p>

    <div class="activity-list">
      <div v-for="activity in activities" :key="activity.key" class="activity-row">
        <div class="activity-info">
          <span class="activity-icon">{{ activity.icon }}</span>
          <div>
            <span class="activity-name">{{ activity.label }}</span>
            <span class="activity-desc">{{ activity.description }}</span>
          </div>
        </div>
        <div class="activity-controls">
          <button
            class="count-btn"
            @click="decrement(activity.key)"
            :disabled="(modelValue[activity.key] || 0) <= 0"
          >-</button>
          <span class="count-value">{{ modelValue[activity.key] || 0 }}</span>
          <button
            class="count-btn"
            @click="increment(activity.key)"
          >+</button>
        </div>
      </div>
    </div>

    <div class="mixer-total">
      <span>Total activity pages:</span>
      <strong>{{ totalPages }}</strong>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const activities = [
  { key: 'trace_and_color', label: 'Trace & Color', icon: '\u270D\uFE0F', description: 'Dashed outline + colored reference' },
  { key: 'which_different', label: 'Which Is Different?', icon: '\uD83D\uDD0D', description: 'Spot the odd one out' },
  { key: 'count_circle', label: 'Count and Circle', icon: '\uD83D\uDD22', description: 'Count items in a grid' },
  { key: 'match', label: 'Match the Pairs', icon: '\uD83D\uDD17', description: 'Draw lines to match' },
  { key: 'word_to_image', label: 'Word to Image', icon: '\uD83D\uDCDD', description: 'Connect words to pictures' },
  { key: 'find_circle', label: 'Find and Circle', icon: '\u2B55', description: 'Find the correct image' },
]

const props = defineProps<{
  modelValue: Record<string, number>
}>()

const emit = defineEmits<{
  'update:modelValue': [value: Record<string, number>]
}>()

const totalPages = computed(() => {
  return Object.values(props.modelValue).reduce((sum, v) => sum + (v || 0), 0)
})

function increment(key: string) {
  const updated = { ...props.modelValue, [key]: (props.modelValue[key] || 0) + 1 }
  emit('update:modelValue', updated)
}

function decrement(key: string) {
  const current = props.modelValue[key] || 0
  if (current > 0) {
    const updated = { ...props.modelValue, [key]: current - 1 }
    emit('update:modelValue', updated)
  }
}
</script>

<style scoped>
.activity-mixer {
  background: var(--color-card-bg);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-xl);
  padding: var(--space-6);
  box-shadow: var(--shadow-md);
}

.mixer-title {
  font-size: var(--text-lg);
  color: var(--color-card-heading);
  margin-bottom: var(--space-1);
}

.mixer-description {
  font-size: var(--text-sm);
  color: var(--color-card-text-muted);
  margin-bottom: var(--space-5);
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.activity-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3) var(--space-4);
  background: var(--color-card-bg-secondary);
  border-radius: var(--radius-lg);
}

.activity-info {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.activity-icon {
  font-size: 1.5rem;
}

.activity-name {
  display: block;
  font-weight: 500;
  color: var(--color-card-text);
  font-size: var(--text-sm);
}

.activity-desc {
  display: block;
  font-size: 0.75rem;
  color: var(--color-card-text-muted);
}

.activity-controls {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.count-btn {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-card-border);
  background: var(--color-card-bg);
  color: var(--color-card-text);
  font-size: var(--text-lg);
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
  font-family: inherit;
}

.count-btn:hover:not(:disabled) {
  background: var(--color-card-bg-secondary);
  border-color: var(--color-brand-start);
}

.count-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.count-value {
  font-size: var(--text-lg);
  font-weight: 600;
  min-width: 24px;
  text-align: center;
  color: var(--color-card-text);
}

.mixer-total {
  margin-top: var(--space-5);
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-card-divider);
  display: flex;
  justify-content: space-between;
  font-size: var(--text-base);
  color: var(--color-card-text);
}

.mixer-total strong {
  color: var(--color-brand-start);
}
</style>
