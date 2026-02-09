<template>
  <Transition name="dialog">
    <div
      v-if="visible"
      class="dialog-overlay"
      role="alertdialog"
      aria-modal="true"
      :aria-label="title"
      @click.self="cancel"
      @keydown.escape="cancel"
    >
      <div class="dialog-content" ref="dialogRef">
        <h3 class="dialog-title">{{ title }}</h3>
        <p class="dialog-message">{{ message }}</p>
        <div class="dialog-actions">
          <button
            ref="cancelRef"
            class="btn btn-cancel"
            @click="cancel"
          >
            {{ cancelText }}
          </button>
          <button
            :class="['btn', destructive ? 'btn-destructive' : 'btn-confirm']"
            @click="confirmAction"
          >
            {{ confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

interface Props {
  visible: boolean
  title?: string
  message: string
  confirmText?: string
  cancelText?: string
  destructive?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Confirm',
  confirmText: 'Confirm',
  cancelText: 'Cancel',
  destructive: false,
})

const emit = defineEmits<{
  (e: 'confirm'): void
  (e: 'cancel'): void
  (e: 'update:visible', value: boolean): void
}>()

const cancelRef = ref<HTMLButtonElement | null>(null)
const dialogRef = ref<HTMLDivElement | null>(null)

watch(() => props.visible, async (newVal) => {
  if (newVal) {
    await nextTick()
    cancelRef.value?.focus()
  }
})

const cancel = () => {
  emit('update:visible', false)
  emit('cancel')
}

const confirmAction = () => {
  emit('update:visible', false)
  emit('confirm')
}
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: var(--color-surface-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal-backdrop);
}

.dialog-content {
  background: var(--color-surface-primary);
  border-radius: var(--radius-xl);
  padding: var(--space-8);
  max-width: 420px;
  width: 90%;
  box-shadow: var(--shadow-2xl);
  z-index: var(--z-modal);
}

.dialog-title {
  font-size: var(--text-xl);
  color: var(--color-text-primary);
  margin-bottom: var(--space-3);
}

.dialog-message {
  font-size: var(--text-base);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-6);
  line-height: 1.5;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}

.btn {
  padding: var(--space-2) var(--space-5);
  border: none;
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-base) ease;
  font-family: inherit;
}

.btn-cancel {
  background: var(--color-surface-subtle);
  color: var(--color-text-primary);
}

.btn-cancel:hover {
  background: var(--color-border-light);
}

.btn-confirm {
  background: var(--color-primary);
  color: white;
}

.btn-confirm:hover {
  background: var(--color-primary-hover);
}

.btn-destructive {
  background: var(--color-danger);
  color: white;
}

.btn-destructive:hover {
  background: var(--color-danger-dark);
}

/* Transition */
.dialog-enter-active {
  transition: opacity var(--transition-base) ease;
}

.dialog-enter-active .dialog-content {
  transition: transform var(--transition-base) ease, opacity var(--transition-base) ease;
}

.dialog-leave-active {
  transition: opacity var(--transition-fast) ease;
}

.dialog-leave-active .dialog-content {
  transition: transform var(--transition-fast) ease, opacity var(--transition-fast) ease;
}

.dialog-enter-from {
  opacity: 0;
}

.dialog-enter-from .dialog-content {
  transform: scale(0.95);
  opacity: 0;
}

.dialog-leave-to {
  opacity: 0;
}

.dialog-leave-to .dialog-content {
  transform: scale(0.95);
  opacity: 0;
}
</style>
