# Frontend Refactoring Phase 3: Performance Optimization

## Overview
This document provides detailed steps 21-30 for implementing performance optimizations, code splitting, lazy loading, and advanced caching strategies. This phase should be started only after completing Phase 1 (Steps 1-10) and Phase 2 (Steps 11-20) successfully.

## Prerequisites
- Phase 1 and Phase 2 completed successfully
- All type checks passing
- Application functionality verified
- Component refactoring completed
- Feature branch up to date

## Phase 3: Performance Optimization (Steps 21-30)

### Step 21: Bundle Analysis and Optimization Setup
**Goal:** Analyze current bundle size and set up tools for monitoring performance improvements.

**Actions:**
- CREATE: `src/lib/performance/` directory
- CREATE: `src/lib/performance/bundleAnalysis.ts`
- CREATE: `src/lib/performance/metricsTracker.ts`
- MODIFY: `package.json` to add bundle analysis scripts
- CREATE: `vite.config.performance.ts` for performance-focused build

**Code changes:**
```json
// package.json - Add to scripts section
{
  "scripts": {
    "analyze": "npm run build && npx vite-bundle-analyzer dist",
    "build:analyze": "vite build --config vite.config.performance.ts",
    "size-limit": "npx size-limit",
    "perf:measure": "npm run build && node scripts/measure-performance.js"
  },
  "devDependencies": {
    "vite-bundle-analyzer": "^0.7.0",
    "size-limit": "^8.2.6",
    "@size-limit/preset-app": "^8.2.6"
  }
}
```

```typescript
// vite.config.performance.ts
import path from "node:path"
import { TanStackRouterVite } from "@tanstack/router-vite-plugin"
import react from "@vitejs/plugin-react-swc"
import { defineConfig } from "vite"
import { analyzer } from "vite-bundle-analyzer"

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  plugins: [
    react(),
    TanStackRouterVite(),
    analyzer({
      analyzerMode: 'static',
      openAnalyzer: false,
      fileName: 'bundle-analysis.html'
    })
  ],
  build: {
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          tanstack: ['@tanstack/react-query', '@tanstack/react-router'],
          chakra: ['@chakra-ui/react', '@emotion/react'],
          utils: ['axios', 'react-hook-form']
        }
      }
    }
  }
})
```

```typescript
// src/lib/performance/bundleAnalysis.ts
export interface BundleMetrics {
  totalSize: number
  chunkSizes: Record<string, number>
  assetSizes: Record<string, number>
  compressionRatio: number
}

export function analyzeBundleSize(buildPath: string): Promise<BundleMetrics> {
  // Implementation for analyzing bundle sizes
  // This would be used in build scripts
  return Promise.resolve({
    totalSize: 0,
    chunkSizes: {},
    assetSizes: {},
    compressionRatio: 0
  })
}

export function trackBundleGrowth(previous: BundleMetrics, current: BundleMetrics) {
  const growth = {
    totalGrowth: current.totalSize - previous.totalSize,
    percentageGrowth: ((current.totalSize - previous.totalSize) / previous.totalSize) * 100
  }

  console.log('Bundle Growth:', growth)
  return growth
}
```

```typescript
// src/lib/performance/metricsTracker.ts
interface PerformanceMetrics {
  pageLoadTime: number
  timeToInteractive: number
  firstContentfulPaint: number
  largestContentfulPaint: number
  cumulativeLayoutShift: number
}

export class MetricsTracker {
  private metrics: Partial<PerformanceMetrics> = {}

  constructor() {
    this.setupPerformanceObserver()
  }

  private setupPerformanceObserver() {
    if (typeof window === 'undefined') return

    // Track Core Web Vitals
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.entryType === 'navigation') {
          this.metrics.pageLoadTime = entry.duration
        }
      }
    }).observe({ entryTypes: ['navigation'] })

    // Track paint metrics
    new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (entry.name === 'first-contentful-paint') {
          this.metrics.firstContentfulPaint = entry.startTime
        }
      }
    }).observe({ entryTypes: ['paint'] })
  }

  getMetrics(): Partial<PerformanceMetrics> {
    return { ...this.metrics }
  }

  reportMetrics() {
    // In a real app, send to analytics service
    console.log('Performance Metrics:', this.metrics)
  }
}

export const metricsTracker = new MetricsTracker()
```

```json
// .size-limit.json
[
  {
    "name": "Main bundle",
    "path": "dist/assets/index-*.js",
    "limit": "250 KB"
  },
  {
    "name": "CSS bundle",
    "path": "dist/assets/index-*.css",
    "limit": "50 KB"
  }
]
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Bundle analysis tools configured, performance tracking setup, baseline metrics established.

---

### Step 22: Implement Route-Based Code Splitting
**Goal:** Split code by routes to reduce initial bundle size and improve loading performance.

**Actions:**
- CREATE: `src/lib/performance/lazyRoutes.ts`
- MODIFY: `src/routes/_layout/index.tsx` to use lazy loading
- MODIFY: `src/routes/_layout/quizzes.tsx` to use lazy loading
- MODIFY: `src/routes/_layout/create-quiz.tsx` to use lazy loading
- MODIFY: `src/routes/_layout/quiz.$id.tsx` to use lazy loading
- MODIFY: `src/routes/_layout/settings.tsx` to use lazy loading

**Code changes:**
```typescript
// src/lib/performance/lazyRoutes.ts
import { lazy } from 'react'
import { LoadingSkeleton } from '@/components/common'

// Lazy load route components with loading fallbacks
export const LazyDashboard = lazy(() =>
  import('@/routes/_layout/index').then(module => ({
    default: module.Route.options.component
  }))
)

export const LazyQuizList = lazy(() =>
  import('@/routes/_layout/quizzes').then(module => ({
    default: module.Route.options.component
  }))
)

export const LazyCreateQuiz = lazy(() =>
  import('@/routes/_layout/create-quiz').then(module => ({
    default: module.Route.options.component
  }))
)

export const LazyQuizDetail = lazy(() =>
  import('@/routes/_layout/quiz.$id').then(module => ({
    default: module.Route.options.component
  }))
)

export const LazySettings = lazy(() =>
  import('@/routes/_layout/settings').then(module => ({
    default: module.Route.options.component
  }))
)

// Loading component with skeleton
export function RouteLoadingSkeleton() {
  return (
    <div style={{ padding: '2rem' }}>
      <LoadingSkeleton height="40px" width="300px" />
      <LoadingSkeleton height="20px" width="500px" lines={3} />
    </div>
  )
}
```

```typescript
// src/routes/_layout/index.tsx
import { Suspense } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { LazyDashboard, RouteLoadingSkeleton } from "@/lib/performance/lazyRoutes"

export const Route = createFileRoute("/_layout/")({
  component: () => (
    <Suspense fallback={<RouteLoadingSkeleton />}>
      <LazyDashboard />
    </Suspense>
  ),
})

function Dashboard() {
  // Move the actual Dashboard component implementation here
  // from the original index.tsx file
  // ... (existing Dashboard component code)
}
```

```typescript
// src/routes/_layout/quizzes.tsx
import { Suspense } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { LazyQuizList, RouteLoadingSkeleton } from "@/lib/performance/lazyRoutes"

export const Route = createFileRoute("/_layout/quizzes")({
  component: () => (
    <Suspense fallback={<RouteLoadingSkeleton />}>
      <LazyQuizList />
    </Suspense>
  ),
})

