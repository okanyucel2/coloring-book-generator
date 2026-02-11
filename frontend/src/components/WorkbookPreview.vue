<template>
  <div class="workbook-preview">
    <h3 class="preview-title">Workbook Preview</h3>

    <div v-if="!workbookId" class="preview-empty">
      <div class="empty-icon">&#128214;</div>
      <p>Configure and create your workbook to see a preview</p>
    </div>

    <div v-else-if="loading" class="preview-loading">
      <div class="loading-spinner"></div>
      <p>Loading preview...</p>
    </div>

    <div v-else class="preview-content">
      <div class="preview-header">
        <h4>{{ previewData?.title || 'Workbook' }}</h4>
        <span class="status-badge" :class="previewData?.status">
          {{ previewData?.status || 'draft' }}
        </span>
      </div>

      <div class="preview-details">
        <div class="detail-row">
          <span class="detail-label">Theme</span>
          <span class="detail-value">{{ previewData?.theme }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">Total Pages</span>
          <span class="detail-value">{{ previewData?.total_pages }}</span>
        </div>
      </div>

      <div v-if="previewData?.activity_mix" class="activity-breakdown">
        <h5>Activity Breakdown</h5>
        <div v-for="(count, type) in previewData.activity_mix" :key="type" class="breakdown-row">
          <span class="breakdown-type">{{ formatActivityType(type as string) }}</span>
          <div class="breakdown-bar-wrapper">
            <div class="breakdown-bar" :style="{ width: barWidth(count as number) }"></div>
          </div>
          <span class="breakdown-count">{{ count }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { apiService } from '@/services/api'

interface PreviewData {
  id: string
  status: string
  title: string
  theme: string
  total_pages: number
  activity_mix: Record<string, number>
}

const props = defineProps<{
  workbookId: string | null
  refreshKey?: number
}>()

const loading = ref(false)
const previewData = ref<PreviewData | null>(null)

async function fetchPreview(id: string) {
  loading.value = true
  try {
    previewData.value = await apiService.get<PreviewData>(`/workbooks/${id}/preview`)
  } catch (e) {
    console.error('Preview failed:', e)
  } finally {
    loading.value = false
  }
}

watch(() => props.workbookId, async (id) => {
  if (!id) {
    previewData.value = null
    return
  }
  await fetchPreview(id)
}, { immediate: true })

watch(() => props.refreshKey, async () => {
  if (props.workbookId) {
    await fetchPreview(props.workbookId)
  }
})

function formatActivityType(type: string): string {
  return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function barWidth(count: number): string {
  const max = Math.max(...Object.values(previewData.value?.activity_mix || { a: 1 }))
  return `${(count / max) * 100}%`
}
</script>

<style scoped>
.workbook-preview {
  background: var(--color-card-bg);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-xl);
  padding: var(--space-6);
  box-shadow: var(--shadow-md);
}

.preview-title {
  font-size: var(--text-lg);
  color: var(--color-card-heading);
  margin-bottom: var(--space-5);
}

.preview-empty {
  text-align: center;
  padding: var(--space-8) 0;
}

.empty-icon {
  font-size: 3rem;
  opacity: 0.4;
  margin-bottom: var(--space-3);
}

.preview-empty p {
  color: var(--color-card-text-muted);
}

.preview-loading {
  text-align: center;
  padding: var(--space-8) 0;
}

.loading-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid rgba(102, 126, 234, 0.2);
  border-top-color: var(--color-brand-start);
  border-radius: 50%;
  margin: 0 auto var(--space-3);
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-4);
}

.preview-header h4 {
  font-size: var(--text-base);
  color: var(--color-card-heading);
}

.status-badge {
  font-size: 0.75rem;
  padding: 2px 10px;
  border-radius: var(--radius-full);
  font-weight: 600;
  text-transform: uppercase;
}

.status-badge.draft { background: rgba(156, 163, 175, 0.2); color: #6b7280; }
.status-badge.generating { background: rgba(245, 158, 11, 0.2); color: #d97706; }
.status-badge.ready { background: var(--color-success-light); color: var(--color-success-dark); }
.status-badge.failed { background: var(--color-danger-light); color: var(--color-danger-text); }

.preview-details {
  margin-bottom: var(--space-5);
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--color-card-divider);
}

.detail-label {
  color: var(--color-card-text-muted);
  font-size: var(--text-sm);
}

.detail-value {
  font-weight: 500;
  color: var(--color-card-text);
  font-size: var(--text-sm);
  text-transform: capitalize;
}

.activity-breakdown h5 {
  font-size: var(--text-sm);
  color: var(--color-card-heading);
  margin-bottom: var(--space-3);
}

.breakdown-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
}

.breakdown-type {
  font-size: 0.75rem;
  color: var(--color-card-text-muted);
  min-width: 100px;
}

.breakdown-bar-wrapper {
  flex: 1;
  height: 8px;
  background: var(--color-card-divider);
  border-radius: 4px;
  overflow: hidden;
}

.breakdown-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--color-brand-start), var(--color-brand-end));
  border-radius: 4px;
  transition: width 0.3s ease;
}

.breakdown-count {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--color-card-text);
  min-width: 20px;
  text-align: right;
}
</style>
