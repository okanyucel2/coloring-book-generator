<template>
  <div
    :class="['theme-card', { selected: isSelected }]"
    @click="$emit('select', theme.slug)"
    role="button"
    tabindex="0"
    @keydown.enter="$emit('select', theme.slug)"
  >
    <div class="theme-icon">{{ themeIcon }}</div>
    <h3 class="theme-name">{{ theme.display_name }}</h3>
    <p class="theme-info">{{ theme.item_count }} items</p>
    <div class="theme-tags">
      <span v-for="group in theme.age_groups" :key="group" class="age-tag">
        {{ group.replace('_', ' ') }}
      </span>
    </div>
    <div v-if="isSelected" class="selected-badge">Selected</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Theme {
  slug: string
  display_name: string
  category: string
  items: string[]
  item_count: number
  age_groups: string[]
  etsy_tags: string[]
}

const props = defineProps<{
  theme: Theme
  isSelected: boolean
}>()

defineEmits<{
  select: [slug: string]
}>()

const themeIcon = computed(() => {
  const icons: Record<string, string> = {
    vehicles: '\uD83D\uDE97',
    animals: '\uD83D\uDC3E',
  }
  return icons[props.theme.slug] || '\uD83C\uDFA8'
})
</script>

<style scoped>
.theme-card {
  background: var(--color-card-bg);
  border: 2px solid var(--color-card-border);
  border-radius: var(--radius-xl);
  padding: var(--space-6);
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  box-shadow: var(--shadow-sm);
}

.theme-card:hover {
  border-color: var(--color-brand-start);
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.theme-card.selected {
  border-color: var(--color-brand-start);
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
}

.theme-icon {
  font-size: 3rem;
  margin-bottom: var(--space-3);
}

.theme-name {
  font-size: var(--text-xl);
  color: var(--color-card-heading);
  margin-bottom: var(--space-2);
}

.theme-info {
  font-size: var(--text-sm);
  color: var(--color-card-text-muted);
  margin-bottom: var(--space-3);
}

.theme-tags {
  display: flex;
  gap: var(--space-2);
  justify-content: center;
  flex-wrap: wrap;
}

.age-tag {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background: rgba(102, 126, 234, 0.15);
  color: var(--color-brand-start);
  text-transform: capitalize;
}

.selected-badge {
  position: absolute;
  top: var(--space-3);
  right: var(--space-3);
  font-size: 0.75rem;
  padding: 2px 10px;
  border-radius: var(--radius-full);
  background: var(--color-brand-start);
  color: white;
  font-weight: 600;
}
</style>