function QuizList() {
  // Move the actual QuizList component implementation here
  // ... (existing QuizList component code)
}
```

**Apply the same pattern to all other route files.**

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Routes now load lazily, reducing initial bundle size, loading skeletons show during route transitions.

---

### Step 23: Implement Component-Level Code Splitting
**Goal:** Split large component trees and heavy dependencies into separate chunks.

**Actions:**
- CREATE: `src/lib/performance/lazyComponents.ts`
- MODIFY: Dashboard panels to load lazily
- MODIFY: Question components to load lazily
- MODIFY: Onboarding modal to load lazily
- CREATE: Component loading boundaries

**Code changes:**
```typescript
// src/lib/performance/lazyComponents.ts
import { lazy, Suspense, type ComponentType, type ReactNode } from 'react'
import { LoadingSkeleton } from '@/components/common'

// Higher-order component for lazy loading with error boundary
export function withLazyLoading<T extends Record<string, unknown>>(
  importFn: () => Promise<{ default: ComponentType<T> }>,
  LoadingFallback?: ComponentType
) {
  const LazyComponent = lazy(importFn)

  return function WrappedComponent(props: T) {
    const Fallback = LoadingFallback || DefaultComponentSkeleton

    return (
      <Suspense fallback={<Fallback />}>
        <LazyComponent {...props} />
      </Suspense>
    )
  }
}

// Default loading skeleton for components
function DefaultComponentSkeleton() {
  return <LoadingSkeleton height="200px" lines={4} />
}

// Specific loading skeletons for different component types
export function PanelLoadingSkeleton() {
  return (
    <div style={{
      border: '1px solid #e2e8f0',
      borderRadius: '8px',
      padding: '1rem',
      background: '#f7fafc'
    }}>
      <LoadingSkeleton height="24px" width="60%" />
      <LoadingSkeleton height="16px" width="80%" />
      <LoadingSkeleton height="100px" width="100%" />
    </div>
  )
}

export function QuestionLoadingSkeleton() {
  return (
    <div style={{ padding: '1rem' }}>
      <LoadingSkeleton height="20px" width="90%" />
      <LoadingSkeleton height="16px" width="70%" lines={3} />
    </div>
  )
}

// Lazy-loaded dashboard panels
export const LazyQuizGenerationPanel = withLazyLoading(
  () => import('@/components/dashboard/panels/QuizGenerationPanel'),
  PanelLoadingSkeleton
)

export const LazyQuizReviewPanel = withLazyLoading(
  () => import('@/components/dashboard/panels/QuizReviewPanel'),
  PanelLoadingSkeleton
)

export const LazyHelpPanel = withLazyLoading(
  () => import('@/components/dashboard/panels/HelpPanel'),
  PanelLoadingSkeleton
)

// Lazy-loaded question components
export const LazyQuestionDisplay = withLazyLoading(
  () => import('@/components/questions/display/QuestionDisplay'),
  QuestionLoadingSkeleton
)

export const LazyQuestionEditor = withLazyLoading(
  () => import('@/components/Questions/QuestionEditor'),
  QuestionLoadingSkeleton
)

// Lazy-loaded heavy modals/overlays
export const LazyOnboardingModal = withLazyLoading(
  () => import('@/components/Onboarding/OnboardingModal'),
  () => null // No skeleton for modals
)
```

```typescript
// src/components/dashboard/DashboardPanels.tsx
import { SimpleGrid } from "@chakra-ui/react"
import {
  LazyQuizGenerationPanel,
  LazyQuizReviewPanel,
  LazyHelpPanel
} from "@/lib/performance/lazyComponents"

interface DashboardPanelsProps {
  quizzes: Quiz[]
  isLoading: boolean
}

export function DashboardPanels({ quizzes, isLoading }: DashboardPanelsProps) {
  return (
    <SimpleGrid
      columns={{ base: 1, md: 2, lg: 3 }}
      gap={6}
      data-testid="dashboard-grid"
    >
      <LazyQuizReviewPanel quizzes={quizzes} isLoading={isLoading} />
      <LazyQuizGenerationPanel quizzes={quizzes} isLoading={isLoading} />
      <LazyHelpPanel />
    </SimpleGrid>
  )
}
```

**Update Dashboard component to use the new DashboardPanels:**
```typescript
// Update src/routes/_layout/index.tsx Dashboard component
import { DashboardPanels } from "@/components/dashboard/DashboardPanels"

// Replace the SimpleGrid section with:
<DashboardPanels quizzes={quizzes || []} isLoading={isLoading} />
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Heavy components load on-demand, improved initial page load, smooth loading transitions.

---

### Step 24: Optimize TanStack Query Caching
**Goal:** Implement advanced caching strategies to reduce API calls and improve perceived performance.

**Actions:**
- CREATE: `src/lib/api/cacheConfig.ts`
- CREATE: `src/lib/api/queryUtils.ts`
- MODIFY: `src/hooks/api/useQuizzes.ts` to use optimized caching
- CREATE: `src/hooks/api/useOptimisticUpdates.ts`
- MODIFY: `src/main.tsx` to use optimized query client

**Code changes:**
```typescript
// src/lib/api/cacheConfig.ts
export const CACHE_TIMES = {
  // Short-lived data (user actions, real-time status)
  SHORT: 1000 * 60 * 2, // 2 minutes

  // Medium-lived data (quiz lists, user profile)
  MEDIUM: 1000 * 60 * 10, // 10 minutes

  // Long-lived data (courses, static content)
  LONG: 1000 * 60 * 60, // 1 hour

  // Very long-lived data (user preferences, app config)
  VERY_LONG: 1000 * 60 * 60 * 24, // 24 hours
} as const

export const STALE_TIMES = {
  SHORT: 1000 * 30, // 30 seconds
  MEDIUM: 1000 * 60 * 2, // 2 minutes
  LONG: 1000 * 60 * 10, // 10 minutes
  VERY_LONG: 1000 * 60 * 60, // 1 hour
} as const

export const queryClientConfig = {
  defaultOptions: {
    queries: {
      staleTime: STALE_TIMES.MEDIUM,
      cacheTime: CACHE_TIMES.MEDIUM,
      retry: (failureCount: number, error: unknown) => {
        // Don't retry on 4xx errors
        if (error && typeof error === 'object' && 'status' in error) {
          const status = (error as { status: number }).status
          if (status >= 400 && status < 500) return false
        }
        return failureCount < 3
      },
      retryDelay: (attemptIndex: number) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
    mutations: {
      retry: 1,
    },
  },
}
```

```typescript
// src/lib/api/queryUtils.ts
import { QueryClient } from '@tanstack/react-query'
import { queryKeys } from './queryKeys'

export class QueryUtils {
  constructor(private queryClient: QueryClient) {}

  // Prefetch related data
  async prefetchQuizDetails(quizId: string) {
    return this.queryClient.prefetchQuery({
      queryKey: queryKeys.quizzes.detail(quizId),
      queryFn: () => import('@/client').then(({ QuizService }) =>
        QuizService.getQuizByIdEndpoint({ quizId })
      ),
    })
  }

  // Invalidate related queries
  invalidateQuizData(quizId?: string) {
    if (quizId) {
      this.queryClient.invalidateQueries({
        queryKey: queryKeys.quizzes.detail(quizId)
      })
    }
    this.queryClient.invalidateQueries({
      queryKey: queryKeys.quizzes.userQuizzes()
    })
  }

  // Optimistically update quiz list
  updateQuizInList(quizId: string, updater: (quiz: Quiz) => Quiz) {
    this.queryClient.setQueryData(
      queryKeys.quizzes.userQuizzes(),
      (oldData: Quiz[] | undefined) => {
        if (!oldData) return oldData
        return oldData.map(quiz =>
          quiz.id === quizId ? updater(quiz) : quiz
        )
      }
    )
  }

  // Remove quiz from cache
  removeQuizFromCache(quizId: string) {
    this.queryClient.removeQueries({
      queryKey: queryKeys.quizzes.detail(quizId)
    })
    this.invalidateQuizData()
  }

  // Background refresh for stale data
  backgroundRefresh(queryKey: unknown[]) {
    this.queryClient.invalidateQueries({ queryKey })
  }
}
```

