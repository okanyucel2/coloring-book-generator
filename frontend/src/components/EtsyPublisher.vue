<template>
  <div class="etsy-publisher">
    <h3 class="publisher-title">Etsy Publishing</h3>

    <!-- Connection Status -->
    <div class="connection-section">
      <div :class="['connection-status', { connected: isConnected }]">
        <span class="status-dot"></span>
        <span>{{ isConnected ? 'Connected to Etsy' : 'Not connected' }}</span>
      </div>
      <button
        v-if="!isConnected"
        class="connect-btn"
        @click="connectEtsy"
        :disabled="connecting"
      >
        {{ connecting ? 'Connecting...' : 'Connect Etsy Account' }}
      </button>
      <button
        v-else
        class="disconnect-btn"
        @click="disconnectEtsy"
      >
        Disconnect
      </button>
    </div>

    <!-- Listing Preview (available even when not connected) -->
    <div v-if="workbookId && listingPreview" class="listing-preview">
      <h4>Listing Preview</h4>

      <div class="preview-field">
        <label>Title</label>
        <input v-model="editableTitle" type="text" maxlength="140" />
        <span class="char-count">{{ editableTitle.length }}/140</span>
      </div>

      <div class="preview-field">
        <label>Price</label>
        <div class="price-input">
          <span class="currency">$</span>
          <input v-model.number="editablePrice" type="number" min="0.99" max="50" step="0.01" />
        </div>
      </div>

      <div class="preview-field">
        <label>Tags ({{ listingPreview.tags.length }}/13)</label>
        <div class="tags-display">
          <span v-for="tag in listingPreview.tags" :key="tag" class="tag">{{ tag }}</span>
        </div>
      </div>

      <div class="preview-field">
        <label>Description</label>
        <textarea v-model="editableDescription" rows="6" readonly></textarea>
      </div>
    </div>

    <!-- Publish Button -->
    <div v-if="workbookId" class="publish-section">
      <div v-if="!isConnected" class="publish-notice">
        Connect your Etsy account to publish workbooks
      </div>

      <div v-if="publishing" class="publishing-status">
        Publishing to Etsy...
      </div>

      <div v-if="publishResult" class="publish-result">
        <div class="result-success">
          <span>Published successfully!</span>
          <p>Listing ID: {{ publishResult.listing_id }}</p>
          <p>Status: {{ publishResult.state }}</p>
        </div>
      </div>

      <button
        v-if="isConnected && !publishing"
        class="publish-btn"
        @click="publishWorkbook"
        :disabled="!canPublish"
      >
        Publish to Etsy
      </button>
    </div>

    <div v-if="!workbookId" class="no-workbook">
      <p>Generate a workbook first, then you can publish it to Etsy</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { apiService } from '@/services/api'

interface ListingPreview {
  title: string
  description: string
  price: number
  tags: string[]
}

interface PublishResult {
  listing_id: number
  title: string
  state: string
  price: number
}

const props = defineProps<{
  workbookId: string | null
}>()

const isConnected = ref(false)
const connecting = ref(false)
const publishing = ref(false)
const listingPreview = ref<ListingPreview | null>(null)
const publishResult = ref<PublishResult | null>(null)
const editableTitle = ref('')
const editableDescription = ref('')
const editablePrice = ref(4.99)

const canPublish = computed(() =>
  isConnected.value && props.workbookId && !publishing.value
)

import { computed } from 'vue'

onMounted(async () => {
  await checkConnection()
})

watch(() => props.workbookId, async (id) => {
  if (id) {
    await loadListingPreview(id)
  }
}, { immediate: true })

async function checkConnection() {
  try {
    const status = await apiService.get<{ connected: boolean }>('/etsy/status')
    isConnected.value = status.connected
  } catch {
    isConnected.value = false
  }
}

async function connectEtsy() {
  connecting.value = true
  try {
    const resp = await apiService.get<{ auth_url: string }>('/etsy/auth-url')
    // Open Etsy OAuth in new window
    window.open(resp.auth_url, '_blank', 'width=600,height=700')
  } catch (e) {
    console.error('Failed to get auth URL:', e)
  } finally {
    connecting.value = false
  }
}

async function disconnectEtsy() {
  try {
    await apiService.post('/etsy/disconnect')
    isConnected.value = false
  } catch (e) {
    console.error('Disconnect failed:', e)
  }
}

