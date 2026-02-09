# Coloring Book Generator - Frontend Polish Plan

## Context

Coloring Book Generator (project001) frontend'i Vue 3 + Vite + TypeScript ile yazilmis, 5 component, 2 service, 1 utils dosyasindan olusuyor. 29/29 E2E test geciyorken su sorunlar tespit edildi:

- **Sifir CSS variable** - 47 unique renk, 7 border-radius, 10+ shadow, 16+ font-size tamami hardcoded
- **Bos ekranlar** - Backend yok, "Failed to load" hatalari gorunuyor, icerik bos
- **UX eksikleri** - Browser confirm() dialog, WCAG AA fail eden disabled butonlar, focus tutarsizligi
- **Test gap** - sanitizer.js (XSS korumalari) 0 test, 2 buyuk component 0 test
- **Storybook yok** - Genesis'in hazir @genesis/storybook-config altyapisi kullanilmiyor

**Genesis Altyapi Avantajlari (yeniden kullanim):**
- `@genesis/storybook-config` - Hazir Storybook setup (Argos CI, viewport presets, dark mode decorator)
- `@genesis/visual-regression` - Storycap + responsive screenshot presets
- `cigkoftecibey design-tokens.css` - Kanitlanmis token sistemi (referans pattern)
- `restaurant95 UI paketi` - ConfirmDialog, Skeleton, EmptyState, Toast, BaseModal zaten var (referans)
- Atomic design pattern (atoms/molecules/organisms)

---

## Phase 0: Storybook Setup

**Hedef:** @genesis/storybook-config ile Storybook kurup, mevcut 5 component icin story dosyalari olusturmak. Boylece her gorsel degisiklik aninda izlenebilir.

### Yeni Dosyalar
- `.storybook/main.ts` - @genesis/storybook-config kullanarak
- `.storybook/preview.ts` - Dark/light bg, viewport presets
- `src/components/stories/App.stories.ts`
- `src/components/stories/PromptLibraryUI.stories.ts`
- `src/components/stories/VariationHistoryComparison.stories.ts`
- `src/components/stories/ComparisonLayout.stories.ts`
- `src/components/stories/ModelOutputPanel.stories.ts`
- `src/components/stories/PromptCustomizationForm.stories.ts`

### Degisecek Dosyalar
- `package.json` - storybook scripts + devDependencies ekleme

### Storybook Config Pattern (referans: restaurant95)
```typescript
// .storybook/main.ts
import { createStorybookConfig } from '@genesis/storybook-config'
export default createStorybookConfig({
  projectSlug: 'project001',
  storiesGlob: '../src/components/stories/**/*.stories.@(js|jsx|ts|tsx)',
})
```

### Story Pattern (her component icin)
```typescript
// ComparisonLayout.stories.ts
import ComparisonLayout from '../ComparisonLayout.vue'
export default { component: ComparisonLayout, title: 'Organisms/ComparisonLayout' }
export const Default = {}
export const WithOutputs = { /* setModelOutput simulated */ }
```

### Dogrulama
```bash
pnpm storybook  # port 6006'da acilmali, tum componentler gorunmeli
```

---

## Phase 1: CSS Design System Foundation

**Hedef:** Tum hardcoded degerleri CSS variable'a tasimak. Sifir gorsel degisiklik.

**Referans:** `cigkoftecibey-webapp/frontend/src/assets/styles/design-tokens.css` pattern'ini takip ediyoruz - ayni adlandirma kurallari, ayni yapı.

### Yeni Dosya
- `src/assets/design-tokens.css`

### Token Yapisi (cigkoftecibey pattern'ine uyumlu)