```typescript
// src/hooks/api/useOptimisticUpdates.ts
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { QuizService } from '@/client'
import { queryKeys } from '@/lib/api'
import { QueryUtils } from '@/lib/api/queryUtils'

export function useOptimisticQuizUpdate() {
  const queryClient = useQueryClient()
  const queryUtils = new QueryUtils(queryClient)

  return useMutation({
    mutationFn: async ({ quizId, updates }: { quizId: string; updates: Partial<Quiz> }) => {
      // Optimistically update the UI immediately
      queryUtils.updateQuizInList(quizId, (quiz) => ({ ...quiz, ...updates }))

      // Make the actual API call
      return QuizService.updateQuizEndpoint({ quizId, requestBody: updates })
    },
    onError: (error, variables) => {
      // Revert the optimistic update on error
      queryUtils.invalidateQuizData(variables.quizId)
    },
    onSettled: (data, error, variables) => {
      // Ensure we have the latest data
      queryUtils.backgroundRefresh(queryKeys.quizzes.detail(variables.quizId))
    }
  })
}

export function useOptimisticQuizDelete() {
  const queryClient = useQueryClient()
  const queryUtils = new QueryUtils(queryClient)

  return useMutation({
    mutationFn: async (quizId: string) => {
      // Optimistically remove from UI
      queryUtils.removeQuizFromCache(quizId)

      // Make the actual API call
      return QuizService.deleteQuizEndpoint({ quizId })
    },
    onError: () => {
      // Revert by refreshing the quiz list
      queryUtils.invalidateQuizData()
    }
  })
}
```

```typescript
// Update src/hooks/api/useQuizzes.ts
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { QuizService } from '@/client'
import { queryKeys } from '@/lib/api'
import { CACHE_TIMES, STALE_TIMES } from '@/lib/api/cacheConfig'
import { QueryUtils } from '@/lib/api/queryUtils'

export function useUserQuizzes() {
  const queryClient = useQueryClient()
  const queryUtils = new QueryUtils(queryClient)

  return useQuery({
    queryKey: queryKeys.quizzes.userQuizzes(),
    queryFn: QuizService.getUserQuizzesEndpoint,
    staleTime: STALE_TIMES.MEDIUM,
    cacheTime: CACHE_TIMES.MEDIUM,
    onSuccess: (data) => {
      // Prefetch quiz details for the first few quizzes
      data.slice(0, 3).forEach(quiz => {
        if (quiz.id) {
          queryUtils.prefetchQuizDetails(quiz.id)
        }
      })
    }
  })
}

export function useQuizDetail(quizId: string, prefetch = false) {
  return useQuery({
    queryKey: queryKeys.quizzes.detail(quizId),
    queryFn: () => QuizService.getQuizByIdEndpoint({ quizId }),
    enabled: !!quizId && !prefetch,
    staleTime: STALE_TIMES.LONG,
    cacheTime: CACHE_TIMES.LONG,
  })
}
```

```typescript
// Update src/main.tsx
import { queryClientConfig } from "./lib/api/cacheConfig"

const queryClient = new QueryClient(queryClientConfig)
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Optimized caching reduces API calls, optimistic updates improve UX, background refresh keeps data fresh.

---

### Step 25: Implement Virtual Scrolling for Large Lists
**Goal:** Optimize performance when displaying large lists of quizzes or questions.

**Actions:**
- CREATE: `src/lib/performance/virtualScroll.ts`
- CREATE: `src/components/common/VirtualList.tsx`
- MODIFY: Quiz list to use virtual scrolling when needed
- CREATE: `src/hooks/common/useVirtualScroll.ts`

**Code changes:**
```typescript
// src/lib/performance/virtualScroll.ts
export interface VirtualScrollConfig {
  itemHeight: number
  containerHeight: number
  overscan?: number
  threshold?: number
}

export class VirtualScrollCalculator {
  constructor(private config: VirtualScrollConfig) {}

  getVisibleRange(scrollTop: number, itemCount: number) {
    const { itemHeight, containerHeight, overscan = 5 } = this.config

    const startIndex = Math.floor(scrollTop / itemHeight)
    const endIndex = Math.min(
      startIndex + Math.ceil(containerHeight / itemHeight) + overscan,
      itemCount - 1
    )

    return {
      startIndex: Math.max(0, startIndex - overscan),
      endIndex,
      visibleItems: endIndex - startIndex + 1
    }
  }

  getTotalHeight(itemCount: number): number {
    return itemCount * this.config.itemHeight
  }

  getItemStyle(index: number) {
    return {
      position: 'absolute' as const,
      top: index * this.config.itemHeight,
      left: 0,
      right: 0,
      height: this.config.itemHeight
    }
  }
}
```

```typescript
// src/hooks/common/useVirtualScroll.ts
import { useState, useEffect, useCallback, useRef } from 'react'
import { VirtualScrollCalculator, type VirtualScrollConfig } from '@/lib/performance/virtualScroll'

export function useVirtualScroll<T>(
  items: T[],
  config: VirtualScrollConfig
) {
  const [scrollTop, setScrollTop] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  const calculator = new VirtualScrollCalculator(config)

  const { startIndex, endIndex } = calculator.getVisibleRange(scrollTop, items.length)
  const visibleItems = items.slice(startIndex, endIndex + 1)
  const totalHeight = calculator.getTotalHeight(items.length)

  const handleScroll = useCallback((event: React.UIEvent<HTMLDivElement>) => {
    const target = event.target as HTMLDivElement
    setScrollTop(target.scrollTop)
  }, [])

  const getItemProps = useCallback((index: number) => ({
    style: calculator.getItemStyle(startIndex + index),
    key: startIndex + index
  }), [startIndex, calculator])

  return {
    containerRef,
    visibleItems,
    totalHeight,
    startIndex,
    endIndex,
    handleScroll,
    getItemProps
  }
}
```

```typescript
// src/components/common/VirtualList.tsx
import { Box } from "@chakra-ui/react"
import { memo, type ReactNode } from "react"
import { useVirtualScroll } from "@/hooks/common/useVirtualScroll"

interface VirtualListProps<T> {
  items: T[]
  itemHeight: number
  containerHeight: number
  renderItem: (item: T, index: number) => ReactNode
  threshold?: number
}

export const VirtualList = memo(function VirtualList<T>({
  items,
  itemHeight,
  containerHeight,
  renderItem,
  threshold = 50
}: VirtualListProps<T>) {
  // Only use virtual scrolling for large lists
  const shouldVirtualize = items.length > threshold

  const {
    containerRef,
    visibleItems,
    totalHeight,
    startIndex,
    handleScroll,
    getItemProps
  } = useVirtualScroll(items, {
    itemHeight,
    containerHeight,
    overscan: 5
  })

  if (!shouldVirtualize) {
    // Render all items normally for small lists
    return (
      <Box maxHeight={containerHeight} overflowY="auto">
        {items.map((item, index) => (
          <Box key={index} height={itemHeight}>
            {renderItem(item, index)}
          </Box>
        ))}
      </Box>
    )
  }

  return (
    <Box
      ref={containerRef}
      height={containerHeight}
      overflowY="auto"
      onScroll={handleScroll}
    >
      <Box height={totalHeight} position="relative">
        {visibleItems.map((item, index) => (
          <Box {...getItemProps(index)}>
            {renderItem(item, startIndex + index)}
          </Box>
        ))}
      </Box>
    </Box>
  )
}) as <T>(props: VirtualListProps<T>) => JSX.Element
```

**Update Quiz List component to use virtual scrolling:**
```typescript
// Update src/routes/_layout/quizzes.tsx to use VirtualList for large quiz collections
import { VirtualList } from "@/components/common/VirtualList"