async function loadListingPreview(workbookId: string) {
  try {
    const preview = await apiService.get<ListingPreview>(
      `/etsy/workbooks/${workbookId}/listing-preview`
    )
    listingPreview.value = preview
    editableTitle.value = preview.title
    editableDescription.value = preview.description
    editablePrice.value = preview.price
  } catch (e) {
    console.error('Failed to load listing preview:', e)
  }
}

async function publishWorkbook() {
  if (!props.workbookId) return

  publishing.value = true
  publishResult.value = null

  try {
    const result = await apiService.post<PublishResult>(
      `/etsy/workbooks/${props.workbookId}/publish`,
      {
        shop_id: 0, // Will need to be configured
        price_override: editablePrice.value,
      }
    )
    publishResult.value = result
  } catch (e) {
    console.error('Publish failed:', e)
  } finally {
    publishing.value = false
  }
}
</script>

<style scoped>
.etsy-publisher {
  background: var(--color-card-bg);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-xl);
  padding: var(--space-6);
  box-shadow: var(--shadow-md);
}

.publisher-title {
  font-size: var(--text-lg);
  color: var(--color-card-heading);
  margin-bottom: var(--space-5);
}

/* Connection */
.connection-section {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  background: var(--color-card-bg-secondary);
  border-radius: var(--radius-lg);
  margin-bottom: var(--space-5);
}

.connection-status {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--color-card-text-muted);
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-danger);
}

.connection-status.connected .status-dot {
  background: var(--color-success);
}

.connect-btn {
  padding: var(--space-2) var(--space-4);
  background: #f97316;
  color: white;
  border: none;
  border-radius: var(--radius-lg);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
}

.connect-btn:hover:not(:disabled) { background: #ea580c; }
.connect-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.disconnect-btn {
  padding: var(--space-2) var(--space-4);
  background: transparent;
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-lg);
  color: var(--color-card-text);
  font-size: var(--text-sm);
  cursor: pointer;
  font-family: inherit;
}

/* Listing Preview */
.listing-preview {
  margin-bottom: var(--space-5);
}

.listing-preview h4 {
  font-size: var(--text-base);
  color: var(--color-card-heading);
  margin-bottom: var(--space-4);
}

.preview-field {
  margin-bottom: var(--space-4);
  position: relative;
}

.preview-field label {
  display: block;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-card-text);
  margin-bottom: var(--space-1);
}

.preview-field input,
.preview-field textarea {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-input-border);
  border-radius: var(--radius-lg);
  background: var(--color-input-bg);
  color: var(--color-input-text);
  font-size: var(--text-sm);
  font-family: inherit;
}

.preview-field textarea {
  resize: vertical;
}

.char-count {
  position: absolute;
  right: var(--space-3);
  top: var(--space-1);
  font-size: 0.7rem;
  color: var(--color-card-text-muted);
}

.price-input {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.currency {
  font-size: var(--text-lg);
  color: var(--color-card-text);
}

.price-input input {
  width: 100px;
}

.tags-display {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}

.tag {
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background: rgba(102, 126, 234, 0.1);
  color: var(--color-brand-start);
}

/* Publish */
.publish-section {
  padding-top: var(--space-4);
  border-top: 1px solid var(--color-card-divider);
}

.publish-notice {
  text-align: center;
  padding: var(--space-4);
  color: var(--color-card-text-muted);
  font-size: var(--text-sm);
}

.publishing-status {
  text-align: center;
  padding: var(--space-4);
  color: #f97316;
  font-weight: 500;
}

.publish-result {
  margin-bottom: var(--space-4);
}

.result-success {
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.3);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  text-align: center;
}

.result-success span { color: var(--color-success-dark); font-weight: 600; }
.result-success p { font-size: var(--text-sm); color: var(--color-card-text-muted); margin-top: var(--space-1); }

.publish-btn {
  width: 100%;
  padding: var(--space-3) var(--space-5);
  background: #f97316;
  color: white;
  border: none;
  border-radius: var(--radius-lg);
  font-size: var(--text-base);
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.2s ease;
}

.publish-btn:hover:not(:disabled) { background: #ea580c; transform: translateY(-1px); }
.publish-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.no-workbook {
  text-align: center;
  padding: var(--space-6);
  color: var(--color-card-text-muted);
}
</style>
