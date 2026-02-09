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

export interface WorkbookTheme {
  slug: string
  display_name: string
  category: string
  items: string[]
  item_count: number
  age_groups: string[]
  etsy_tags: string[]
}

export interface WorkbookConfig {
  theme: string
  title: string
  subtitle?: string
  age_min: number
  age_max: number
  page_count: number
  items: string[]
  activity_mix: Record<string, number>
  page_size: string
}

export interface WorkbookResponse {
  id: string
  theme: string
  title: string
  subtitle?: string
  age_min: number
  age_max: number
  page_count: number
  items: string[]
  activity_mix: Record<string, number>
  page_size: string
  status: 'draft' | 'generating' | 'ready' | 'failed'
  progress: number | null
  pdf_url: string | null
  etsy_listing_id: string | null
  created_at: string | null
  updated_at: string | null
}