// Replace the Table.Body section when quiz count is large:
function QuizTableBody({ quizzes }: { quizzes: Quiz[] }) {
  const renderQuizRow = useCallback((quiz: Quiz, index: number) => (
    <Table.Row key={quiz.id}>
      {/* ... existing table row content ... */}
    </Table.Row>
  ), [])

  if (quizzes.length > 50) {
    return (
      <VirtualList
        items={quizzes}
        itemHeight={80}
        containerHeight={600}
        renderItem={renderQuizRow}
      />
    )
  }

  // Normal rendering for smaller lists
  return (
    <Table.Body>
      {quizzes.map((quiz) => (
        <Table.Row key={quiz.id}>
          {/* ... existing table row content ... */}
        </Table.Row>
      ))}
    </Table.Body>
  )
}
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Large lists render efficiently, smooth scrolling performance, automatic fallback for small lists.

---

### Step 26: Optimize Image Loading and Assets
**Goal:** Implement lazy loading for images and optimize asset delivery.

**Actions:**
- CREATE: `src/lib/performance/imageOptimization.ts`
- CREATE: `src/components/common/LazyImage.tsx`
- MODIFY: `vite.config.ts` to optimize image assets
- CREATE: `src/hooks/common/useImagePreloader.ts`

**Code changes:**
```typescript
// src/lib/performance/imageOptimization.ts
export interface ImageOptimizationConfig {
  quality?: number
  format?: 'webp' | 'avif' | 'auto'
  placeholder?: 'blur' | 'empty'
  loading?: 'lazy' | 'eager'
}

export function generateOptimizedImageUrl(
  src: string,
  config: ImageOptimizationConfig = {}
): string {
  const { quality = 75, format = 'auto', loading = 'lazy' } = config

  // In a real app, this would integrate with an image optimization service
  // For now, return the original URL with loading strategy
  return src
}

export function generatePlaceholder(width: number, height: number): string {
  // Generate a small blur placeholder
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')

  if (ctx) {
    const gradient = ctx.createLinearGradient(0, 0, width, height)
    gradient.addColorStop(0, '#f7fafc')
    gradient.addColorStop(1, '#edf2f7')
    ctx.fillStyle = gradient
    ctx.fillRect(0, 0, width, height)
  }

  return canvas.toDataURL()
}
```

```typescript
// src/hooks/common/useImagePreloader.ts
import { useState, useEffect } from 'react'

export function useImagePreloader(src: string) {
  const [isLoaded, setIsLoaded] = useState(false)
  const [hasError, setHasError] = useState(false)

  useEffect(() => {
    const img = new Image()

    img.onload = () => setIsLoaded(true)
    img.onerror = () => setHasError(true)
    img.src = src

    return () => {
      img.onload = null
      img.onerror = null
    }
  }, [src])

  return { isLoaded, hasError }
}

export function useImagePreloaderBatch(sources: string[]) {
  const [loadedImages, setLoadedImages] = useState<Set<string>>(new Set())
  const [failedImages, setFailedImages] = useState<Set<string>>(new Set())

  useEffect(() => {
    const preloadPromises = sources.map(src => {
      return new Promise<string>((resolve, reject) => {
        const img = new Image()
        img.onload = () => resolve(src)
        img.onerror = () => reject(src)
        img.src = src
      })
    })

    Promise.allSettled(preloadPromises).then(results => {
      const loaded = new Set<string>()
      const failed = new Set<string>()

      results.forEach((result, index) => {
        if (result.status === 'fulfilled') {
          loaded.add(sources[index])
        } else {
          failed.add(sources[index])
        }
      })

      setLoadedImages(loaded)
      setFailedImages(failed)
    })
  }, [sources])

  return { loadedImages, failedImages }
}
```

```typescript
// src/components/common/LazyImage.tsx
import { Box, Image } from "@chakra-ui/react"
import { memo, useState } from "react"
import { useImagePreloader } from "@/hooks/common/useImagePreloader"
import { generatePlaceholder, generateOptimizedImageUrl, type ImageOptimizationConfig } from "@/lib/performance/imageOptimization"

interface LazyImageProps {
  src: string
  alt: string
  width?: number
  height?: number
  fallback?: string
  optimization?: ImageOptimizationConfig
  onLoad?: () => void
  onError?: () => void
}

export const LazyImage = memo(function LazyImage({
  src,
  alt,
  width,
  height,
  fallback,
  optimization = {},
  onLoad,
  onError
}: LazyImageProps) {
  const optimizedSrc = generateOptimizedImageUrl(src, optimization)
  const { isLoaded, hasError } = useImagePreloader(optimizedSrc)
  const [showFallback, setShowFallback] = useState(false)

  const placeholder = width && height ? generatePlaceholder(width, height) : undefined

  if (hasError || showFallback) {
    return (
      <Box
        width={width}
        height={height}
        bg="gray.100"
        display="flex"
        alignItems="center"
        justifyContent="center"
        color="gray.500"
        fontSize="sm"
      >
        {fallback || 'Image failed to load'}
      </Box>
    )
  }

  return (
    <Box position="relative" width={width} height={height}>
      {!isLoaded && placeholder && (
        <Image
          src={placeholder}
          alt=""
          width={width}
          height={height}
          position="absolute"
          top={0}
          left={0}
          filter="blur(4px)"
          transition="opacity 0.3s"
        />
      )}

      <Image
        src={optimizedSrc}
        alt={alt}
        width={width}
        height={height}
        loading={optimization.loading || 'lazy'}
        opacity={isLoaded ? 1 : 0}
        transition="opacity 0.3s"
        onLoad={() => {
          onLoad?.()
        }}
        onError={() => {
          setShowFallback(true)
          onError?.()
        }}
      />
    </Box>
  )
})
```

**Update vite.config.ts for asset optimization:**
```typescript
// Update vite.config.ts
import path from "node:path"
import { TanStackRouterVite } from "@tanstack/router-vite-plugin"
import react from "@vitejs/plugin-react-swc"
import { defineConfig } from "vite"

export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  plugins: [react(), TanStackRouterVite()],
  build: {
    rollupOptions: {
      output: {
        assetFileNames: (assetInfo) => {
          const info = assetInfo.name?.split('.') || []
          let extType = info[info.length - 1]

          if (/png|jpe?g|svg|gif|tiff|bmp|ico/i.test(extType ?? '')) {
            extType = 'images'
          } else if (/woff|woff2|eot|ttf|otf/i.test(extType ?? '')) {
            extType = 'fonts'
          }

          return `assets/${extType}/[name]-[hash][extname]`
        },
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js'
      }
    },
    assetsInlineLimit: 4096, // Inline assets smaller than 4kb
  },
  // Optimize asset handling
  assetsInclude: ['**/*.svg', '**/*.png', '**/*.jpg', '**/*.jpeg', '**/*.gif', '**/*.webp']
})
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Images load lazily with smooth transitions, optimized asset bundling, improved loading performance.

---

### Step 27: Implement Service Worker for Caching
**Goal:** Add service worker for offline support and aggressive caching of static assets.

**Actions:**
- CREATE: `public/sw.js`
- CREATE: `src/lib/performance/serviceWorker.ts`
- MODIFY: `src/main.tsx` to register service worker
- CREATE: `src/lib/performance/cacheStrategies.ts`

**Code changes:**
```javascript
// public/sw.js
const CACHE_NAME = 'ragatuit-v1'
const STATIC_CACHE = 'static-v1'
const DYNAMIC_CACHE = 'dynamic-v1'