```css
:root {
  /* ========================================
     COLORING BOOK GENERATOR - DESIGN TOKENS v1.0
     Pattern: cigkoftecibey design-tokens.css
     ======================================== */

  /* === SHELL (Dark App Chrome) === */
  --color-shell-bg-start: #1a1a2e;
  --color-shell-bg-mid: #16213e;
  --color-shell-bg-end: #0f3460;
  --color-shell-surface: rgba(255, 255, 255, 0.05);
  --color-shell-surface-hover: rgba(255, 255, 255, 0.08);
  --color-shell-border: rgba(255, 255, 255, 0.1);
  --color-shell-border-hover: rgba(255, 255, 255, 0.2);
  --color-shell-text: #e0e0e0;
  --color-shell-text-muted: #a0aec0;
  --color-shell-text-subtle: #8892b0;
  --color-shell-text-dim: #64748b;

  /* === CONTENT AREAS (Light Panels) === */
  --color-content-bg-start: #f5f7fa;
  --color-content-bg-end: #c3cfe2;

  /* Surfaces (cards, modals, panels) */
  --color-surface-primary: #ffffff;
  --color-surface-secondary: #fafafa;
  --color-surface-tertiary: #f9f9f9;
  --color-surface-muted: #f5f5f5;
  --color-surface-subtle: #f0f0f0;
  --color-surface-overlay: rgba(0, 0, 0, 0.5);

  /* === TEXT (Light Theme Content) === */
  --color-text-primary: #333;
  --color-text-secondary: #666;
  --color-text-tertiary: #999;

  /* === BRAND === */
  --color-brand-start: #667eea;
  --color-brand-end: #764ba2;

  /* === SEMANTIC (cigkoftecibey uyumlu adlandirma) === */
  --color-primary: #2196f3;
  --color-primary-hover: #1976d2;
  --color-primary-light: #e3f2fd;
  --color-primary-surface: #f0f7ff;

  --color-success: #4CAF50;
  --color-success-hover: #45a049;
  --color-success-dark: #388e3c;
  --color-success-light: #f1f8f6;

  --color-warning: #ff9800;
  --color-warning-light: #fff3e0;
  --color-warning-surface: #fff3cd;
  --color-warning-text: #856404;

  --color-danger: #f44336;
  --color-danger-hover: #da190b;
  --color-danger-dark: #d32f2f;
  --color-danger-light: #ffebee;
  --color-danger-text: #c62828;

  --color-star: #ffc107;

  /* === BORDER === */
  --color-border-light: #e0e0e0;

  /* === TYPOGRAPHY (cigkoftecibey uyumlu) === */
  --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  --font-mono: 'Monaco', 'Courier New', monospace;
  --text-xs: 0.75rem;     /* 12px */
  --text-sm: 0.875rem;    /* 14px */
  --text-base: 1rem;      /* 16px */
  --text-lg: 1.125rem;    /* 18px */
  --text-xl: 1.25rem;     /* 20px */
  --text-2xl: 1.5rem;     /* 24px */
  --text-3xl: 1.875rem;   /* 30px */

  /* === SPACING (4px base - cigkoftecibey uyumlu) === */
  --space-1: 0.25rem;     /* 4px */
  --space-2: 0.5rem;      /* 8px */
  --space-3: 0.75rem;     /* 12px */
  --space-4: 1rem;        /* 16px */
  --space-5: 1.25rem;     /* 20px */
  --space-6: 1.5rem;      /* 24px */
  --space-8: 2rem;        /* 32px */
  --space-10: 2.5rem;     /* 40px */
  --space-12: 3rem;       /* 48px */

  /* === BORDER RADIUS (cigkoftecibey uyumlu) === */
  --radius-sm: 0.25rem;   /* 4px */
  --radius-md: 0.375rem;  /* 6px */
  --radius-lg: 0.5rem;    /* 8px */
  --radius-xl: 0.75rem;   /* 12px */
  --radius-pill: 1.25rem; /* 20px */
  --radius-full: 9999px;  /* circle */

  /* === SHADOWS === */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 2px 8px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 4px 12px rgba(0, 0, 0, 0.15);
  --shadow-xl: 0 8px 16px rgba(0, 0, 0, 0.15);
  --shadow-2xl: 0 8px 32px rgba(0, 0, 0, 0.2);
  --shadow-toast: 0 4px 12px rgba(0, 0, 0, 0.3);
  --shadow-brand: 0 4px 15px rgba(102, 126, 234, 0.4);

  /* Focus Rings */
  --focus-ring: 0 0 0 3px rgba(33, 150, 243, 0.15);

  /* === TRANSITIONS (cigkoftecibey uyumlu) === */
  --transition-fast: 150ms;
  --transition-base: 200ms;
  --transition-slow: 300ms;
  --ease-out: cubic-bezier(0.33, 1, 0.68, 1);

  /* === Z-INDEX (cigkoftecibey uyumlu) === */
  --z-sticky: 20;
  --z-fixed: 30;
  --z-modal-backdrop: 40;
  --z-modal: 50;
  --z-toast: 60;
  --z-header: 100;
}
```

