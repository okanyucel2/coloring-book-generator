<template>
  <div :class="['skeleton', `skeleton-${variant}`]">
    <template v-if="variant === 'card'">
      <div class="skeleton-image shimmer"></div>
      <div class="skeleton-lines">
        <div class="skeleton-line shimmer" style="width: 80%"></div>
        <div class="skeleton-line shimmer" style="width: 60%"></div>
        <div class="skeleton-line shimmer short" style="width: 40%"></div>
      </div>
    </template>
    <template v-else-if="variant === 'row'">
      <div class="skeleton-thumb shimmer"></div>
      <div class="skeleton-lines">
        <div class="skeleton-line shimmer" style="width: 70%"></div>
        <div class="skeleton-line shimmer short" style="width: 50%"></div>
      </div>
    </template>
  </div>
</template>

<script setup>
defineProps({
  variant: {
    type: String,
    default: 'card',
    validator: (v) => ['card', 'row'].includes(v),
  },
})
</script>

<style scoped>
.skeleton {
  overflow: hidden;
}

.skeleton-card {
  background: var(--color-surface-primary);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-xl);
  padding: var(--space-4);
}

.skeleton-image {
  width: 100%;
  height: 140px;
  border-radius: var(--radius-lg);
  margin-bottom: var(--space-4);
}

.skeleton-lines {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.skeleton-line {
  height: 14px;
  border-radius: var(--radius-sm);
}

.skeleton-line.short {
  height: 10px;
}

.skeleton-row {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  background: var(--color-surface-primary);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
}

.skeleton-thumb {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-lg);
  flex-shrink: 0;
}

.skeleton-row .skeleton-lines {
  flex: 1;
}

.shimmer {
  background: linear-gradient(
    90deg,
    var(--color-surface-muted) 25%,
    var(--color-surface-subtle) 50%,
    var(--color-surface-muted) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