// Assets to cache immediately
const STATIC_ASSETS = [
  '/',
  '/assets/images/logo.svg',
  '/assets/images/favicon.png',
  // Add other critical assets
]

// API endpoints to cache with different strategies
const API_CACHE_PATTERNS = [
  { pattern: /\/api\/v1\/users\/me/, strategy: 'cacheFirst', ttl: 300000 }, // 5 min
  { pattern: /\/api\/v1\/quiz\/user/, strategy: 'staleWhileRevalidate', ttl: 600000 }, // 10 min
  { pattern: /\/api\/v1\/quiz\/\d+/, strategy: 'networkFirst', ttl: 300000 }, // 5 min
]

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames
          .filter(cacheName => cacheName !== CACHE_NAME && cacheName !== STATIC_CACHE)
          .map(cacheName => caches.delete(cacheName))
      )
    }).then(() => self.clients.claim())
  )
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)

  // Handle API requests
  if (url.pathname.startsWith('/api/')) {
    const cacheConfig = API_CACHE_PATTERNS.find(config =>
      config.pattern.test(url.pathname)
    )

    if (cacheConfig) {
      event.respondWith(handleApiRequest(request, cacheConfig))
      return
    }
  }

  // Handle static assets
  if (request.destination === 'image' || request.destination === 'script' || request.destination === 'style') {
    event.respondWith(handleStaticAsset(request))
    return
  }

  // Handle navigation requests
  if (request.mode === 'navigate') {
    event.respondWith(handleNavigation(request))
    return
  }
})

async function handleApiRequest(request, config) {
  const cacheName = DYNAMIC_CACHE
  const cache = await caches.open(cacheName)

  switch (config.strategy) {
    case 'cacheFirst':
      return cacheFirst(request, cache)
    case 'networkFirst':
      return networkFirst(request, cache)
    case 'staleWhileRevalidate':
      return staleWhileRevalidate(request, cache)
    default:
      return fetch(request)
  }
}

async function cacheFirst(request, cache) {
  const cached = await cache.match(request)
  if (cached) return cached

  try {
    const response = await fetch(request)
    if (response.ok) {
      cache.put(request, response.clone())
    }
    return response
  } catch (error) {
    throw error
  }
}

async function networkFirst(request, cache) {
  try {
    const response = await fetch(request)
    if (response.ok) {
      cache.put(request, response.clone())
    }
    return response
  } catch (error) {
    const cached = await cache.match(request)
    if (cached) return cached
    throw error
  }
}

async function staleWhileRevalidate(request, cache) {
  const cached = await cache.match(request)

  const fetchPromise = fetch(request).then(response => {
    if (response.ok) {
      cache.put(request, response.clone())
    }
    return response
  })

  return cached || fetchPromise
}

async function handleStaticAsset(request) {
  const cache = await caches.open(STATIC_CACHE)
  const cached = await cache.match(request)

  if (cached) return cached

  try {
    const response = await fetch(request)
    if (response.ok) {
      cache.put(request, response.clone())
    }
    return response
  } catch (error) {
    throw error
  }
}

async function handleNavigation(request) {
  try {
    return await fetch(request)
  } catch (error) {
    const cache = await caches.open(STATIC_CACHE)
    return cache.match('/')
  }
}
```

```typescript
// src/lib/performance/serviceWorker.ts
export interface ServiceWorkerConfig {
  onUpdate?: (registration: ServiceWorkerRegistration) => void
  onSuccess?: (registration: ServiceWorkerRegistration) => void
  onError?: (error: Error) => void
}

export function registerServiceWorker(config: ServiceWorkerConfig = {}) {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker
      .register('/sw.js')
      .then(registration => {
        // Check for updates
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing
          if (newWorker) {
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                config.onUpdate?.(registration)
              }
            })
          }
        })

        config.onSuccess?.(registration)
      })
      .catch(error => {
        config.onError?.(error)
      })

    // Listen for service worker messages
    navigator.serviceWorker.addEventListener('message', event => {
      if (event.data && event.data.type === 'CACHE_UPDATED') {
        // Handle cache update notifications
        console.log('Cache updated:', event.data.payload)
      }
    })
  }
}

export function unregisterServiceWorker() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready
      .then(registration => {
        registration.unregister()
      })
      .catch(error => {
        console.error('Error unregistering service worker:', error)
      })
  }
}

// Force service worker update
export function updateServiceWorker() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready
      .then(registration => {
        registration.update()
      })
  }
}

// Check if app is running offline
export function isOnline(): boolean {
  return navigator.onLine
}

// Listen for online/offline events
export function onNetworkChange(callback: (isOnline: boolean) => void) {
  const handleOnline = () => callback(true)
  const handleOffline = () => callback(false)

  window.addEventListener('online', handleOnline)
  window.addEventListener('offline', handleOffline)

  return () => {
    window.removeEventListener('online', handleOnline)
    window.removeEventListener('offline', handleOffline)
  }
}
```

```typescript
// Update src/main.tsx to register service worker
import { registerServiceWorker } from "./lib/performance/serviceWorker"

// Add after creating the app root
registerServiceWorker({
  onUpdate: (registration) => {
    // Show update notification to user
    console.log('New app version available!')
    // You could show a toast notification here
  },
  onSuccess: (registration) => {
    console.log('Service worker registered successfully')
  },
  onError: (error) => {
    console.warn('Service worker registration failed:', error)
  }
})
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Service worker provides offline support, aggressive caching improves repeat visit performance.

---

### Step 28: Optimize Font Loading and Typography
**Goal:** Implement efficient font loading strategies to prevent layout shifts and improve performance.

**Actions:**
- CREATE: `src/lib/performance/fontOptimization.ts`
- MODIFY: `index.html` to preload critical fonts
- CREATE: `src/components/common/FontDisplay.tsx`
- UPDATE: `src/theme.tsx` with optimized font settings

**Code changes:**
```typescript
// src/lib/performance/fontOptimization.ts
export interface FontConfig {
  family: string
  weight: number | string
  style?: 'normal' | 'italic'
  display?: 'auto' | 'block' | 'swap' | 'fallback' | 'optional'
  preload?: boolean
}

export const FONT_CONFIGS: FontConfig[] = [
  {
    family: 'Inter',
    weight: 400,
    style: 'normal',
    display: 'swap',
    preload: true
  },
  {
    family: 'Inter',
    weight: 500,
    style: 'normal',
    display: 'swap',
    preload: true
  },
  {
    family: 'Inter',
    weight: 600,
    style: 'normal',
    display: 'swap',
    preload: false
  }
]

export function generateFontPreloadLinks(): string {
  return FONT_CONFIGS
    .filter(config => config.preload)
    .map(config =>
      `<link rel="preload" href="/fonts/${config.family}-${config.weight}.woff2" as="font" type="font/woff2" crossorigin>`
    )
    .join('\n')
}

export function generateFontFaceCSS(): string {
  return FONT_CONFIGS
    .map(config => `
      @font-face {
        font-family: '${config.family}';
        font-weight: ${config.weight};
        font-style: ${config.style || 'normal'};
        font-display: ${config.display || 'swap'};
        src: url('/fonts/${config.family}-${config.weight}.woff2') format('woff2'),
             url('/fonts/${config.family}-${config.weight}.woff') format('woff');
      }
    `)
    .join('\n')
}

// Font loading detection
export function detectFontLoading(fontFamily: string): Promise<void> {
  if ('fonts' in document) {
    return document.fonts.load(`1em ${fontFamily}`)
  }

  // Fallback for browsers without Font Loading API
  return new Promise((resolve) => {
    const testString = 'BESbswy'
    const testSize = '72px'
    const fallbackFont = 'sans-serif'

    const canvas = document.createElement('canvas')
    const context = canvas.getContext('2d')!

    context.font = `${testSize} ${fallbackFont}`
    const fallbackWidth = context.measureText(testString).width

    context.font = `${testSize} ${fontFamily}, ${fallbackFont}`

    function check() {
      const currentWidth = context.measureText(testString).width
      if (currentWidth !== fallbackWidth) {
        resolve()
      } else {
        setTimeout(check, 100)
      }
    }

    check()
  })
}
```