### Degisecek Dosyalar (7)
| Dosya | Islem |
|-------|-------|
| `src/main.ts` | `import './assets/design-tokens.css'` |
| `src/App.vue` | ~30 hardcoded deger -> variable |
| `src/components/PromptLibraryUI.vue` | ~60 hardcoded deger -> variable |
| `src/components/VariationHistoryComparison.vue` | ~55 hardcoded deger -> variable |
| `src/components/ComparisonLayout.vue` | ~15 hardcoded deger -> variable |
| `src/components/ModelOutputPanel.vue` | ~25 hardcoded deger -> variable |
| `src/components/PromptCustomizationForm.vue` | ~35 hardcoded deger -> variable |

### Dogrulama
```bash
npx playwright test --reporter=list  # 29/29 pass olmali (sifir gorsel degisiklik)
pnpm storybook                       # Storybook'ta tum componentler ayni gorunmeli
```

---

## Phase 2: Mock Data ile Dolu Ekranlar

**Hedef:** Bos "Failed to load" ekranlari yerine gercekci ornek veriler gostermek.

### Yeni Dosya
- `src/data/mock-data.ts` - 4 ornek prompt + 3 ornek variation

### Ornek Prompt Verileri
- "Woodland Animals" - fox in forest, kids, animals tag
- "Underwater Kingdom" - sea turtle, coral reef, detailed tag
- "Geometric Mandala" - floral mandala, adult coloring tag
- "Fantasy Castle" - fairy tale castle, dragon, kids tag

### Ornek Variation Verileri
- Lion portrait (dall-e-3, rating 4, seed 42581)
- Butterfly mandala (stable-diffusion, rating 5, seed 73920)
- Cozy cottage (midjourney, rating 3, seed 19847)

### Degisiklikler (3 dosya)
| Dosya | Degisiklik |
|-------|-----------|
| `PromptLibraryUI.vue` | `loadPrompts()` catch -> samplePrompts fallback, toast "info" |
| `VariationHistoryComparison.vue` | `loadHistory()` catch -> sampleVariations fallback, toast "info" |
| `App.vue` | `handleGenerate()` daha gercekci demo akisi |

### Storybook Story Guncelleme
- PromptLibraryUI.stories.ts: "With Sample Data" variant
- VariationHistoryComparison.stories.ts: "With History" variant

### Dogrulama
```bash
npx playwright test --reporter=list   # E2E testler permissive, pass olmali
npx playwright test --grep "capture"  # Screenshot'lari kontrol et - dolu ekranlar
pnpm storybook                        # Storybook'ta dolu gorunum
```

---

## Phase 3: Kritik UX Duzeltmeleri

**Hedef:** Accessibility, focus tutarliligi, custom confirm dialog, responsive grid.

**Referans:** Restaurant95 UI paketi zaten ConfirmDialog organism'i iceriyor - ayni pattern'i kullaniyoruz.

### Yeni Dosya
- `src/components/ConfirmDialog.vue` - restaurant95 `organisms/ConfirmDialog.vue` referansiyla

