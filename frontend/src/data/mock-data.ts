export interface MockPrompt {
  id: string
  name: string
  promptText: string
  category: string
  tags: string[]
  isPublic: boolean
  createdAt: string
  updatedAt: string
  rating: number
  usageCount: number
}

export interface MockVariation {
  id: string
  prompt: string
  model: string
  imageUrl: string
  rating: number
  seed: number
  generatedAt: string
  notes: string
  parameters: Record<string, string | number>
}

export const samplePrompts: MockPrompt[] = [
  {
    id: 'sample-1',
    name: 'Woodland Animals',
    promptText: 'A playful fox sitting in a sun-dappled forest clearing, surrounded by mushrooms and wildflowers, clean line art suitable for children, no shading',
    category: 'animals',
    tags: ['animals', 'forest', 'kids', 'nature'],
    isPublic: true,
    createdAt: '2026-02-01T10:30:00Z',
    updatedAt: '2026-02-05T14:20:00Z',
    rating: 4,
    usageCount: 12,
  },
  {
    id: 'sample-2',
    name: 'Underwater Kingdom',
    promptText: 'A majestic sea turtle gliding through a coral reef with tropical fish, detailed line work with intricate coral patterns, suitable for adults and teens',
    category: 'animals',
    tags: ['ocean', 'detailed', 'animals', 'underwater'],
    isPublic: true,
    createdAt: '2026-01-28T09:15:00Z',
    updatedAt: '2026-02-03T11:45:00Z',
    rating: 5,
    usageCount: 23,
  },
  {
    id: 'sample-3',
    name: 'Geometric Mandala',
    promptText: 'A complex floral mandala with repeating petal patterns, concentric circles, and geometric borders, black outlines on white, adult coloring level',
    category: 'patterns',
    tags: ['mandala', 'geometric', 'adult', 'relaxation'],
    isPublic: false,
    createdAt: '2026-02-03T16:00:00Z',
    updatedAt: '2026-02-03T16:00:00Z',
    rating: 5,
    usageCount: 8,
  },
  {
    id: 'sample-4',
    name: 'Fantasy Castle',
    promptText: 'A fairy tale castle on a hilltop with a friendly dragon circling overhead, clouds, stars, and a winding path, kid-friendly coloring page',
    category: 'landscape',
    tags: ['fantasy', 'castle', 'dragon', 'kids'],
    isPublic: true,
    createdAt: '2026-02-06T08:45:00Z',
    updatedAt: '2026-02-07T10:30:00Z',
    rating: 3,
    usageCount: 5,
  },
]

export const sampleVariations: MockVariation[] = [
  {
    id: 'var-1',
    prompt: 'A majestic lion portrait with flowing mane, detailed line art',
    model: 'dall-e-3',
    imageUrl: 'https://picsum.photos/seed/lion-coloring/400/400',
    rating: 4,
    seed: 42581,
    generatedAt: '2026-02-08T14:30:00Z',
    notes: 'Great mane detail, could use more background elements',
    parameters: { style: 'line-art', quality: 'hd', size: '1024x1024' },
  },
  {
    id: 'var-2',
    prompt: 'A symmetrical butterfly mandala with floral wings',
    model: 'stable-diffusion',
    imageUrl: 'https://picsum.photos/seed/butterfly-mandala/400/400',
    rating: 5,
    seed: 73920,
    generatedAt: '2026-02-08T15:15:00Z',
    notes: 'Perfect symmetry, excellent for adult coloring',
    parameters: { style: 'mandala', steps: 50, cfg_scale: 7.5 },
  },
  {
    id: 'var-3',
    prompt: 'A cozy cottage with garden, smoke from chimney, winding path',
    model: 'midjourney',
    imageUrl: 'https://picsum.photos/seed/cottage-coloring/400/400',
    rating: 3,
    seed: 19847,
    generatedAt: '2026-02-07T11:00:00Z',
    notes: 'Nice composition but lines too thin in some areas',
    parameters: { style: 'coloring-book', version: '6.1' },
  },
]