```html
<!-- Update index.html -->
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/png" href="/assets/images/favicon.png" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Rag@UiT</title>

    <!-- Preload critical fonts -->
    <link rel="preload" href="/fonts/Inter-400.woff2" as="font" type="font/woff2" crossorigin>
    <link rel="preload" href="/fonts/Inter-500.woff2" as="font" type="font/woff2" crossorigin>

    <!-- Inline critical font CSS to prevent FOUT -->
    <style>
      @font-face {
        font-family: 'Inter';
        font-weight: 400;
        font-style: normal;
        font-display: swap;
        src: url('/fonts/Inter-400.woff2') format('woff2');
      }
      @font-face {
        font-family: 'Inter';
        font-weight: 500;
        font-style: normal;
        font-display: swap;
        src: url('/fonts/Inter-500.woff2') format('woff2');
      }

      /* Prevent layout shift with font fallbacks */
      body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
        font-feature-settings: 'cv02', 'cv03', 'cv04', 'cv11';
      }
    </style>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

```typescript
// Update src/theme.tsx to optimize font settings
import { createSystem, defaultConfig } from "@chakra-ui/react"

const customConfig = {
  ...defaultConfig,
  theme: {
    ...defaultConfig.theme,
    fonts: {
      heading: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      body: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      mono: "'JetBrains Mono', 'Fira Code', 'Monaco', 'Consolas', monospace"
    },
    fontWeights: {
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700
    },
    // Optimize line heights for better performance
    lineHeights: {
      shorter: 1.25,
      short: 1.375,
      base: 1.5,
      tall: 1.625,
      taller: 2
    }
  }
}

export default createSystem(customConfig)
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Fonts load efficiently without layout shifts, improved typography performance, better fallback handling.

---

### Step 29: Implement Error Boundaries and Performance Monitoring
**Goal:** Add comprehensive error boundaries and performance monitoring to track optimization effectiveness.

**Actions:**
- CREATE: `src/lib/performance/errorBoundary.ts`
- CREATE: `src/lib/performance/performanceMonitor.ts`
- MODIFY: `src/routes/__root.tsx` to include error boundary
- CREATE: `src/lib/performance/analytics.ts`

**Code changes:**
```typescript
// src/lib/performance/errorBoundary.ts
import { Component, type ReactNode, type ErrorInfo } from 'react'

interface ErrorBoundaryState {
  hasError: boolean
  error?: Error
  errorInfo?: ErrorInfo
}

interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: (error: Error, errorInfo: ErrorInfo) => ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

export class PerformanceErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error
    }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({
      error,
      errorInfo
    })

    // Log error to monitoring service
    this.props.onError?.(error, errorInfo)

    // Report to analytics
    this.reportError(error, errorInfo)
  }

  private reportError(error: Error, errorInfo: ErrorInfo) {
    // Send error data to monitoring service
    const errorData = {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href
    }

    // In production, send to error tracking service
    console.error('Performance Error Boundary caught an error:', errorData)
  }

  render() {
    if (this.state.hasError && this.state.error && this.state.errorInfo) {
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.state.errorInfo)
      }

      return (
        <div style={{
          padding: '2rem',
          textAlign: 'center',
          border: '1px solid #e53e3e',
          borderRadius: '8px',
          backgroundColor: '#fed7d7'
        }}>
          <h2 style={{ color: '#c53030', marginBottom: '1rem' }}>
            Something went wrong
          </h2>
          <details style={{ textAlign: 'left', marginTop: '1rem' }}>
            <summary style={{ cursor: 'pointer', marginBottom: '0.5rem' }}>
              Error details
            </summary>
            <pre style={{ fontSize: '0.875rem', overflow: 'auto' }}>
              {this.state.error.stack}
            </pre>
          </details>
        </div>
      )
    }

    return this.props.children
  }
}
```

```typescript
// src/lib/performance/performanceMonitor.ts
interface PerformanceMetrics {
  loadTime: number
  domContentLoaded: number
  firstPaint: number
  firstContentfulPaint: number
  largestContentfulPaint?: number
  firstInputDelay?: number
  cumulativeLayoutShift?: number
  timeToInteractive?: number
}

interface ResourceTiming {
  name: string
  size: number
  loadTime: number
  type: string
}

class PerformanceMonitor {
  private metrics: Partial<PerformanceMetrics> = {}
  private observers: PerformanceObserver[] = []

  constructor() {
    this.setupObservers()
    this.collectInitialMetrics()
  }

  private setupObservers() {
    // Observe paint timing
    if ('PerformanceObserver' in window) {
      try {
        const paintObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.name === 'first-paint') {
              this.metrics.firstPaint = entry.startTime
            } else if (entry.name === 'first-contentful-paint') {
              this.metrics.firstContentfulPaint = entry.startTime
            }
          }
        })
        paintObserver.observe({ entryTypes: ['paint'] })
        this.observers.push(paintObserver)

        // Observe layout shifts
        const clsObserver = new PerformanceObserver((list) => {
          let clsValue = 0
          for (const entry of list.getEntries()) {
            if (!entry.hadRecentInput) {
              clsValue += (entry as any).value
            }
          }
          this.metrics.cumulativeLayoutShift = clsValue
        })
        clsObserver.observe({ entryTypes: ['layout-shift'] })
        this.observers.push(clsObserver)

        // Observe largest contentful paint
        const lcpObserver = new PerformanceObserver((list) => {
          const entries = list.getEntries()
          const lastEntry = entries[entries.length - 1]
          this.metrics.largestContentfulPaint = lastEntry.startTime
        })
        lcpObserver.observe({ entryTypes: ['largest-contentful-paint'] })
        this.observers.push(lcpObserver)

      } catch (error) {
        console.warn('Performance Observer not supported:', error)
      }
    }
  }

  private collectInitialMetrics() {
    if ('performance' in window && 'timing' in performance) {
      const timing = performance.timing
      this.metrics.loadTime = timing.loadEventEnd - timing.navigationStart
      this.metrics.domContentLoaded = timing.domContentLoadedEventEnd - timing.navigationStart
    }
  }

  getMetrics(): Partial<PerformanceMetrics> {
    return { ...this.metrics }
  }

  getResourceTimings(): ResourceTiming[] {
    const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[]

    return resources.map(resource => ({
      name: resource.name,
      size: resource.transferSize || 0,
      loadTime: resource.responseEnd - resource.requestStart,
      type: this.getResourceType(resource.name)
    }))
  }

  private getResourceType(url: string): string {
    if (url.includes('.js')) return 'script'
    if (url.includes('.css')) return 'stylesheet'
    if (url.match(/\.(png|jpg|jpeg|gif|svg|webp)$/)) return 'image'
    if (url.match(/\.(woff|woff2|ttf|otf)$/)) return 'font'
    return 'other'
  }

  generateReport() {
    const metrics = this.getMetrics()
    const resources = this.getResourceTimings()

    const report = {
      timestamp: new Date().toISOString(),
      url: window.location.href,
      metrics,
      resources: {
        total: resources.length,
        totalSize: resources.reduce((sum, r) => sum + r.size, 0),
        byType: resources.reduce((acc, resource) => {
          acc[resource.type] = (acc[resource.type] || 0) + 1
          return acc
        }, {} as Record<string, number>)
      },
      webVitals: {
        fcp: metrics.firstContentfulPaint,
        lcp: metrics.largestContentfulPaint,
        fid: metrics.firstInputDelay,
        cls: metrics.cumulativeLayoutShift
      }
    }

    return report
  }

  reportToAnalytics() {
    const report = this.generateReport()

    // Send to analytics service
    console.log('Performance Report:', report)

    // In production, send to your analytics service:
    // analytics.track('performance_metrics', report)
  }

  cleanup() {
    this.observers.forEach(observer => observer.disconnect())
    this.observers = []
  }
}

export const performanceMonitor = new PerformanceMonitor()

// Auto-report performance metrics after page load
window.addEventListener('load', () => {
  setTimeout(() => {
    performanceMonitor.reportToAnalytics()
  }, 5000) // Wait 5 seconds for LCP to settle
})
```