### 3a. Focus Rengi Tutarliligi
Yesil `#4CAF50` focus -> `var(--color-primary)` mavi (6 yer):
- PromptLibraryUI.vue: search-input:focus, form input:focus, textarea:focus
- VariationHistoryComparison.vue: filter-select:focus, search-input:focus, notes-input:focus

### 3b. Disabled Buton Contrast (WCAG AA)
Simdi: `#999 on #ccc` = 1.96:1 (FAIL)
Sonra: `var(--color-text-secondary) on var(--color-surface-subtle)` = `#666 on #f0f0f0` = 5.74:1 (PASS)
Dosyalar: PromptCustomizationForm.vue (2 yer), PromptLibraryUI.vue (1 yer)

### 3c. Custom Confirm Dialog (restaurant95 pattern)
`window.confirm()` kullanan 3 yer:
- `PromptLibraryUI.vue:434` - prompt silme
- `VariationHistoryComparison.vue:600` - variation silme
- `VariationHistoryComparison.vue:614` - gecmis temizleme

ConfirmDialog ozellikleri:
- `role="alertdialog"`, `aria-modal="true"`, focus trap
- Escape ile kapatma, Cancel auto-focus
- Destructive mod (kirmizi confirm butonu)
- `<Transition>` ile giris/cikis animasyonu

### 3d. Global Focus-Visible
design-tokens.css'e ekleme:
```css
:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
```

### 3e. ComparisonLayout Responsive
`grid-template-columns: repeat(3, 1fr)` -> breakpoints ekleme:
- `<=1024px`: 2 kolon
- `<=640px`: 1 kolon

### Storybook Stories
- `ConfirmDialog.stories.ts` - Default, Destructive, Long Message variants

### Degisecek Dosyalar (5+1)
PromptLibraryUI, VariationHistory, ComparisonLayout, ModelOutputPanel, PromptCustomizationForm + yeni ConfirmDialog

### Dogrulama
```bash
npx playwright test --reporter=list  # Mevcut testler pass olmali
pnpm storybook                       # ConfirmDialog story'si gorunmeli
```

---

## Phase 4: Loading States ve Animasyonlar

**Hedef:** Skeleton loader, modal animasyonlari, toast mobile fix.

**Referans:** Restaurant95 UI'da `molecules/Skeleton.vue` + `Skeleton.stories.ts` mevcut.

### Yeni Dosya
- `src/components/SkeletonLoader.vue` - restaurant95 Skeleton referansiyla

### Skeleton Variants
- `card` - Prompt kartlari icin (image + 3 shimmer line)
- `row` - Timeline satirlari icin (thumb + 2 shimmer line)

### Degisiklikler (3 dosya)
| Dosya | Degisiklik |
|-------|-----------|
| `PromptLibraryUI.vue` | `isLoading` sirasinda 6 skeleton card |
| `VariationHistoryComparison.vue` | `isLoading` sirasinda 4 skeleton row |
| `App.vue` | output-loading skeleton iyilestirmesi |

### Modal Animasyonlari
PromptLibraryUI ve VariationHistory modal overlay'larina Vue `<Transition>` ekleme:
- Giris: opacity 0->1 + scale(0.95)->1, `var(--transition-base)`
- Cikis: opacity 1->0, `var(--transition-fast)`

### Toast Mobile Fix
```css
@media (max-width: 480px) {
  .toast { left: var(--space-4); right: var(--space-4); bottom: var(--space-4); }
}
```

### Storybook Stories
- `SkeletonLoader.stories.ts` - Card, Row, Grid variants

### Dogrulama
```bash
npx playwright test --reporter=list  # Pass olmali
pnpm storybook                       # Skeleton story'leri gorunmeli
```

---

## Phase 5: Test Coverage

**Hedef:** Kritik test eksikliklerini kapatmak.

