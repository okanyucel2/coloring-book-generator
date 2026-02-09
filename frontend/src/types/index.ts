/** Shared type definitions for Coloring Book Generator frontend */

export interface ConfirmDialogConfig {
  title: string
  message: string
  confirmText: string
  cancelText: string
  destructive: boolean
  onConfirm: () => void
}

export interface Notification {
  type: string
  message: string
}

export interface Prompt {
  id: string
  name: string
  promptText: string
  category?: string
  tags: string[]
  isPublic: boolean
  isFavorite?: boolean
  createdAt?: string
  updatedAt?: string
}

export interface Variation {
  id: string
  model: string
  prompt: string
  imageUrl: string
  seed: number
  width: number
  height: number
  rating: number | null
  notes: string | null
  createdAt: string
}