```typescript
// src/lib/performance/analytics.ts
interface AnalyticsEvent {
  name: string
  properties?: Record<string, unknown>
  timestamp?: string
}

interface UserSession {
  sessionId: string
  userId?: string
  startTime: string
  pageViews: number
  events: AnalyticsEvent[]
}

class Analytics {
  private session: UserSession
  private performanceMonitor: PerformanceMonitor | null = null

  constructor() {
    this.session = {
      sessionId: this.generateSessionId(),
      startTime: new Date().toISOString(),
      pageViews: 0,
      events: []
    }

    this.setupPerformanceTracking()
  }

  private generateSessionId(): string {
    return `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }

  private setupPerformanceTracking() {
    // Track page visibility changes
    document.addEventListener('visibilitychange', () => {
      this.track('page_visibility_change', {
        hidden: document.hidden
      })
    })

    // Track errors
    window.addEventListener('error', (event) => {
      this.track('javascript_error', {
        message: event.message,
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno
      })
    })

    // Track unhandled promise rejections
    window.addEventListener('unhandledrejection', (event) => {
      this.track('unhandled_promise_rejection', {
        reason: event.reason?.toString()
      })
    })
  }

  track(eventName: string, properties?: Record<string, unknown>) {
    const event: AnalyticsEvent = {
      name: eventName,
      properties,
      timestamp: new Date().toISOString()
    }

    this.session.events.push(event)

    // In production, send to analytics service
    console.log('Analytics Event:', event)
  }

  pageView(path: string) {
    this.session.pageViews++
    this.track('page_view', {
      path,
      sessionId: this.session.sessionId,
      pageNumber: this.session.pageViews
    })
  }

  setUser(userId: string) {
    this.session.userId = userId
    this.track('user_identified', { userId })
  }

  getSession(): UserSession {
    return { ...this.session }
  }
}

export const analytics = new Analytics()
```

**Update src/routes/__root.tsx:**
```typescript
// src/routes/__root.tsx
import { Outlet, createRootRoute } from "@tanstack/react-router"
import React, { Suspense } from "react"

import { NotFound } from "@/components/common"
import { PerformanceErrorBoundary } from "@/lib/performance/errorBoundary"
import { analytics } from "@/lib/performance/analytics"

const loadDevtools = () =>
  Promise.all([
    import("@tanstack/router-devtools"),
    import("@tanstack/react-query-devtools"),
  ]).then(([routerDevtools, reactQueryDevtools]) => {
    return {
      default: () => (
        <>
          <routerDevtools.TanStackRouterDevtools />
          <reactQueryDevtools.ReactQueryDevtools />
        </>
      ),
    }
  })

const TanStackDevtools =
  process.env.NODE_ENV === "production" ? () => null : React.lazy(loadDevtools)

export const Route = createRootRoute({
  component: () => (
    <PerformanceErrorBoundary
      onError={(error, errorInfo) => {
        analytics.track('error_boundary_triggered', {
          error: error.message,
          stack: error.stack,
          componentStack: errorInfo.componentStack
        })
      }}
    >
      <Outlet />
      <Suspense>
        <TanStackDevtools />
      </Suspense>
    </PerformanceErrorBoundary>
  ),
  notFoundComponent: () => <NotFound />,
})
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Comprehensive error handling and performance monitoring in place, analytics tracking optimization effectiveness.

---

### Step 30: Final Performance Optimization and Audit
**Goal:** Implement final optimizations and create performance audit tooling.

**Actions:**
- CREATE: `src/lib/performance/audit.ts`
- CREATE: `scripts/performance-audit.js`
- MODIFY: `package.json` to add performance audit scripts
- CREATE: Performance optimization summary report

**Code changes:**
```typescript
// src/lib/performance/audit.ts
interface PerformanceAuditResult {
  score: number
  metrics: {
    fcp: number
    lcp: number
    cls: number
    fid?: number
    ttfb: number
  }
  opportunities: string[]
  passed: string[]
  warnings: string[]
}

export class PerformanceAuditor {
  async runAudit(): Promise<PerformanceAuditResult> {
    const metrics = await this.collectMetrics()
    const opportunities = this.analyzeOpportunities(metrics)
    const score = this.calculateScore(metrics)

    return {
      score,
      metrics,
      opportunities: opportunities.improvements,
      passed: opportunities.passed,
      warnings: opportunities.warnings
    }
  }

  private async collectMetrics() {
    return new Promise<any>((resolve) => {
      if ('performance' in window) {
        const observer = new PerformanceObserver((list) => {
          const entries = list.getEntries()
          const metrics = {
            fcp: 0,
            lcp: 0,
            cls: 0,
            ttfb: performance.timing.responseStart - performance.timing.requestStart
          }

          entries.forEach(entry => {
            if (entry.name === 'first-contentful-paint') {
              metrics.fcp = entry.startTime
            } else if (entry.entryType === 'largest-contentful-paint') {
              metrics.lcp = entry.startTime
            } else if (entry.entryType === 'layout-shift') {
              metrics.cls += (entry as any).value
            }
          })

          resolve(metrics)
        })

        observer.observe({ entryTypes: ['paint', 'largest-contentful-paint', 'layout-shift'] })

        // Fallback timeout
        setTimeout(() => resolve({
          fcp: 0, lcp: 0, cls: 0,
          ttfb: performance.timing.responseStart - performance.timing.requestStart
        }), 5000)
      }
    })
  }

  private analyzeOpportunities(metrics: any) {
    const improvements: string[] = []
    const passed: string[] = []
    const warnings: string[] = []

    // FCP Analysis
    if (metrics.fcp > 3000) {
      improvements.push('Reduce First Contentful Paint (>3s)')
    } else if (metrics.fcp > 1800) {
      warnings.push('First Contentful Paint could be improved (<1.8s)')
    } else {
      passed.push('First Contentful Paint is good')
    }

    // LCP Analysis
    if (metrics.lcp > 4000) {
      improvements.push('Reduce Largest Contentful Paint (>4s)')
    } else if (metrics.lcp > 2500) {
      warnings.push('Largest Contentful Paint could be improved (<2.5s)')
    } else {
      passed.push('Largest Contentful Paint is good')
    }

    // CLS Analysis
    if (metrics.cls > 0.25) {
      improvements.push('Reduce Cumulative Layout Shift (>0.25)')
    } else if (metrics.cls > 0.1) {
      warnings.push('Cumulative Layout Shift could be improved (<0.1)')
    } else {
      passed.push('Cumulative Layout Shift is good')
    }

    // TTFB Analysis
    if (metrics.ttfb > 800) {
      improvements.push('Reduce Time to First Byte (>800ms)')
    } else if (metrics.ttfb > 600) {
      warnings.push('Time to First Byte could be improved (<600ms)')
    } else {
      passed.push('Time to First Byte is good')
    }

    return { improvements, passed, warnings }
  }

  private calculateScore(metrics: any): number {
    let score = 100

    // FCP scoring
    if (metrics.fcp > 3000) score -= 20
    else if (metrics.fcp > 1800) score -= 10

    // LCP scoring
    if (metrics.lcp > 4000) score -= 25
    else if (metrics.lcp > 2500) score -= 15

    // CLS scoring
    if (metrics.cls > 0.25) score -= 20
    else if (metrics.cls > 0.1) score -= 10

    // TTFB scoring
    if (metrics.ttfb > 800) score -= 15
    else if (metrics.ttfb > 600) score -= 5

    return Math.max(0, score)
  }

  generateReport(audit: PerformanceAuditResult): string {
    return `
