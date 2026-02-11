<template>
  <div class="pdf-viewer">
    <div class="pdf-toolbar">
      <span class="pdf-title">PDF Preview</span>
      <div class="pdf-actions">
        <a :href="downloadUrl" class="pdf-action-btn download" download>
          <span class="action-icon">&#8681;</span>
          Download
        </a>
        <button class="pdf-action-btn close" @click="$emit('close')">
          <span class="action-icon">&times;</span>
          Close
        </button>
      </div>
    </div>
    <div class="pdf-frame-wrapper">
      <iframe
        :src="src"
        class="pdf-frame"
        frameborder="0"
        title="PDF Preview"
      ></iframe>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  src: string
  downloadUrl: string
}>()

defineEmits<{
  close: []
}>()
</script>

<style scoped>
.pdf-viewer {
  background: var(--color-card-bg);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-md);
}

.pdf-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-3) var(--space-4);
  background: var(--color-card-bg-secondary);
  border-bottom: 1px solid var(--color-card-divider);
}

.pdf-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-card-heading);
}

.pdf-actions {
  display: flex;
  gap: var(--space-2);
}

.pdf-action-btn {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-lg);
  font-size: var(--text-xs, 0.75rem);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
  text-decoration: none;
}

.pdf-action-btn.download {
  background: var(--color-success);
  color: white;
  border: none;
}

.pdf-action-btn.download:hover {
  background: var(--color-success-dark);
}

.pdf-action-btn.close {
  background: var(--color-card-bg);
  color: var(--color-card-text-muted);
  border: 1px solid var(--color-card-border);
}

.pdf-action-btn.close:hover {
  border-color: var(--color-brand-start);
  color: var(--color-brand-start);
}

.action-icon {
  font-size: 1rem;
  line-height: 1;
}

.pdf-frame-wrapper {
  width: 100%;
  aspect-ratio: 8.5 / 11;
  max-height: 600px;
}

.pdf-frame {
  width: 100%;
  height: 100%;
  border: none;
  display: block;
}
</style>