### Yeni Dosyalar (4)
| Dosya | Test Sayisi | Oncelik |
|-------|------------|---------|
| `src/utils/__tests__/sanitizer.spec.ts` | ~20 | CRITICAL (XSS) |
| `src/services/__tests__/api.spec.ts` | ~12 | HIGH |
| `src/components/__tests__/PromptLibraryUI.spec.ts` | ~15 | MEDIUM |
| `src/components/__tests__/VariationHistoryComparison.spec.ts` | ~15 | MEDIUM |

### sanitizer.spec.ts (en yuksek oncelik)
- `sanitizeHtml()`: script tag escape, null input, plain text koruma
- `sanitizeText()`: &, <, >, ", ' escape
- `isSafeUrl()`: https kabul, javascript: reddet
- `validateFormData()`: required, minLength, maxLength, enum, pattern
- `RateLimiter`: limit icinde izin, limit asilinca engel, window reset

### Dogrulama
```bash
npm run test           # Vitest - tum unit testler
npm run test:coverage  # Coverage raporu
npx playwright test    # E2E hala 29/29
```

---

## Faz Sirasi ve Bagimliliklar

```
Phase 0: Storybook Setup  ←── ILK (gorsel degisiklikleri izleme altyapisi)
    |
Phase 1: Design System    ←── BLOCKING (diger fazlar tokenlari kullanir)
    |
    ├── Phase 2: Mock Data      (bagimsiz)
    ├── Phase 3: UX Fixes       (bagimsiz)
    |
    v
Phase 4: Loading States    (Phase 1 tokenlari + Phase 2 verileri)
    |
    v
Phase 5: Test Coverage     (son - tum fazlari dogrular)
```

## Toplam Degisiklik Ozeti

| Faz | Yeni Dosya | Degisecek Dosya | Risk |
|-----|-----------|----------------|------|
| 0: Storybook | 8 (.storybook + stories) | 1 (package.json) | Dusuk |
| 1: Design System | 1 (design-tokens.css) | 7 (tum Vue + main.ts) | Dusuk |
| 2: Mock Data | 1 (mock-data.ts) | 3 (App, Library, History) | Dusuk |
| 3: UX Fixes | 2 (ConfirmDialog + story) | 5 (componentler) | Orta |
| 4: Loading States | 2 (SkeletonLoader + story) | 3 (App, Library, History) | Orta |
| 5: Test Coverage | 4 (test dosyalari) | 0 | Sifir |
| **TOPLAM** | **18 yeni** | **7 tekil dosya** | |

## Genesis Altyapi Yeniden Kullanim

| Altyapi | Kullanim |
|---------|---------|
| `@genesis/storybook-config` | Phase 0 - Storybook main.ts + preview.ts |
| `@genesis/visual-regression` | Phase 0 - Argos CI entegrasyonu (gelecek) |
| `cigkoftecibey design-tokens.css` | Phase 1 - Token adlandirma pattern'i |
| `restaurant95 ConfirmDialog` | Phase 3 - Dialog component referansi |
| `restaurant95 Skeleton` | Phase 4 - Skeleton component referansi |
| `restaurant95 stories/*` | Phase 0-4 - Story yazim pattern'i |

## Kritik Dosyalar

- `src/App.vue` (519 satir) - Phase 0, 1, 2, 4
- `src/components/PromptLibraryUI.vue` (1146 satir) - Phase 0, 1, 2, 3, 4
- `src/components/VariationHistoryComparison.vue` (1519 satir) - Phase 0, 1, 2, 3, 4
- `src/utils/sanitizer.js` (281 satir) - Phase 5
- `e2e/coloring-book.spec.ts` (283 satir) - Her fazda dogrulama referansi
- `packages/storybook-config/main.js` (291 satir) - Phase 0 referans
- `projects/cigkoftecibey-webapp/.../design-tokens.css` (130 satir) - Phase 1 referans
- `projects/restaurant95-ai/packages/ui/src/index.ts` (45 satir) - Phase 3-4 referans