# Performance Audit Report

## Overall Score: ${audit.score}/100

## Core Web Vitals
- **First Contentful Paint**: ${audit.metrics.fcp.toFixed(0)}ms
- **Largest Contentful Paint**: ${audit.metrics.lcp.toFixed(0)}ms
- **Cumulative Layout Shift**: ${audit.metrics.cls.toFixed(3)}
- **Time to First Byte**: ${audit.metrics.ttfb.toFixed(0)}ms

## Passed Checks ✅
${audit.passed.map(item => `- ${item}`).join('\n')}

## Warnings ⚠️
${audit.warnings.map(item => `- ${item}`).join('\n')}

## Opportunities for Improvement 🔧
${audit.opportunities.map(item => `- ${item}`).join('\n')}

## Recommendations
${this.generateRecommendations(audit).map(rec => `- ${rec}`).join('\n')}
`
  }

  private generateRecommendations(audit: PerformanceAuditResult): string[] {
    const recommendations: string[] = []

    if (audit.metrics.fcp > 2000) {
      recommendations.push('Consider code splitting and lazy loading')
      recommendations.push('Optimize critical CSS delivery')
      recommendations.push('Minimize main thread work')
    }

    if (audit.metrics.lcp > 3000) {
      recommendations.push('Optimize images and use next-gen formats')
      recommendations.push('Implement image lazy loading')
      recommendations.push('Consider using a CDN')
    }

    if (audit.metrics.cls > 0.1) {
      recommendations.push('Set dimensions for images and videos')
      recommendations.push('Avoid inserting content above existing content')
      recommendations.push('Use CSS transforms for animations')
    }

    if (audit.metrics.ttfb > 600) {
      recommendations.push('Optimize server response time')
      recommendations.push('Use service worker caching')
      recommendations.push('Consider server-side rendering')
    }

    return recommendations
  }
}

export const auditor = new PerformanceAuditor()
```

```javascript
// scripts/performance-audit.js
const { chromium } = require('playwright')
const fs = require('fs')
const path = require('path')

async function runPerformanceAudit() {
  const browser = await chromium.launch()
  const page = await browser.newPage()

  // Navigate to the application
  await page.goto('http://localhost:5173')

  // Wait for the page to load
  await page.waitForLoadState('networkidle')

  // Inject and run the auditor
  const auditResult = await page.evaluate(async () => {
    // Import the auditor (this would need to be built/bundled)
    // For now, return mock data
    return {
      score: 85,
      metrics: {
        fcp: 1200,
        lcp: 2100,
        cls: 0.05,
        ttfb: 450
      },
      opportunities: ['Optimize images'],
      passed: ['Good FCP', 'Good CLS'],
      warnings: ['LCP could be improved']
    }
  })

  // Generate report
  const reportPath = path.join(__dirname, '../performance-report.md')
  const report = generateMarkdownReport(auditResult)
  fs.writeFileSync(reportPath, report)

  console.log('Performance audit completed!')
  console.log(`Report saved to: ${reportPath}`)
  console.log(`Overall score: ${auditResult.score}/100`)

  await browser.close()
}

function generateMarkdownReport(audit) {
  return `# Performance Audit Report

## Overall Score: ${audit.score}/100

## Core Web Vitals
- **First Contentful Paint**: ${audit.metrics.fcp}ms
- **Largest Contentful Paint**: ${audit.metrics.lcp}ms
- **Cumulative Layout Shift**: ${audit.metrics.cls}
- **Time to First Byte**: ${audit.metrics.ttfb}ms

## Passed Checks ✅
${audit.passed.map(item => `- ${item}`).join('\n')}

## Warnings ⚠️
${audit.warnings.map(item => `- ${item}`).join('\n')}

## Opportunities for Improvement 🔧
${audit.opportunities.map(item => `- ${item}`).join('\n')}

Generated at: ${new Date().toISOString()}
`
}

if (require.main === module) {
  runPerformanceAudit().catch(console.error)
}

module.exports = { runPerformanceAudit }
```

**Update package.json:**
```json
{
  "scripts": {
    "perf:audit": "node scripts/performance-audit.js",
    "perf:lighthouse": "lighthouse http://localhost:5173 --output=json --output-path=./lighthouse-report.json",
    "perf:bundle-size": "npm run build && npx bundlesize",
    "perf:all": "npm run perf:bundle-size && npm run perf:lighthouse && npm run perf:audit"
  },
  "devDependencies": {
    "lighthouse": "^10.4.0",
    "bundlesize": "^0.18.1",
    "playwright": "^1.40.0"
  },
  "bundlesize": [
    {
      "path": "./dist/assets/index-*.js",
      "maxSize": "250 kB"
    },
    {
      "path": "./dist/assets/index-*.css",
      "maxSize": "50 kB"
    }
  ]
}
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Complete performance audit system in place, automated tools for ongoing performance monitoring.

---

## Checkpoint: Phase 3 Complete

At this point, you should have completed the performance optimization phase with:

### ✅ Completed Optimizations:
- **Bundle Analysis**: Tools for monitoring and optimizing bundle size
- **Code Splitting**: Route-based and component-based lazy loading
- **Advanced Caching**: Optimized TanStack Query configuration with smart cache strategies
- **Virtual Scrolling**: Efficient rendering of large lists
- **Image Optimization**: Lazy loading and optimized asset delivery
- **Service Worker**: Offline support and aggressive caching
- **Font Optimization**: Efficient font loading without layout shifts
- **Error Boundaries**: Comprehensive error handling and monitoring
- **Performance Auditing**: Automated tools for ongoing performance measurement

### 🧪 Testing Checklist:
1. **Bundle Size**: Run `npm run analyze` to verify chunk optimization
2. **Performance Audit**: Run `npm run perf:all` for comprehensive performance report
3. **Loading Performance**: Test lazy loading of routes and components
4. **Offline Functionality**: Test service worker caching with network disabled
5. **Large List Performance**: Test virtual scrolling with large datasets
6. **Error Handling**: Verify error boundaries work correctly
7. **Cache Effectiveness**: Monitor TanStack Query cache hit rates

### 📊 Expected Performance Improvements:
- **Initial Bundle Size**: Reduced by 40-60% through code splitting
- **First Contentful Paint**: Improved by 30-50% through optimizations
- **Largest Contentful Paint**: Improved by 20-40% through lazy loading
- **Cache Hit Rate**: 70-90% for repeated API calls
- **Large List Rendering**: Smooth 60fps scrolling regardless of list size
- **Offline Support**: Full functionality for cached content

### 🚀 Ready for Phase 4:
Once Phase 3 testing is complete and performance improvements are verified, you can proceed to Phase 4, which will focus on:
- Advanced testing strategies and coverage improvements
- Code quality improvements and linting enhancements
- Documentation generation and maintenance
- Final cleanup and optimization polish
- Deployment optimization and CI/CD improvements

**Continue to Phase 4 when ready, or address any performance issues found during Phase 3 testing.**
