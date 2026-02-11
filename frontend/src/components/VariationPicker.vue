<template>
  <div class="variation-picker" v-if="visible">
    <h3>Select Images for Each Item</h3>
    <p class="picker-description">Choose from previously generated AI images for each workbook item</p>

    <div v-if="loading" class="picker-loading">
      <div class="spinner-small"></div>
      <span>Finding matching images...</span>
    </div>

    <div v-else class="picker-grid">
      <div v-for="item in items" :key="item" class="picker-item">
        <span class="item-name">{{ formatName(item) }}</span>
        <div class="variation-options">
          <template v-if="(matches[item] ?? []).length > 0">
            <button
              v-for="v in (matches[item] ?? [])"
              :key="v.id"
              :class="['var-thumb', { selected: selected[item] === v.id }]"
              @click="select(item, v.id)"
              :title="v.prompt"
            >
              <img :src="v.imageUrl" :alt="v.prompt" />
            </button>
          </template>
          <span v-else class="no-match">No matching variations</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { apiService } from '@/services/api'

interface VariationInfo {
  id: string
  prompt: string
  model: string
  imageUrl: string
  rating: number
}

const props = defineProps<{
  items: string[]
  visible: boolean
}>()

const emit = defineEmits<{
  'update:variationMap': [map: Record<string, string>]
}>()

const matches = ref<Record<string, VariationInfo[]>>({})
const selected = ref<Record<string, string>>({})
const loading = ref(false)

function formatName(name: string): string {
  return name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function select(item: string, variationId: string) {
  if (selected.value[item] === variationId) {
    // Deselect
    const next = { ...selected.value }
    delete next[item]
    selected.value = next
  } else {
    selected.value = { ...selected.value, [item]: variationId }
  }
  emit('update:variationMap', { ...selected.value })
}

async function fetchMatches() {
  if (!props.items.length) return
  loading.value = true
  try {
    const itemsParam = props.items.join(',')
    const resp = await apiService.get<{ data: Record<string, VariationInfo[]> }>(
      `/variations/match?items=${encodeURIComponent(itemsParam)}`
    )
    matches.value = resp.data
  } catch (e) {
    console.error('Failed to fetch variation matches:', e)
  } finally {
    loading.value = false
  }
}

watch(() => props.visible, (val) => {
  if (val && props.items.length > 0) {
    fetchMatches()
  }
})

onMounted(() => {
  if (props.visible && props.items.length > 0) {
    fetchMatches()
  }
})
</script>

<style scoped>
.variation-picker {
  background: var(--color-card-bg);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-xl);
  padding: var(--space-5);
  margin-top: var(--space-4);
}

.variation-picker h3 {
  font-size: var(--text-base);
  color: var(--color-card-heading);
  margin-bottom: var(--space-1);
}

.picker-description {
  font-size: var(--text-sm);
  color: var(--color-card-text-muted);
  margin-bottom: var(--space-4);
}

.picker-loading {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  color: var(--color-card-text-muted);
  font-size: var(--text-sm);
}

.spinner-small {
  width: 20px;
  height: 20px;
  border: 2px solid var(--color-card-divider);
  border-top-color: var(--color-brand-start);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.picker-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.picker-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--color-card-divider);
}

.picker-item:last-child {
  border-bottom: none;
}

.item-name {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-card-text);
  min-width: 120px;
  flex-shrink: 0;
}

.variation-options {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  align-items: center;
}

.var-thumb {
  width: 64px;
  height: 64px;
  padding: 2px;
  border: 2px solid var(--color-card-border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  background: var(--color-card-bg);
  transition: all 0.15s ease;
  overflow: hidden;
}

.var-thumb:hover {
  border-color: var(--color-brand-start);
}

.var-thumb.selected {
  border-color: var(--color-brand-start);
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.3);
}

.var-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: calc(var(--radius-lg) - 3px);
}

.no-match {
  font-size: var(--text-xs, 0.75rem);
  color: var(--color-card-text-muted);
  font-style: italic;
}
</style>
