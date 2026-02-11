<template>
  <div class="thumbnail-gallery">
    <div class="gallery-header">
      <h4 class="gallery-title">Page Preview</h4>
      <span class="gallery-count">{{ totalPages }} pages</span>
    </div>

    <div class="gallery-scroll" ref="scrollContainer">
      <div
        v-for="thumb in thumbnails"
        :key="thumb.page"
        :class="['page-card', `type-${thumb.type}`]"
        @click="openLightbox(thumb)"
      >
        <span class="page-badge">{{ thumb.page }}</span>
        <span class="page-icon">{{ iconFor(thumb.type) }}</span>
        <span class="page-label">{{ thumb.label }}</span>
        <span class="page-type">{{ formatType(thumb.type) }}</span>
      </div>
    </div>

    <!-- Lightbox -->
    <Transition name="lightbox">
      <div v-if="activeThumbnail" class="lightbox-overlay" @click.self="activeThumbnail = null">
        <div class="lightbox-card">
          <button class="lightbox-close" @click="activeThumbnail = null">&times;</button>
          <div class="lightbox-icon">{{ iconFor(activeThumbnail.type) }}</div>
          <div class="lightbox-page">Page {{ activeThumbnail.page }}</div>
          <h3 class="lightbox-label">{{ activeThumbnail.label }}</h3>
          <p class="lightbox-desc">{{ activeThumbnail.description }}</p>
          <span class="lightbox-type-badge">{{ formatType(activeThumbnail.type) }}</span>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Thumbnail {
  page: number
  type: string
  label: string
  description: string
}

defineProps<{
  thumbnails: Thumbnail[]
  totalPages: number
}>()

const activeThumbnail = ref<Thumbnail | null>(null)

const ICON_MAP: Record<string, string> = {
  cover: '\uD83D\uDCD6',
  trace_and_color: '\u270D\uFE0F',
  which_different: '\uD83D\uDD0D',
  count_circle: '\uD83D\uDD22',
  match: '\uD83D\uDD17',
  word_to_image: '\uD83D\uDCDD',
  find_circle: '\u2B55',
}

function iconFor(type: string): string {
  return ICON_MAP[type] || '\uD83D\uDCC4'
}

function formatType(type: string): string {
  return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function openLightbox(thumb: Thumbnail) {
  activeThumbnail.value = thumb
}
</script>

<style scoped>
.thumbnail-gallery {
  margin-bottom: var(--space-6);
}

.gallery-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-3);
}

.gallery-title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-card-heading);
}

.gallery-count {
  font-size: var(--text-xs, 0.75rem);
  color: var(--color-card-text-muted);
  background: var(--color-card-bg);
  padding: 2px 10px;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-card-border);
}

.gallery-scroll {
  display: flex;
  gap: var(--space-3);
  overflow-x: auto;
  padding: var(--space-2) 0 var(--space-3);
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
}

.gallery-scroll::-webkit-scrollbar {
  height: 6px;
}

.gallery-scroll::-webkit-scrollbar-track {
  background: var(--color-card-divider);
  border-radius: 3px;
}

.gallery-scroll::-webkit-scrollbar-thumb {
  background: var(--color-brand-start);
  border-radius: 3px;
  opacity: 0.5;
}

.page-card {
  flex-shrink: 0;
  width: 110px;
  height: 140px;
  background: var(--color-card-bg);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-lg);
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  cursor: pointer;
  transition: all 0.2s ease;
  scroll-snap-align: start;
  position: relative;
  overflow: hidden;
}

.page-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--color-brand-start), var(--color-brand-end));
  opacity: 0;
  transition: opacity 0.2s ease;
}

.page-card:hover {
  border-color: var(--color-brand-start);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
}

.page-card:hover::before {
  opacity: 1;
}

.page-card.type-cover {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.08), rgba(118, 75, 162, 0.08));
  border-color: rgba(102, 126, 234, 0.3);
}

.page-badge {
  position: absolute;
  top: 6px;
  left: 6px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--color-card-bg-secondary);
  border: 1px solid var(--color-card-divider);
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--color-card-text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
}

.page-icon {
  font-size: 1.8rem;
  line-height: 1;
}

.page-label {
  font-size: 0.7rem;
  font-weight: 500;
  color: var(--color-card-text);
  text-align: center;
  line-height: 1.2;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.page-type {
  font-size: 0.6rem;
  color: var(--color-card-text-muted);
  text-align: center;
}

/* Lightbox */
.lightbox-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9998;
}

.lightbox-card {
  background: var(--color-card-bg);
  border: 1px solid var(--color-card-border);
  border-radius: var(--radius-xl);
  padding: var(--space-8);
  max-width: 340px;
  width: 90%;
  text-align: center;
  position: relative;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.lightbox-close {
  position: absolute;
  top: var(--space-3);
  right: var(--space-3);
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 1px solid var(--color-card-border);
  background: var(--color-card-bg);
  color: var(--color-card-text-muted);
  font-size: 1.1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
  font-family: inherit;
}

.lightbox-close:hover {
  border-color: var(--color-brand-start);
  color: var(--color-brand-start);
}

.lightbox-icon {
  font-size: 3rem;
  margin-bottom: var(--space-3);
}

.lightbox-page {
  font-size: var(--text-xs, 0.75rem);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-brand-start);
  margin-bottom: var(--space-2);
}

.lightbox-label {
  font-size: var(--text-lg);
  color: var(--color-card-heading);
  margin-bottom: var(--space-2);
}

.lightbox-desc {
  font-size: var(--text-sm);
  color: var(--color-card-text-muted);
  line-height: 1.5;
  margin-bottom: var(--space-4);
}

.lightbox-type-badge {
  display: inline-block;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.12), rgba(118, 75, 162, 0.12));
  color: var(--color-brand-start);
}

/* Transitions */
.lightbox-enter-active,
.lightbox-leave-active {
  transition: opacity 0.2s ease;
}

.lightbox-enter-active .lightbox-card,
.lightbox-leave-active .lightbox-card {
  transition: transform 0.2s ease;
}

.lightbox-enter-from,
.lightbox-leave-to {
  opacity: 0;
}

.lightbox-enter-from .lightbox-card {
  transform: scale(0.95);
}

.lightbox-leave-to .lightbox-card {
  transform: scale(0.95);
}
</style>
