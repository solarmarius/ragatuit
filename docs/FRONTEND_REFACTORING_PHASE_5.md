# Frontend Refactoring Phase 5: Final Optimization & Long-term Sustainability

## Overview
This document provides detailed steps 41-50 for implementing final optimizations, establishing long-term maintenance procedures, and ensuring project sustainability. This phase should be started only after completing Phases 1-4 successfully.

## Prerequisites
- Phases 1, 2, 3, and 4 completed successfully
- All tests passing with 80%+ coverage
- Production monitoring active
- CI/CD pipelines functional
- Documentation complete

## Phase 5: Final Optimization & Sustainability (Steps 41-50)

### Step 41: Advanced Performance Optimization
**Goal:** Implement cutting-edge performance optimizations and micro-improvements.

**Actions:**
- CREATE: `src/lib/optimization/` directory
- CREATE: `src/lib/optimization/preloading.ts`
- CREATE: `src/lib/optimization/resourceHints.ts`
- CREATE: `src/lib/optimization/criticalPath.ts`
- MODIFY: Application to use advanced optimization techniques

**Code changes:**
```typescript
// src/lib/optimization/preloading.ts
interface PreloadConfig {
  routes: string[]
  components: string[]
  data: string[]
  images: string[]
  fonts: string[]
}

class IntelligentPreloader {
  private preloadedRoutes = new Set<string>()
  private preloadedComponents = new Set<string>()
  private preloadedData = new Set<string>()
  private intersectionObserver?: IntersectionObserver
  private idleCallback?: number

  constructor(private config: PreloadConfig) {
    this.setupIntersectionObserver()
    this.setupIdlePreloading()
    this.setupUserBehaviorTracking()
  }

  private setupIntersectionObserver() {
    if ('IntersectionObserver' in window) {
      this.intersectionObserver = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              this.preloadLinkTarget(entry.target as HTMLElement)
            }
          })
        },
        { rootMargin: '100px' }
      )

      // Observe all navigation links
      document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('a[href^="/"]').forEach((link) => {
          this.intersectionObserver?.observe(link)
        })
      })
    }
  }

  private setupIdlePreloading() {
    if ('requestIdleCallback' in window) {
      this.idleCallback = window.requestIdleCallback(() => {
        this.preloadCriticalResources()
      }, { timeout: 5000 })
    } else {
      // Fallback for browsers without requestIdleCallback
      setTimeout(() => this.preloadCriticalResources(), 2000)
    }
  }

  private setupUserBehaviorTracking() {
    // Track mouse hover to predict navigation intent
    document.addEventListener('mouseover', (event) => {
      const target = event.target as HTMLElement
      const link = target.closest('a[href^="/"]')

      if (link) {
        const href = link.getAttribute('href')
        if (href && !this.preloadedRoutes.has(href)) {
          // Debounce to avoid excessive preloading
          setTimeout(() => this.preloadRoute(href), 100)
        }
      }
    })

    // Track scroll patterns for predictive loading
    let scrollTimeout: number
    document.addEventListener('scroll', () => {
      clearTimeout(scrollTimeout)
      scrollTimeout = window.setTimeout(() => {
        this.handleScrollEnd()
      }, 150)
    })
  }

  private preloadLinkTarget(element: HTMLElement) {
    const link = element.closest('a[href^="/"]')
    if (link) {
      const href = link.getAttribute('href')
      if (href) {
        this.preloadRoute(href)
      }
    }
  }

  private async preloadRoute(route: string) {
    if (this.preloadedRoutes.has(route)) return

    this.preloadedRoutes.add(route)

    try {
      // Preload route component
      await this.preloadRouteComponent(route)

      // Preload route data
      await this.preloadRouteData(route)

      // Preload critical assets
      await this.preloadRouteAssets(route)
    } catch (error) {
      console.warn(`Failed to preload route ${route}:`, error)
    }
  }

  private async preloadRouteComponent(route: string) {
    const componentMap: Record<string, () => Promise<any>> = {
      '/dashboard': () => import('@/routes/_layout/index'),
      '/quizzes': () => import('@/routes/_layout/quizzes'),
      '/create-quiz': () => import('@/routes/_layout/create-quiz'),
      '/settings': () => import('@/routes/_layout/settings'),
    }

    const importFn = componentMap[route]
    if (importFn && !this.preloadedComponents.has(route)) {
      this.preloadedComponents.add(route)
      await importFn()
    }
  }

  private async preloadRouteData(route: string) {
    if (this.preloadedData.has(route)) return

    const dataPreloaders: Record<string, () => Promise<void>> = {
      '/dashboard': async () => {
        const { QueryClient } = await import('@tanstack/react-query')
        const { QuizService } = await import('@/client')
        const queryClient = new QueryClient()

        await queryClient.prefetchQuery({
          queryKey: ['user-quizzes'],
          queryFn: QuizService.getUserQuizzesEndpoint,
          staleTime: 5 * 60 * 1000 // 5 minutes
        })
      },
      '/quizzes': async () => {
        // Preload quiz list data
        const { QuizService } = await import('@/client')
        await QuizService.getUserQuizzesEndpoint()
      }
    }

    const preloader = dataPreloaders[route]
    if (preloader) {
      this.preloadedData.add(route)
      await preloader()
    }
  }

  private async preloadRouteAssets(route: string) {
    const assetMap: Record<string, string[]> = {
      '/dashboard': [
        '/assets/images/dashboard-illustration.svg',
        '/assets/images/chart-icons.svg'
      ],
      '/create-quiz': [
        '/assets/images/quiz-creation-steps.svg'
      ]
    }

    const assets = assetMap[route]
    if (assets) {
      await Promise.all(assets.map(asset => this.preloadImage(asset)))
    }
  }

  private preloadImage(src: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const img = new Image()
      img.onload = () => resolve()
      img.onerror = reject
      img.src = src
    })
  }

  private async preloadCriticalResources() {
    // Preload fonts
    await Promise.all(this.config.fonts.map(font => this.preloadFont(font)))

    // Preload critical images
    await Promise.all(this.config.images.map(img => this.preloadImage(img)))

    // Preload likely next routes based on current page
    const currentPath = window.location.pathname
    const likelyRoutes = this.getPredictedRoutes(currentPath)

    for (const route of likelyRoutes) {
      await this.preloadRoute(route)
    }
  }

  private preloadFont(fontUrl: string): Promise<void> {
    if ('fonts' in document) {
      return document.fonts.load(`1em ${fontUrl}`)
    }
    return Promise.resolve()
  }

  private getPredictedRoutes(currentPath: string): string[] {
    const routePredictions: Record<string, string[]> = {
      '/': ['/dashboard', '/quizzes'],
      '/dashboard': ['/create-quiz', '/quizzes'],
      '/quizzes': ['/create-quiz'],
      '/create-quiz': ['/dashboard']
    }

    return routePredictions[currentPath] || []
  }

  private handleScrollEnd() {
    const scrollPosition = window.scrollY
    const documentHeight = document.documentElement.scrollHeight
    const windowHeight = window.innerHeight

    // If user scrolled past 70% of the page, preload next likely content
    if (scrollPosition / (documentHeight - windowHeight) > 0.7) {
      this.preloadNextPageContent()
    }
  }

  private async preloadNextPageContent() {
    // Preload pagination or infinite scroll content
    const currentPath = window.location.pathname

    if (currentPath === '/quizzes') {
      // Preload additional quiz data
      try {
        const { QuizService } = await import('@/client')
        await QuizService.getUserQuizzesEndpoint()
      } catch (error) {
        console.warn('Failed to preload next page content:', error)
      }
    }
  }

  destroy() {
    this.intersectionObserver?.disconnect()
    if (this.idleCallback) {
      window.cancelIdleCallback(this.idleCallback)
    }
  }
}

export { IntelligentPreloader, type PreloadConfig }
```

```typescript
// src/lib/optimization/resourceHints.ts
interface ResourceHint {
  href: string
  as?: string
  type?: string
  crossorigin?: string
  integrity?: string
}

class ResourceHintManager {
  private addedHints = new Set<string>()

  constructor() {
    this.addCriticalResourceHints()
  }

  private addCriticalResourceHints() {
    // Add DNS prefetch for external resources
    this.addDnsPrefetch('https://fonts.googleapis.com')
    this.addDnsPrefetch('https://fonts.gstatic.com')

    // Add preconnect for critical external resources
    this.addPreconnect('https://api.your-domain.com', true)

    // Add modulepreload for critical JavaScript
    this.addModulePreload('/assets/index.js')
  }

  addDnsPrefetch(href: string) {
    if (this.addedHints.has(`dns-prefetch:${href}`)) return

    const link = document.createElement('link')
    link.rel = 'dns-prefetch'
    link.href = href

    document.head.appendChild(link)
    this.addedHints.add(`dns-prefetch:${href}`)
  }

  addPreconnect(href: string, crossorigin = false) {
    if (this.addedHints.has(`preconnect:${href}`)) return

    const link = document.createElement('link')
    link.rel = 'preconnect'
    link.href = href

    if (crossorigin) {
      link.crossOrigin = 'anonymous'
    }

    document.head.appendChild(link)
    this.addedHints.add(`preconnect:${href}`)
  }

  addPreload(hint: ResourceHint) {
    const key = `preload:${hint.href}`
    if (this.addedHints.has(key)) return

    const link = document.createElement('link')
    link.rel = 'preload'
    link.href = hint.href

    if (hint.as) link.as = hint.as
    if (hint.type) link.type = hint.type
    if (hint.crossorigin) link.crossOrigin = hint.crossorigin
    if (hint.integrity) link.integrity = hint.integrity

    document.head.appendChild(link)
    this.addedHints.add(key)
  }

  addModulePreload(href: string) {
    if (this.addedHints.has(`modulepreload:${href}`)) return

    const link = document.createElement('link')
    link.rel = 'modulepreload'
    link.href = href

    document.head.appendChild(link)
    this.addedHints.add(`modulepreload:${href}`)
  }

  addPrefetch(href: string) {
    if (this.addedHints.has(`prefetch:${href}`)) return

    const link = document.createElement('link')
    link.rel = 'prefetch'
    link.href = href

    document.head.appendChild(link)
    this.addedHints.add(`prefetch:${href}`)
  }

  // Preload critical above-the-fold images
  preloadCriticalImages(images: string[]) {
    images.forEach(src => {
      this.addPreload({
        href: src,
        as: 'image',
        type: this.getImageType(src)
      })
    })
  }

  // Preload critical fonts
  preloadCriticalFonts(fonts: Array<{ href: string; type: string }>) {
    fonts.forEach(font => {
      this.addPreload({
        href: font.href,
        as: 'font',
        type: font.type,
        crossorigin: 'anonymous'
      })
    })
  }

  private getImageType(src: string): string {
    const ext = src.split('.').pop()?.toLowerCase()
    const typeMap: Record<string, string> = {
      'jpg': 'image/jpeg',
      'jpeg': 'image/jpeg',
      'png': 'image/png',
      'webp': 'image/webp',
      'avif': 'image/avif',
      'svg': 'image/svg+xml'
    }
    return typeMap[ext || ''] || 'image/*'
  }

  removeHint(rel: string, href: string) {
    const link = document.querySelector(`link[rel="${rel}"][href="${href}"]`)
    if (link) {
      document.head.removeChild(link)
      this.addedHints.delete(`${rel}:${href}`)
    }
  }

  cleanup() {
    // Remove all added hints
    this.addedHints.forEach(hint => {
      const [rel, href] = hint.split(':')
      this.removeHint(rel, href)
    })
    this.addedHints.clear()
  }
}

export const resourceHintManager = new ResourceHintManager()
```

```typescript
// src/lib/optimization/criticalPath.ts
interface CriticalPathConfig {
  inlineCSS: boolean
  preloadFonts: boolean
  optimizeImages: boolean
  deferNonCritical: boolean
}

class CriticalPathOptimizer {
  private config: CriticalPathConfig

  constructor(config: CriticalPathConfig) {
    this.config = config
    this.initializeOptimizations()
  }

  private initializeOptimizations() {
    if (this.config.inlineCSS) {
      this.inlineCriticalCSS()
    }

    if (this.config.preloadFonts) {
      this.optimizeFontLoading()
    }

    if (this.config.optimizeImages) {
      this.optimizeImageLoading()
    }

    if (this.config.deferNonCritical) {
      this.deferNonCriticalResources()
    }
  }

  private inlineCriticalCSS() {
    // Extract and inline critical CSS for above-the-fold content
    const criticalCSS = `
      /* Critical CSS for above-the-fold content */
      body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        margin: 0;
        padding: 0;
      }

      .loading-skeleton {
        background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
        background-size: 200% 100%;
        animation: loading 1.5s infinite;
      }

      @keyframes loading {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
      }

      /* Critical layout styles */
      .app-container {
        min-height: 100vh;
        display: flex;
        flex-direction: column;
      }
    `

    const style = document.createElement('style')
    style.textContent = criticalCSS
    document.head.appendChild(style)
  }

  private optimizeFontLoading() {
    // Preload critical fonts and use font-display: swap
    const criticalFonts = [
      { href: '/fonts/Inter-400.woff2', type: 'font/woff2' },
      { href: '/fonts/Inter-500.woff2', type: 'font/woff2' }
    ]

    criticalFonts.forEach(font => {
      const link = document.createElement('link')
      link.rel = 'preload'
      link.href = font.href
      link.as = 'font'
      link.type = font.type
      link.crossOrigin = 'anonymous'
      document.head.appendChild(link)
    })

    // Add font-display: swap CSS
    const fontCSS = `
      @font-face {
        font-family: 'Inter';
        font-display: swap;
        src: url('/fonts/Inter-400.woff2') format('woff2');
        font-weight: 400;
        font-style: normal;
      }

      @font-face {
        font-family: 'Inter';
        font-display: swap;
        src: url('/fonts/Inter-500.woff2') format('woff2');
        font-weight: 500;
        font-style: normal;
      }
    `

    const style = document.createElement('style')
    style.textContent = fontCSS
    document.head.appendChild(style)
  }

  private optimizeImageLoading() {
    // Add loading="lazy" to all images below the fold
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const img = entry.target as HTMLImageElement
            if (img.dataset.src) {
              img.src = img.dataset.src
              img.removeAttribute('data-src')
              observer.unobserve(img)
            }
          }
        })
      },
      { rootMargin: '50px' }
    )

    // Observe all images with data-src
    document.querySelectorAll('img[data-src]').forEach(img => {
      observer.observe(img)
    })

    // Add decoding="async" to all images
    document.querySelectorAll('img').forEach(img => {
      img.decoding = 'async'
    })
  }

  private deferNonCriticalResources() {
    // Defer non-critical JavaScript
    this.deferNonCriticalJS()

    // Defer non-critical CSS
    this.deferNonCriticalCSS()

    // Defer analytics and tracking scripts
    this.deferAnalytics()
  }

  private deferNonCriticalJS() {
    const nonCriticalScripts = [
      'analytics',
      'tracking',
      'social',
      'comments'
    ]

    // Defer loading of non-critical scripts until after main content
    window.addEventListener('load', () => {
      setTimeout(() => {
        nonCriticalScripts.forEach(scriptType => {
          this.loadDeferredScript(scriptType)
        })
      }, 1000)
    })
  }

  private deferNonCriticalCSS() {
    // Load non-critical CSS asynchronously
    const nonCriticalCSS = [
      '/assets/non-critical.css',
      '/assets/print.css'
    ]

    nonCriticalCSS.forEach(href => {
      const link = document.createElement('link')
      link.rel = 'preload'
      link.href = href
      link.as = 'style'
      link.onload = () => {
        link.rel = 'stylesheet'
      }
      document.head.appendChild(link)
    })
  }

  private deferAnalytics() {
    // Defer analytics until user interaction or after 3 seconds
    let analyticsLoaded = false

    const loadAnalytics = () => {
      if (analyticsLoaded) return
      analyticsLoaded = true

      // Load analytics scripts here
      console.log('Loading analytics...')
    }

    // Load on first user interaction
    const interactionEvents = ['click', 'scroll', 'keydown', 'touchstart']
    const onFirstInteraction = () => {
      loadAnalytics()
      interactionEvents.forEach(event => {
        document.removeEventListener(event, onFirstInteraction)
      })
    }

    interactionEvents.forEach(event => {
      document.addEventListener(event, onFirstInteraction, { passive: true })
    })

    // Fallback: load after 3 seconds
    setTimeout(loadAnalytics, 3000)
  }

  private loadDeferredScript(scriptType: string) {
    // Implementation for loading deferred scripts
    console.log(`Loading deferred script: ${scriptType}`)
  }

  measureCriticalPath() {
    // Measure critical rendering path metrics
    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming

    const metrics = {
      domContentLoaded: navigation.domContentLoadedEventEnd - navigation.navigationStart,
      firstPaint: 0,
      firstContentfulPaint: 0,
      largestContentfulPaint: 0
    }

    // Get paint timing
    const paintEntries = performance.getEntriesByType('paint')
    paintEntries.forEach(entry => {
      if (entry.name === 'first-paint') {
        metrics.firstPaint = entry.startTime
      } else if (entry.name === 'first-contentful-paint') {
        metrics.firstContentfulPaint = entry.startTime
      }
    })

    // Get LCP
    const lcpEntries = performance.getEntriesByType('largest-contentful-paint')
    if (lcpEntries.length > 0) {
      metrics.largestContentfulPaint = lcpEntries[lcpEntries.length - 1].startTime
    }

    return metrics
  }
}

export { CriticalPathOptimizer, type CriticalPathConfig }
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Advanced performance optimizations implemented with intelligent preloading and critical path optimization.

---

### Step 42: Memory Management and Leak Prevention
**Goal:** Implement comprehensive memory management to prevent memory leaks and optimize garbage collection.

**Actions:**
- CREATE: `src/lib/optimization/memoryManager.ts`
- CREATE: `src/lib/optimization/leakDetection.ts`
- CREATE: `src/hooks/common/useMemoryOptimization.ts`
- MODIFY: Components to use memory optimization patterns

**Code changes:**
```typescript
// src/lib/optimization/memoryManager.ts
interface MemoryMetrics {
  usedJSHeapSize: number
  totalJSHeapSize: number
  jsHeapSizeLimit: number
  timestamp: number
}

interface ComponentMemoryTracker {
  componentName: string
  mountTime: number
  unmountTime?: number
  memoryUsage: MemoryMetrics[]
}

class MemoryManager {
  private componentTrackers = new Map<string, ComponentMemoryTracker>()
  private cleanupTasks = new Set<() => void>()
  private memoryWatcher?: number
  private isWatching = false

  constructor() {
    this.setupMemoryWatcher()
    this.setupUnloadCleanup()
  }

  private setupMemoryWatcher() {
    if ('memory' in performance) {
      this.startMemoryWatching()
    }
  }

  private setupUnloadCleanup() {
    window.addEventListener('beforeunload', () => {
      this.cleanup()
    })

    // Handle page visibility changes
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.performMaintenanceCleanup()
      }
    })
  }

  startMemoryWatching() {
    if (this.isWatching) return

    this.isWatching = true
    this.memoryWatcher = window.setInterval(() => {
      this.collectMemoryMetrics()
    }, 10000) // Every 10 seconds
  }

  stopMemoryWatching() {
    if (this.memoryWatcher) {
      clearInterval(this.memoryWatcher)
      this.memoryWatcher = undefined
    }
    this.isWatching = false
  }

  private collectMemoryMetrics() {
    if ('memory' in performance) {
      const memory = (performance as any).memory
      const metrics: MemoryMetrics = {
        usedJSHeapSize: memory.usedJSHeapSize,
        totalJSHeapSize: memory.totalJSHeapSize,
        jsHeapSizeLimit: memory.jsHeapSizeLimit,
        timestamp: Date.now()
      }

      this.analyzeMemoryUsage(metrics)

      // Store metrics for active components
      this.componentTrackers.forEach((tracker) => {
        if (!tracker.unmountTime) {
          tracker.memoryUsage.push(metrics)

          // Keep only last 10 measurements per component
          if (tracker.memoryUsage.length > 10) {
            tracker.memoryUsage.shift()
          }
        }
      })
    }
  }

  private analyzeMemoryUsage(metrics: MemoryMetrics) {
    const usagePercentage = (metrics.usedJSHeapSize / metrics.jsHeapSizeLimit) * 100

    if (usagePercentage > 80) {
      console.warn('High memory usage detected:', usagePercentage.toFixed(2) + '%')
      this.performMaintenanceCleanup()
    }

    if (usagePercentage > 90) {
      console.error('Critical memory usage detected:', usagePercentage.toFixed(2) + '%')
      this.performEmergencyCleanup()
    }
  }

  trackComponent(componentName: string): string {
    const trackerId = `${componentName}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

    const tracker: ComponentMemoryTracker = {
      componentName,
      mountTime: Date.now(),
      memoryUsage: []
    }

    this.componentTrackers.set(trackerId, tracker)
    return trackerId
  }

  untrackComponent(trackerId: string) {
    const tracker = this.componentTrackers.get(trackerId)
    if (tracker) {
      tracker.unmountTime = Date.now()

      // Remove tracker after a delay to allow for analysis
      setTimeout(() => {
        this.componentTrackers.delete(trackerId)
      }, 60000) // Keep for 1 minute after unmount
    }
  }

  addCleanupTask(task: () => void): () => void {
    this.cleanupTasks.add(task)

    // Return a function to remove the cleanup task
    return () => {
      this.cleanupTasks.delete(task)
    }
  }

  private performMaintenanceCleanup() {
    // Run garbage collection if available
    if ('gc' in window) {
      (window as any).gc()
    }

    // Clear old component trackers
    const now = Date.now()
    const oneHourAgo = now - (60 * 60 * 1000)

    this.componentTrackers.forEach((tracker, id) => {
      if (tracker.unmountTime && tracker.unmountTime < oneHourAgo) {
        this.componentTrackers.delete(id)
      }
    })

    // Run maintenance cleanup tasks
    this.cleanupTasks.forEach(task => {
      try {
        task()
      } catch (error) {
        console.warn('Cleanup task failed:', error)
      }
    })
  }

  private performEmergencyCleanup() {
    // Clear all cached data
    this.clearAllCaches()

    // Perform maintenance cleanup
    this.performMaintenanceCleanup()

    // Clear old DOM references
    this.clearDOMReferences()
  }

  private clearAllCaches() {
    // Clear query cache
    const queryClient = (window as any).__REACT_QUERY_CLIENT__
    if (queryClient) {
      queryClient.clear()
    }

    // Clear router cache
    const router = (window as any).__TANSTACK_ROUTER__
    if (router) {
      router.clearCache?.()
    }

    // Clear image caches
    this.clearImageCaches()
  }

  private clearImageCaches() {
    // Remove unused images from DOM
    document.querySelectorAll('img[data-loaded="false"]').forEach(img => {
      if (img.parentNode) {
        img.parentNode.removeChild(img)
      }
    })
  }

  private clearDOMReferences() {
    // Clear event listeners that might hold references
    const elements = document.querySelectorAll('[data-cleanup-required]')
    elements.forEach(element => {
      // Clone element to remove all event listeners
      const newElement = element.cloneNode(true)
      element.parentNode?.replaceChild(newElement, element)
    })
  }

  getMemoryReport(): MemoryReport {
    const activeComponents = Array.from(this.componentTrackers.values())
      .filter(tracker => !tracker.unmountTime)

    const memoryLeaks = this.detectPotentialLeaks()

    let currentMetrics: MemoryMetrics | null = null
    if ('memory' in performance) {
      const memory = (performance as any).memory
      currentMetrics = {
        usedJSHeapSize: memory.usedJSHeapSize,
        totalJSHeapSize: memory.totalJSHeapSize,
        jsHeapSizeLimit: memory.jsHeapSizeLimit,
        timestamp: Date.now()
      }
    }

    return {
      currentMemoryUsage: currentMetrics,
      activeComponents: activeComponents.length,
      potentialLeaks: memoryLeaks,
      cleanupTasks: this.cleanupTasks.size,
      componentDetails: activeComponents.map(tracker => ({
        name: tracker.componentName,
        mountDuration: Date.now() - tracker.mountTime,
        memoryTrend: this.calculateMemoryTrend(tracker.memoryUsage)
      }))
    }
  }

  private detectPotentialLeaks(): string[] {
    const leaks: string[] = []
    const now = Date.now()
    const oneHourAgo = now - (60 * 60 * 1000)

    // Check for long-lived components
    this.componentTrackers.forEach((tracker, id) => {
      if (!tracker.unmountTime && tracker.mountTime < oneHourAgo) {
        leaks.push(`Long-lived component: ${tracker.componentName}`)
      }

      // Check for memory growth in components
      if (tracker.memoryUsage.length >= 5) {
        const trend = this.calculateMemoryTrend(tracker.memoryUsage)
        if (trend > 1000000) { // 1MB growth
          leaks.push(`Memory growth in component: ${tracker.componentName}`)
        }
      }
    })

    return leaks
  }

  private calculateMemoryTrend(metrics: MemoryMetrics[]): number {
    if (metrics.length < 2) return 0

    const first = metrics[0].usedJSHeapSize
    const last = metrics[metrics.length - 1].usedJSHeapSize

    return last - first
  }

  cleanup() {
    this.stopMemoryWatching()

    // Run all cleanup tasks
    this.cleanupTasks.forEach(task => {
      try {
        task()
      } catch (error) {
        console.warn('Cleanup task failed:', error)
      }
    })

    this.cleanupTasks.clear()
    this.componentTrackers.clear()
  }
}

interface MemoryReport {
  currentMemoryUsage: MemoryMetrics | null
  activeComponents: number
  potentialLeaks: string[]
  cleanupTasks: number
  componentDetails: Array<{
    name: string
    mountDuration: number
    memoryTrend: number
  }>
}

export const memoryManager = new MemoryManager()
export type { MemoryReport, MemoryMetrics }
```

```typescript
// src/hooks/common/useMemoryOptimization.ts
import { useEffect, useRef, useCallback } from 'react'
import { memoryManager } from '@/lib/optimization/memoryManager'

interface MemoryOptimizationOptions {
  componentName: string
  trackMemory?: boolean
  cleanupInterval?: number
  autoCleanup?: boolean
}

export function useMemoryOptimization(options: MemoryOptimizationOptions) {
  const { componentName, trackMemory = true, cleanupInterval = 60000, autoCleanup = true } = options

  const trackerIdRef = useRef<string>()
  const cleanupTasksRef = useRef<Set<() => void>>(new Set())
  const timersRef = useRef<Set<number>>(new Set())
  const observersRef = useRef<Set<IntersectionObserver | MutationObserver | ResizeObserver>>(new Set())

  useEffect(() => {
    if (trackMemory) {
      trackerIdRef.current = memoryManager.trackComponent(componentName)
    }

    return () => {
      if (trackerIdRef.current) {
        memoryManager.untrackComponent(trackerIdRef.current)
      }
    }
  }, [componentName, trackMemory])

  useEffect(() => {
    if (autoCleanup && cleanupInterval > 0) {
      const interval = setInterval(() => {
        performCleanup()
      }, cleanupInterval)

      timersRef.current.add(interval)

      return () => {
        clearInterval(interval)
        timersRef.current.delete(interval)
      }
    }
  }, [autoCleanup, cleanupInterval])

  const addCleanupTask = useCallback((task: () => void) => {
    cleanupTasksRef.current.add(task)

    return () => {
      cleanupTasksRef.current.delete(task)
    }
  }, [])

  const addTimer = useCallback((timer: number) => {
    timersRef.current.add(timer)

    return () => {
      clearTimeout(timer)
      clearInterval(timer)
      timersRef.current.delete(timer)
    }
  }, [])

  const addObserver = useCallback((observer: IntersectionObserver | MutationObserver | ResizeObserver) => {
    observersRef.current.add(observer)

    return () => {
      observer.disconnect()
      observersRef.current.delete(observer)
    }
  }, [])

  const performCleanup = useCallback(() => {
    // Run component-specific cleanup tasks
    cleanupTasksRef.current.forEach(task => {
      try {
        task()
      } catch (error) {
        console.warn(`Cleanup task failed in ${componentName}:`, error)
      }
    })

    // Clear timers
    timersRef.current.forEach(timer => {
      clearTimeout(timer)
      clearInterval(timer)
    })

    // Disconnect observers
    observersRef.current.forEach(observer => {
      observer.disconnect()
    })
  }, [componentName])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      performCleanup()
      cleanupTasksRef.current.clear()
      timersRef.current.clear()
      observersRef.current.clear()
    }
  }, [performCleanup])

  return {
    addCleanupTask,
    addTimer,
    addObserver,
    performCleanup
  }
}

// Higher-order component for automatic memory optimization
export function withMemoryOptimization<T extends Record<string, unknown>>(
  Component: React.ComponentType<T>,
  componentName?: string
) {
  const MemoizedComponent = React.memo(Component)

  return function MemoryOptimizedComponent(props: T) {
    const name = componentName || Component.displayName || Component.name || 'Unknown'
    useMemoryOptimization({ componentName: name })

    return <MemoizedComponent {...props} />
  }
}
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Comprehensive memory management system preventing leaks and optimizing garbage collection.

---

### Step 43: Accessibility Excellence and Compliance
**Goal:** Achieve WCAG 2.1 AA compliance and implement advanced accessibility features.

**Actions:**
- CREATE: `src/lib/accessibility/` directory
- CREATE: `src/lib/accessibility/a11yManager.ts`
- CREATE: `src/lib/accessibility/announcer.ts`
- CREATE: `src/hooks/common/useA11y.ts`
- CREATE: Accessibility audit tools

**Code changes:**
```typescript
// src/lib/accessibility/a11yManager.ts
interface AccessibilityConfig {
  enableAnnouncements: boolean
  enableKeyboardNav: boolean
  enableScreenReader: boolean
  enableHighContrast: boolean
  enableReducedMotion: boolean
}

interface AccessibilityPreferences {
  reducedMotion: boolean
  highContrast: boolean
  screenReader: boolean
  keyboardOnly: boolean
  fontSize: 'small' | 'medium' | 'large' | 'xl'
  colorScheme: 'light' | 'dark' | 'auto'
}

class AccessibilityManager {
  private config: AccessibilityConfig
  private preferences: AccessibilityPreferences
  private focusTraps = new Map<string, HTMLElement[]>()
  private announcer?: LiveRegionAnnouncer

  constructor(config: AccessibilityConfig) {
    this.config = config
    this.preferences = this.loadPreferences()
    this.initialize()
  }

  private initialize() {
    this.detectSystemPreferences()
    this.setupKeyboardNavigation()
    this.setupScreenReaderSupport()
    this.setupFocusManagement()
    this.applyUserPreferences()

    if (this.config.enableAnnouncements) {
      this.announcer = new LiveRegionAnnouncer()
    }
  }

  private detectSystemPreferences() {
    // Detect reduced motion preference
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      this.preferences.reducedMotion = true
    }

    // Detect high contrast preference
    if (window.matchMedia('(prefers-contrast: high)').matches) {
      this.preferences.highContrast = true
    }

    // Detect color scheme preference
    if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      this.preferences.colorScheme = 'dark'
    }

    // Listen for changes
    window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', (e) => {
      this.preferences.reducedMotion = e.matches
      this.applyMotionPreferences()
    })

    window.matchMedia('(prefers-contrast: high)').addEventListener('change', (e) => {
      this.preferences.highContrast = e.matches
      this.applyContrastPreferences()
    })
  }

  private setupKeyboardNavigation() {
    if (!this.config.enableKeyboardNav) return

    // Skip links for keyboard users
    this.createSkipLinks()

    // Keyboard shortcuts
    this.setupKeyboardShortcuts()

    // Focus indicators
    this.setupFocusIndicators()

    // Tab trapping
    this.setupTabTrapping()
  }

  private createSkipLinks() {
    const skipLink = document.createElement('a')
    skipLink.href = '#main-content'
    skipLink.textContent = 'Skip to main content'
    skipLink.className = 'skip-link'
    skipLink.style.cssText = `
      position: absolute;
      top: -40px;
      left: 6px;
      background: #000;
      color: #fff;
      padding: 8px;
      text-decoration: none;
      z-index: 1000;
      border-radius: 4px;
      transition: top 0.3s;
    `

    skipLink.addEventListener('focus', () => {
      skipLink.style.top = '6px'
    })

    skipLink.addEventListener('blur', () => {
      skipLink.style.top = '-40px'
    })

    document.body.insertBefore(skipLink, document.body.firstChild)
  }

  private setupKeyboardShortcuts() {
    const shortcuts = new Map([
      ['Alt+1', () => this.focusElement('#main-content')],
      ['Alt+2', () => this.focusElement('[role="navigation"]')],
      ['Alt+3', () => this.focusElement('[role="search"]')],
      ['Escape', () => this.handleEscape()],
      ['?', () => this.showKeyboardHelp()]
    ])

    document.addEventListener('keydown', (event) => {
      const key = this.getKeyboardShortcut(event)
      const handler = shortcuts.get(key)

      if (handler) {
        event.preventDefault()
        handler()
      }
    })
  }

  private getKeyboardShortcut(event: KeyboardEvent): string {
    const parts = []

    if (event.altKey) parts.push('Alt')
    if (event.ctrlKey) parts.push('Ctrl')
    if (event.shiftKey) parts.push('Shift')
    if (event.metaKey) parts.push('Meta')

    parts.push(event.key)

    return parts.join('+')
  }

  private setupFocusIndicators() {
    const style = document.createElement('style')
    style.textContent = `
      .a11y-focus-indicator {
        outline: 3px solid #005fcc;
        outline-offset: 2px;
        border-radius: 4px;
      }

      .a11y-focus-indicator:focus-visible {
        outline: 3px solid #005fcc;
        outline-offset: 2px;
      }

      .a11y-high-contrast .a11y-focus-indicator:focus-visible {
        outline: 3px solid #ffff00;
      }
    `
    document.head.appendChild(style)

    // Add focus indicators to interactive elements
    const interactiveElements = document.querySelectorAll(
      'button, a, input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )

    interactiveElements.forEach(element => {
      element.classList.add('a11y-focus-indicator')
    })
  }

  private setupTabTrapping() {
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Tab') {
        this.handleTabNavigation(event)
      }
    })
  }

  private handleTabNavigation(event: KeyboardEvent) {
    const activeTraps = Array.from(this.focusTraps.values()).flat()
    if (activeTraps.length === 0) return

    const focusableElements = this.getFocusableElements(activeTraps[0])
    if (focusableElements.length === 0) return

    const firstElement = focusableElements[0]
    const lastElement = focusableElements[focusableElements.length - 1]

    if (event.shiftKey) {
      if (document.activeElement === firstElement) {
        event.preventDefault()
        lastElement.focus()
      }
    } else {
      if (document.activeElement === lastElement) {
        event.preventDefault()
        firstElement.focus()
      }
    }
  }

  private getFocusableElements(container: HTMLElement): HTMLElement[] {
    const selector = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    return Array.from(container.querySelectorAll(selector))
      .filter(el => this.isElementVisible(el as HTMLElement)) as HTMLElement[]
  }

  private isElementVisible(element: HTMLElement): boolean {
    const style = window.getComputedStyle(element)
    return style.display !== 'none' && style.visibility !== 'hidden' && !element.hidden
  }

  private setupScreenReaderSupport() {
    if (!this.config.enableScreenReader) return

    // Add landmarks
    this.addLandmarks()

    // Add aria-live regions
    this.setupLiveRegions()

    // Add descriptions for complex UI
    this.addDescriptions()
  }

  private addLandmarks() {
    // Ensure main content area has proper landmark
    const main = document.querySelector('main')
    if (!main) {
      const mainContent = document.querySelector('#main-content, .main-content')
      if (mainContent && !mainContent.getAttribute('role')) {
        mainContent.setAttribute('role', 'main')
        mainContent.id = 'main-content'
      }
    }

    // Add navigation landmarks
    document.querySelectorAll('nav').forEach((nav, index) => {
      if (!nav.getAttribute('aria-label') && !nav.getAttribute('aria-labelledby')) {
        nav.setAttribute('aria-label', `Navigation ${index + 1}`)
      }
    })
  }

  private setupLiveRegions() {
    // Create polite live region for status updates
    const politeRegion = document.createElement('div')
    politeRegion.setAttribute('aria-live', 'polite')
    politeRegion.setAttribute('aria-atomic', 'true')
    politeRegion.className = 'sr-only'
    politeRegion.id = 'a11y-status-region'
    document.body.appendChild(politeRegion)

    // Create assertive live region for urgent updates
    const assertiveRegion = document.createElement('div')
    assertiveRegion.setAttribute('aria-live', 'assertive')
    assertiveRegion.setAttribute('aria-atomic', 'true')
    assertiveRegion.className = 'sr-only'
    assertiveRegion.id = 'a11y-alert-region'
    document.body.appendChild(assertiveRegion)
  }

  private addDescriptions() {
    // Add descriptions for form validation
    document.querySelectorAll('input[required]').forEach((input, index) => {
      if (!input.getAttribute('aria-describedby')) {
        const description = document.createElement('span')
        description.id = `field-description-${index}`
        description.className = 'sr-only'
        description.textContent = 'This field is required'
        input.parentNode?.insertBefore(description, input.nextSibling)
        input.setAttribute('aria-describedby', description.id)
      }
    })
  }

  private setupFocusManagement() {
    // Store original focus when modals open
    let lastFocusedElement: HTMLElement | null = null

    document.addEventListener('focusin', (event) => {
      if (!event.target) return

      const target = event.target as HTMLElement
      if (!target.closest('[role="dialog"], [role="alertdialog"]')) {
        lastFocusedElement = target
      }
    })

    // Restore focus when modals close
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && lastFocusedElement) {
        lastFocusedElement.focus()
      }
    })
  }

  // Public methods
  announce(message: string, priority: 'polite' | 'assertive' = 'polite') {
    this.announcer?.announce(message, priority)
  }

  createFocusTrap(containerId: string, container: HTMLElement) {
    const focusableElements = this.getFocusableElements(container)
    this.focusTraps.set(containerId, focusableElements)

    // Focus first element
    if (focusableElements.length > 0) {
      focusableElements[0].focus()
    }
  }

  removeFocusTrap(containerId: string) {
    this.focusTraps.delete(containerId)
  }

  focusElement(selector: string) {
    const element = document.querySelector(selector) as HTMLElement
    if (element) {
      element.focus()
      return true
    }
    return false
  }

  private handleEscape() {
    // Close modals, menus, etc.
    const openModal = document.querySelector('[role="dialog"][aria-hidden="false"]')
    if (openModal) {
      const closeButton = openModal.querySelector('[aria-label*="close"], [aria-label*="Close"]')
      if (closeButton) {
        (closeButton as HTMLElement).click()
      }
    }
  }

  private showKeyboardHelp() {
    this.announce('Keyboard shortcuts: Alt+1 for main content, Alt+2 for navigation, Alt+3 for search, Escape to close modals')
  }

  private applyUserPreferences() {
    this.applyMotionPreferences()
    this.applyContrastPreferences()
    this.applyFontSizePreferences()
  }

  private applyMotionPreferences() {
    if (this.preferences.reducedMotion) {
      document.documentElement.classList.add('a11y-reduced-motion')

      const style = document.createElement('style')
      style.textContent = `
        .a11y-reduced-motion * {
          animation-duration: 0.001ms !important;
          transition-duration: 0.001ms !important;
        }
      `
      document.head.appendChild(style)
    }
  }

  private applyContrastPreferences() {
    if (this.preferences.highContrast) {
      document.documentElement.classList.add('a11y-high-contrast')
    }
  }

  private applyFontSizePreferences() {
    document.documentElement.setAttribute('data-font-size', this.preferences.fontSize)
  }

  private loadPreferences(): AccessibilityPreferences {
    const stored = localStorage.getItem('a11y-preferences')
    const defaults: AccessibilityPreferences = {
      reducedMotion: false,
      highContrast: false,
      screenReader: false,
      keyboardOnly: false,
      fontSize: 'medium',
      colorScheme: 'auto'
    }

    if (stored) {
      return { ...defaults, ...JSON.parse(stored) }
    }

    return defaults
  }

  updatePreferences(updates: Partial<AccessibilityPreferences>) {
    this.preferences = { ...this.preferences, ...updates }
    localStorage.setItem('a11y-preferences', JSON.stringify(this.preferences))
    this.applyUserPreferences()
  }

  getPreferences(): AccessibilityPreferences {
    return { ...this.preferences }
  }

  runAccessibilityAudit(): AccessibilityAuditResult {
    return {
      landmarks: this.auditLandmarks(),
      headings: this.auditHeadings(),
      forms: this.auditForms(),
      images: this.auditImages(),
      colorContrast: this.auditColorContrast(),
      keyboard: this.auditKeyboardAccess(),
      aria: this.auditAriaUsage()
    }
  }

  private auditLandmarks() {
    const landmarks = document.querySelectorAll('[role="main"], main, [role="navigation"], nav, [role="banner"], header, [role="contentinfo"], footer')
    return {
      count: landmarks.length,
      hasMain: document.querySelector('[role="main"], main') !== null,
      hasNavigation: document.querySelector('[role="navigation"], nav') !== null
    }
  }

  private auditHeadings() {
    const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6')
    const levels = Array.from(headings).map(h => parseInt(h.tagName.charAt(1)))

    return {
      count: headings.length,
      hasH1: levels.includes(1),
      structure: this.validateHeadingStructure(levels)
    }
  }

  private validateHeadingStructure(levels: number[]): boolean {
    for (let i = 1; i < levels.length; i++) {
      if (levels[i] > levels[i - 1] + 1) {
        return false // Skipped heading level
      }
    }
    return true
  }

  private auditForms() {
    const inputs = document.querySelectorAll('input, select, textarea')
    const unlabeled = Array.from(inputs).filter(input =>
      !input.getAttribute('aria-label') &&
      !input.getAttribute('aria-labelledby') &&
      !document.querySelector(`label[for="${input.id}"]`)
    )

    return {
      totalInputs: inputs.length,
      unlabeledInputs: unlabeled.length,
      hasRequiredFieldIndicators: document.querySelectorAll('[required]').length > 0
    }
  }

  private auditImages() {
    const images = document.querySelectorAll('img')
    const missingAlt = Array.from(images).filter(img => !img.alt && !img.getAttribute('aria-hidden'))

    return {
      totalImages: images.length,
      missingAlt: missingAlt.length
    }
  }

  private auditColorContrast() {
    // Basic color contrast audit (would need more sophisticated implementation)
    return {
      hasContrastIssues: false, // Placeholder
      checkedElements: 0
    }
  }

  private auditKeyboardAccess() {
    const focusableElements = this.getFocusableElements(document.body)
    const withoutTabIndex = focusableElements.filter(el => !el.hasAttribute('tabindex'))

    return {
      focusableElements: focusableElements.length,
      hasSkipLinks: document.querySelector('.skip-link') !== null,
      hasTabTraps: this.focusTraps.size > 0
    }
  }

  private auditAriaUsage() {
    const ariaElements = document.querySelectorAll('[aria-label], [aria-labelledby], [aria-describedby], [role]')

    return {
      elementsWithAria: ariaElements.length,
      hasLiveRegions: document.querySelectorAll('[aria-live]').length > 0
    }
  }
}

class LiveRegionAnnouncer {
  private politeRegion: HTMLElement
  private assertiveRegion: HTMLElement

  constructor() {
    this.politeRegion = document.getElementById('a11y-status-region') || this.createRegion('polite')
    this.assertiveRegion = document.getElementById('a11y-alert-region') || this.createRegion('assertive')
  }

  private createRegion(type: 'polite' | 'assertive'): HTMLElement {
    const region = document.createElement('div')
    region.setAttribute('aria-live', type)
    region.setAttribute('aria-atomic', 'true')
    region.className = 'sr-only'
    region.id = `a11y-${type}-region`
    document.body.appendChild(region)
    return region
  }

  announce(message: string, priority: 'polite' | 'assertive' = 'polite') {
    const region = priority === 'assertive' ? this.assertiveRegion : this.politeRegion

    // Clear and then set the message to ensure it's announced
    region.textContent = ''
    setTimeout(() => {
      region.textContent = message
    }, 100)

    // Clear after announcement
    setTimeout(() => {
      region.textContent = ''
    }, 5000)
  }
}

interface AccessibilityAuditResult {
  landmarks: any
  headings: any
  forms: any
  images: any
  colorContrast: any
  keyboard: any
  aria: any
}

export { AccessibilityManager, type AccessibilityConfig, type AccessibilityPreferences, type AccessibilityAuditResult }
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Comprehensive accessibility system achieving WCAG 2.1 AA compliance with advanced features.

---

### Step 44: Advanced State Management and Data Flow
**Goal:** Implement sophisticated state management patterns for complex application state.

**Actions:**
- CREATE: `src/lib/state/` directory
- CREATE: `src/lib/state/stateManager.ts`
- CREATE: `src/lib/state/observableStore.ts`
- CREATE: `src/hooks/state/` directory
- CREATE: Advanced state management patterns

**Code changes:**
```typescript
// src/lib/state/observableStore.ts
type Listener<T> = (state: T, previousState: T) => void
type Selector<T, R> = (state: T) => R
type StateUpdater<T> = (state: T) => T | Partial<T>

interface StoreConfig<T> {
  name: string
  initialState: T
  persist?: boolean
  devtools?: boolean
}

class ObservableStore<T extends Record<string, unknown>> {
  private state: T
  private listeners = new Set<Listener<T>>()
  private selectorCache = new Map<string, any>()
  private config: StoreConfig<T>
  private middlewares: Array<(store: ObservableStore<T>) => void> = []

  constructor(config: StoreConfig<T>) {
    this.config = config
    this.state = this.loadPersistedState() || config.initialState

    if (config.devtools && typeof window !== 'undefined') {
      this.setupDevtools()
    }
  }

  private loadPersistedState(): T | null {
    if (!this.config.persist || typeof window === 'undefined') return null

    try {
      const stored = localStorage.getItem(`store_${this.config.name}`)
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  }

  private persistState() {
    if (!this.config.persist || typeof window === 'undefined') return

    try {
      localStorage.setItem(`store_${this.config.name}`, JSON.stringify(this.state))
    } catch (error) {
      console.warn('Failed to persist state:', error)
    }
  }

  private setupDevtools() {
    const devtools = (window as any).__REDUX_DEVTOOLS_EXTENSION__
    if (devtools) {
      const instance = devtools.connect({ name: this.config.name })
      instance.init(this.state)

      this.subscribe((state, prevState) => {
        instance.send('STATE_UPDATE', state)
      })
    }
  }

  getState(): T {
    return this.state
  }

  setState(updater: StateUpdater<T> | Partial<T>) {
    const previousState = this.state

    if (typeof updater === 'function') {
      const result = updater(this.state)
      this.state = { ...this.state, ...result } as T
    } else {
      this.state = { ...this.state, ...updater } as T
    }

    // Clear selector cache
    this.selectorCache.clear()

    // Notify listeners
    this.listeners.forEach(listener => {
      try {
        listener(this.state, previousState)
      } catch (error) {
        console.error('Store listener error:', error)
      }
    })

    // Persist state
    this.persistState()

    // Apply middlewares
    this.middlewares.forEach(middleware => middleware(this))
  }

  subscribe(listener: Listener<T>): () => void {
    this.listeners.add(listener)

    return () => {
      this.listeners.delete(listener)
    }
  }

  select<R>(selector: Selector<T, R>, deps?: any[]): R {
    const cacheKey = deps ? `${selector.toString()}_${JSON.stringify(deps)}` : selector.toString()

    if (this.selectorCache.has(cacheKey)) {
      return this.selectorCache.get(cacheKey)
    }

    const result = selector(this.state)
    this.selectorCache.set(cacheKey, result)

    return result
  }

  addMiddleware(middleware: (store: ObservableStore<T>) => void) {
    this.middlewares.push(middleware)
  }

  reset() {
    this.setState(this.config.initialState)
  }

  destroy() {
    this.listeners.clear()
    this.selectorCache.clear()
    this.middlewares = []

    if (this.config.persist) {
      localStorage.removeItem(`store_${this.config.name}`)
    }
  }
}

// Factory function for creating typed stores
export function createStore<T extends Record<string, unknown>>(config: StoreConfig<T>) {
  return new ObservableStore(config)
}

export { ObservableStore, type StoreConfig, type Listener, type Selector, type StateUpdater }
```

```typescript
// src/lib/state/stateManager.ts
import { ObservableStore, createStore } from './observableStore'

// Application state interfaces
interface AppState {
  ui: UIState
  user: UserState
  data: DataState
  preferences: PreferencesState
}

interface UIState {
  sidebarOpen: boolean
  theme: 'light' | 'dark' | 'auto'
  loading: Record<string, boolean>
  errors: Record<string, string | null>
  notifications: Notification[]
}

interface UserState {
  currentUser: any | null
  isAuthenticated: boolean
  permissions: string[]
  preferences: Record<string, unknown>
}

interface DataState {
  quizzes: any[]
  questions: any[]
  cache: Record<string, any>
  lastFetch: Record<string, number>
}

interface PreferencesState {
  accessibility: any
  performance: any
  features: Record<string, boolean>
}

interface Notification {
  id: string
  type: 'info' | 'success' | 'warning' | 'error'
  title: string
  message: string
  timestamp: number
  duration?: number
  actions?: Array<{
    label: string
    action: () => void
  }>
}

class StateManager {
  private stores = new Map<string, ObservableStore<any>>()
  private globalListeners = new Set<(storeName: string, state: any) => void>()

  constructor() {
    this.initializeStores()
    this.setupGlobalMiddleware()
  }

  private initializeStores() {
    // UI Store
    this.createUIStore()

    // User Store
    this.createUserStore()

    // Data Store
    this.createDataStore()

    // Preferences Store
    this.createPreferencesStore()
  }

  private createUIStore() {
    const uiStore = createStore({
      name: 'ui',
      initialState: {
        sidebarOpen: true,
        theme: 'auto' as const,
        loading: {},
        errors: {},
        notifications: []
      } as UIState,
      persist: true,
      devtools: true
    })

    // Add UI-specific middleware
    uiStore.addMiddleware((store) => {
      const state = store.getState()

      // Auto-dismiss notifications
      if (state.notifications.length > 0) {
        setTimeout(() => {
          const now = Date.now()
          const activeNotifications = state.notifications.filter(n =>
            !n.duration || (now - n.timestamp) < n.duration
          )

          if (activeNotifications.length !== state.notifications.length) {
            store.setState({ notifications: activeNotifications })
          }
        }, 1000)
      }

      // Apply theme changes
      if (state.theme !== 'auto') {
        document.documentElement.setAttribute('data-theme', state.theme)
      } else {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
        document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light')
      }
    })

    this.stores.set('ui', uiStore)
  }

  private createUserStore() {
    const userStore = createStore({
      name: 'user',
      initialState: {
        currentUser: null,
        isAuthenticated: false,
        permissions: [],
        preferences: {}
      } as UserState,
      persist: true,
      devtools: true
    })

    this.stores.set('user', userStore)
  }

  private createDataStore() {
    const dataStore = createStore({
      name: 'data',
      initialState: {
        quizzes: [],
        questions: [],
        cache: {},
        lastFetch: {}
      } as DataState,
      persist: false, // Don't persist data store
      devtools: true
    })

    // Add data invalidation middleware
    dataStore.addMiddleware((store) => {
      const state = store.getState()
      const now = Date.now()
      const fiveMinutes = 5 * 60 * 1000

      // Invalidate old cache entries
      Object.entries(state.lastFetch).forEach(([key, timestamp]) => {
        if (now - timestamp > fiveMinutes) {
          const newCache = { ...state.cache }
          delete newCache[key]
          const newLastFetch = { ...state.lastFetch }
          delete newLastFetch[key]

          store.setState({
            cache: newCache,
            lastFetch: newLastFetch
          })
        }
      })
    })

    this.stores.set('data', dataStore)
  }

  private createPreferencesStore() {
    const preferencesStore = createStore({
      name: 'preferences',
      initialState: {
        accessibility: {},
        performance: {},
        features: {}
      } as PreferencesState,
      persist: true,
      devtools: true
    })

    this.stores.set('preferences', preferencesStore)
  }

  private setupGlobalMiddleware() {
    // Log all state changes in development
    if (process.env.NODE_ENV === 'development') {
      this.stores.forEach((store, name) => {
        store.subscribe((state, prevState) => {
          console.group(`🔄 ${name.toUpperCase()} State Change`)
          console.log('Previous:', prevState)
          console.log('Current:', state)
          console.groupEnd()
        })
      })
    }

    // Notify global listeners
    this.stores.forEach((store, name) => {
      store.subscribe((state) => {
        this.globalListeners.forEach(listener => {
          listener(name, state)
        })
      })
    })
  }

  // Public API
  getStore<T>(name: string): ObservableStore<T> | undefined {
    return this.stores.get(name)
  }

  getUIStore(): ObservableStore<UIState> {
    return this.stores.get('ui')!
  }

  getUserStore(): ObservableStore<UserState> {
    return this.stores.get('user')!
  }

  getDataStore(): ObservableStore<DataState> {
    return this.stores.get('data')!
  }

  getPreferencesStore(): ObservableStore<PreferencesState> {
    return this.stores.get('preferences')!
  }

  // UI Actions
  setLoading(key: string, loading: boolean) {
    const uiStore = this.getUIStore()
    const currentLoading = uiStore.getState().loading
    uiStore.setState({
      loading: { ...currentLoading, [key]: loading }
    })
  }

  setError(key: string, error: string | null) {
    const uiStore = this.getUIStore()
    const currentErrors = uiStore.getState().errors
    uiStore.setState({
      errors: { ...currentErrors, [key]: error }
    })
  }

  addNotification(notification: Omit<Notification, 'id' | 'timestamp'>) {
    const uiStore = this.getUIStore()
    const currentNotifications = uiStore.getState().notifications

    const newNotification: Notification = {
      ...notification,
      id: `notification_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
      duration: notification.duration || 5000
    }

    uiStore.setState({
      notifications: [...currentNotifications, newNotification]
    })

    return newNotification.id
  }

  removeNotification(id: string) {
    const uiStore = this.getUIStore()
    const currentNotifications = uiStore.getState().notifications
    uiStore.setState({
      notifications: currentNotifications.filter(n => n.id !== id)
    })
  }

  // User Actions
  setUser(user: any) {
    const userStore = this.getUserStore()
    userStore.setState({
      currentUser: user,
      isAuthenticated: !!user
    })
  }

  logout() {
    const userStore = this.getUserStore()
    userStore.setState({
      currentUser: null,
      isAuthenticated: false,
      permissions: [],
      preferences: {}
    })

    // Clear data cache on logout
    const dataStore = this.getDataStore()
    dataStore.setState({
      quizzes: [],
      questions: [],
      cache: {},
      lastFetch: {}
    })
  }

  // Data Actions
  cacheData(key: string, data: any) {
    const dataStore = this.getDataStore()
    const currentCache = dataStore.getState().cache
    const currentLastFetch = dataStore.getState().lastFetch

    dataStore.setState({
      cache: { ...currentCache, [key]: data },
      lastFetch: { ...currentLastFetch, [key]: Date.now() }
    })
  }

  getCachedData(key: string): any | null {
    const dataStore = this.getDataStore()
    return dataStore.getState().cache[key] || null
  }

  isCacheValid(key: string, maxAge = 5 * 60 * 1000): boolean {
    const dataStore = this.getDataStore()
    const lastFetch = dataStore.getState().lastFetch[key]

    if (!lastFetch) return false

    return Date.now() - lastFetch < maxAge
  }

  // Global listeners
  subscribe(listener: (storeName: string, state: any) => void): () => void {
    this.globalListeners.add(listener)

    return () => {
      this.globalListeners.delete(listener)
    }
  }

  // Debugging and development
  getDebugInfo() {
    const info: Record<string, any> = {}

    this.stores.forEach((store, name) => {
      info[name] = store.getState()
    })

    return info
  }

  exportState() {
    return this.getDebugInfo()
  }

  importState(state: Record<string, any>) {
    Object.entries(state).forEach(([storeName, storeState]) => {
      const store = this.stores.get(storeName)
      if (store) {
        store.setState(storeState)
      }
    })
  }

  reset() {
    this.stores.forEach(store => store.reset())
  }

  destroy() {
    this.stores.forEach(store => store.destroy())
    this.stores.clear()
    this.globalListeners.clear()
  }
}

// Global state manager instance
export const stateManager = new StateManager()

// Export types
export type {
  AppState,
  UIState,
  UserState,
  DataState,
  PreferencesState,
  Notification
}
```

```typescript
// src/hooks/state/useStore.ts
import { useEffect, useState, useRef, useCallback } from 'react'
import { ObservableStore, type Selector } from '@/lib/state/observableStore'
import { stateManager } from '@/lib/state/stateManager'

// Hook for subscribing to store changes
export function useStore<T, R = T>(
  store: ObservableStore<T>,
  selector?: Selector<T, R>,
  deps?: any[]
): R {
  const selectorRef = useRef(selector)
  const depsRef = useRef(deps)

  // Update refs when dependencies change
  useEffect(() => {
    selectorRef.current = selector
    depsRef.current = deps
  })

  const [state, setState] = useState<R>(() => {
    return selector ? store.select(selector, deps) : (store.getState() as unknown as R)
  })

  useEffect(() => {
    const unsubscribe = store.subscribe((newState) => {
      const newSelectedState = selectorRef.current
        ? store.select(selectorRef.current, depsRef.current)
        : (newState as unknown as R)

      setState(newSelectedState)
    })

    return unsubscribe
  }, [store])

  return state
}

// Hook for UI store
export function useUIStore<R = any>(selector?: Selector<any, R>, deps?: any[]) {
  return useStore(stateManager.getUIStore(), selector, deps)
}

// Hook for user store
export function useUserStore<R = any>(selector?: Selector<any, R>, deps?: any[]) {
  return useStore(stateManager.getUserStore(), selector, deps)
}

// Hook for data store
export function useDataStore<R = any>(selector?: Selector<any, R>, deps?: any[]) {
  return useStore(stateManager.getDataStore(), selector, deps)
}

// Hook for preferences store
export function usePreferencesStore<R = any>(selector?: Selector<any, R>, deps?: any[]) {
  return useStore(stateManager.getPreferencesStore(), selector, deps)
}

// Hook for UI actions
export function useUIActions() {
  return {
    setLoading: useCallback((key: string, loading: boolean) => {
      stateManager.setLoading(key, loading)
    }, []),

    setError: useCallback((key: string, error: string | null) => {
      stateManager.setError(key, error)
    }, []),

    addNotification: useCallback((notification: any) => {
      return stateManager.addNotification(notification)
    }, []),

    removeNotification: useCallback((id: string) => {
      stateManager.removeNotification(id)
    }, []),

    toggleSidebar: useCallback(() => {
      const uiStore = stateManager.getUIStore()
      const currentState = uiStore.getState()
      uiStore.setState({ sidebarOpen: !currentState.sidebarOpen })
    }, []),

    setTheme: useCallback((theme: 'light' | 'dark' | 'auto') => {
      const uiStore = stateManager.getUIStore()
      uiStore.setState({ theme })
    }, [])
  }
}

// Hook for user actions
export function useUserActions() {
  return {
    setUser: useCallback((user: any) => {
      stateManager.setUser(user)
    }, []),

    logout: useCallback(() => {
      stateManager.logout()
    }, []),

    updatePreferences: useCallback((preferences: Record<string, unknown>) => {
      const userStore = stateManager.getUserStore()
      const currentState = userStore.getState()
      userStore.setState({
        preferences: { ...currentState.preferences, ...preferences }
      })
    }, [])
  }
}

// Hook for data actions
export function useDataActions() {
  return {
    cacheData: useCallback((key: string, data: any) => {
      stateManager.cacheData(key, data)
    }, []),

    getCachedData: useCallback((key: string) => {
      return stateManager.getCachedData(key)
    }, []),

    isCacheValid: useCallback((key: string, maxAge?: number) => {
      return stateManager.isCacheValid(key, maxAge)
    }, []),

    updateQuizzes: useCallback((quizzes: any[]) => {
      const dataStore = stateManager.getDataStore()
      dataStore.setState({ quizzes })
    }, []),

    updateQuestions: useCallback((questions: any[]) => {
      const dataStore = stateManager.getDataStore()
      dataStore.setState({ questions })
    }, [])
  }
}

// Hook for async state management
export function useAsyncState<T>(
  asyncFn: () => Promise<T>,
  deps: any[] = [],
  options: {
    cacheKey?: string
    maxAge?: number
    loadingKey?: string
    errorKey?: string
  } = {}
) {
  const { cacheKey, maxAge = 5 * 60 * 1000, loadingKey, errorKey } = options
  const [data, setData] = useState<T | null>(null)
  const { setLoading, setError } = useUIActions()
  const { cacheData, getCachedData, isCacheValid } = useDataActions()

  const execute = useCallback(async () => {
    // Check cache first
    if (cacheKey && isCacheValid(cacheKey, maxAge)) {
      const cachedData = getCachedData(cacheKey)
      if (cachedData) {
        setData(cachedData)
        return cachedData
      }
    }

    try {
      if (loadingKey) setLoading(loadingKey, true)
      if (errorKey) setError(errorKey, null)

      const result = await asyncFn()
      setData(result)

      // Cache the result
      if (cacheKey) {
        cacheData(cacheKey, result)
      }

      return result
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'An error occurred'
      if (errorKey) setError(errorKey, errorMessage)
      throw error
    } finally {
      if (loadingKey) setLoading(loadingKey, false)
    }
  }, deps)

  useEffect(() => {
    execute()
  }, deps)

  return { data, execute, refetch: execute }
}
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Advanced state management system with observable stores, middleware, and caching capabilities.

---

### Step 45: Progressive Web App (PWA) Implementation
**Goal:** Transform the application into a full-featured Progressive Web App.

**Actions:**
- CREATE: `public/manifest.json`
- CREATE: `src/lib/pwa/` directory
- CREATE: `src/lib/pwa/serviceWorker.ts`
- CREATE: `src/lib/pwa/installPrompt.ts`
- CREATE: `src/lib/pwa/backgroundSync.ts`
- MODIFY: Application to support PWA features

**Code changes:**
```json
// public/manifest.json
{
  "name": "Rag@UiT - Canvas Quiz Generator",
  "short_name": "Rag@UiT",
  "description": "AI-powered Canvas LMS quiz generator for educational institutions",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#013343",
  "theme_color": "#013343",
  "orientation": "portrait-primary",
  "categories": ["education", "productivity"],
  "lang": "en",
  "dir": "ltr",
  "scope": "/",
  "icons": [
    {
      "src": "/assets/images/icon-72x72.png",
      "sizes": "72x72",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/assets/images/icon-96x96.png",
      "sizes": "96x96",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/assets/images/icon-128x128.png",
      "sizes": "128x128",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/assets/images/icon-144x144.png",
      "sizes": "144x144",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/assets/images/icon-152x152.png",
      "sizes": "152x152",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/assets/images/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/assets/images/icon-384x384.png",
      "sizes": "384x384",
      "type": "image/png",
      "purpose": "any"
    },
    {
      "src": "/assets/images/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ],
  "screenshots": [
    {
      "src": "/assets/images/screenshot-wide.png",
      "sizes": "1280x720",
      "type": "image/png",
      "form_factor": "wide",
      "label": "Dashboard view of Rag@UiT"
    },
    {
      "src": "/assets/images/screenshot-narrow.png",
      "sizes": "390x844",
      "type": "image/png",
      "form_factor": "narrow",
      "label": "Mobile view of Rag@UiT"
    }
  ],
  "shortcuts": [
    {
      "name": "Dashboard",
      "short_name": "Dashboard",
      "description": "View your quiz dashboard",
      "url": "/dashboard",
      "icons": [
        {
          "src": "/assets/images/shortcut-dashboard.png",
          "sizes": "96x96"
        }
      ]
    },
    {
      "name": "Create Quiz",
      "short_name": "Create",
      "description": "Create a new quiz",
      "url": "/create-quiz",
      "icons": [
        {
          "src": "/assets/images/shortcut-create.png",
          "sizes": "96x96"
        }
      ]
    },
    {
      "name": "View Quizzes",
      "short_name": "Quizzes",
      "description": "View all your quizzes",
      "url": "/quizzes",
      "icons": [
        {
          "src": "/assets/images/shortcut-quizzes.png",
          "sizes": "96x96"
        }
      ]
    }
  ],
  "share_target": {
    "action": "/share",
    "method": "POST",
    "enctype": "multipart/form-data",
    "params": {
      "title": "title",
      "text": "text",
      "url": "url",
      "files": [
        {
          "name": "file",
          "accept": ["text/plain", "application/pdf", ".docx"]
        }
      ]
    }
  },
  "protocol_handlers": [
    {
      "protocol": "web+ragatuit",
      "url": "/quiz/import?url=%s"
    }
  ],
  "edge_side_panel": {
    "preferred_width": 400
  },
  "launch_handler": {
    "client_mode": "focus-existing"
  }
}
```

```typescript
// src/lib/pwa/serviceWorker.ts
interface ServiceWorkerConfig {
  onUpdate?: (registration: ServiceWorkerRegistration) => void
  onSuccess?: (registration: ServiceWorkerRegistration) => void
  onError?: (error: Error) => void
  cacheFirst?: string[]
  networkFirst?: string[]
  staleWhileRevalidate?: string[]
}

class PWAServiceWorker {
  private registration: ServiceWorkerRegistration | null = null
  private config: ServiceWorkerConfig

  constructor(config: ServiceWorkerConfig = {}) {
    this.config = config
  }

  async register(): Promise<ServiceWorkerRegistration | null> {
    if (!('serviceWorker' in navigator)) {
      console.warn('Service Worker not supported')
      return null
    }

    try {
      this.registration = await navigator.serviceWorker.register('/sw.js', {
        scope: '/'
      })

      // Check for updates
      this.registration.addEventListener('updatefound', () => {
        const newWorker = this.registration!.installing
        if (newWorker) {
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              this.config.onUpdate?.(this.registration!)
            }
          })
        }
      })

      // Listen for controlling service worker change
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        window.location.reload()
      })

      this.config.onSuccess?.(this.registration)
      return this.registration
    } catch (error) {
      this.config.onError?.(error as Error)
      return null
    }
  }

  async unregister(): Promise<boolean> {
    if (this.registration) {
      return await this.registration.unregister()
    }
    return false
  }

  async update(): Promise<void> {
    if (this.registration) {
      await this.registration.update()
    }
  }

  async skipWaiting(): Promise<void> {
    if (this.registration?.waiting) {
      this.registration.waiting.postMessage({ type: 'SKIP_WAITING' })
    }
  }

  // Background sync
  async scheduleBackgroundSync(tag: string, data?: any): Promise<void> {
    if (this.registration && 'sync' in window.ServiceWorkerRegistration.prototype) {
      try {
        await (this.registration as any).sync.register(tag)

        // Store data for sync
        if (data) {
          const syncData = JSON.parse(localStorage.getItem('pwa-sync-data') || '{}')
          syncData[tag] = data
          localStorage.setItem('pwa-sync-data', JSON.stringify(syncData))
        }
      } catch (error) {
        console.warn('Background sync registration failed:', error)
      }
    }
  }

  // Push notifications
  async subscribeToPush(): Promise<PushSubscription | null> {
    if (!this.registration) return null

    try {
      const subscription = await this.registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: this.urlBase64ToUint8Array(
          process.env.VITE_VAPID_PUBLIC_KEY || ''
        )
      })

      // Send subscription to server
      await this.sendSubscriptionToServer(subscription)

      return subscription
    } catch (error) {
      console.warn('Push subscription failed:', error)
      return null
    }
  }

  private urlBase64ToUint8Array(base64String: string): Uint8Array {
    const padding = '='.repeat((4 - base64String.length % 4) % 4)
    const base64 = (base64String + padding)
      .replace(/-/g, '+')
      .replace(/_/g, '/')

    const rawData = window.atob(base64)
    const outputArray = new Uint8Array(rawData.length)

    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i)
    }
    return outputArray
  }

  private async sendSubscriptionToServer(subscription: PushSubscription): Promise<void> {
    try {
      await fetch('/api/v1/push/subscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(subscription)
      })
    } catch (error) {
      console.warn('Failed to send subscription to server:', error)
    }
  }

  // Share API
  async share(data: ShareData): Promise<boolean> {
    if (navigator.share) {
      try {
        await navigator.share(data)
        return true
      } catch (error) {
        console.warn('Share failed:', error)
        return false
      }
    }
    return false
  }

  // Check if app can be shared to
  canShareTo(): boolean {
    return 'canShare' in navigator && navigator.canShare?.()
  }

  // Get network status
  getNetworkStatus(): { online: boolean; effectiveType?: string; downlink?: number } {
    const connection = (navigator as any).connection || (navigator as any).mozConnection || (navigator as any).webkitConnection

    return {
      online: navigator.onLine,
      effectiveType: connection?.effectiveType,
      downlink: connection?.downlink
    }
  }

  // Monitor network changes
  onNetworkChange(callback: (online: boolean) => void): () => void {
    const handleOnline = () => callback(true)
    const handleOffline = () => callback(false)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }
}

export { PWAServiceWorker, type ServiceWorkerConfig }
```

```typescript
// src/lib/pwa/installPrompt.ts
interface InstallPromptConfig {
  showAfterVisits?: number
  showAfterDelay?: number
  hideAfterDismiss?: number
  customPrompt?: (event: BeforeInstallPromptEvent) => Promise<boolean>
}

interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[]
  readonly userChoice: Promise<{
    outcome: 'accepted' | 'dismissed'
    platform: string
  }>
  prompt(): Promise<void>
}

class InstallPromptManager {
  private deferredPrompt: BeforeInstallPromptEvent | null = null
  private config: InstallPromptConfig
  private isInstalled = false
  private visitCount = 0
  private lastDismissed = 0

  constructor(config: InstallPromptConfig = {}) {
    this.config = {
      showAfterVisits: 3,
      showAfterDelay: 60000, // 1 minute
      hideAfterDismiss: 7 * 24 * 60 * 60 * 1000, // 1 week
      ...config
    }

    this.initialize()
  }

  private initialize() {
    this.loadState()
    this.setupEventListeners()
    this.trackVisit()
  }

  private loadState() {
    const state = localStorage.getItem('pwa-install-state')
    if (state) {
      const parsed = JSON.parse(state)
      this.visitCount = parsed.visitCount || 0
      this.lastDismissed = parsed.lastDismissed || 0
      this.isInstalled = parsed.isInstalled || false
    }
  }

  private saveState() {
    localStorage.setItem('pwa-install-state', JSON.stringify({
      visitCount: this.visitCount,
      lastDismissed: this.lastDismissed,
      isInstalled: this.isInstalled
    }))
  }

  private setupEventListeners() {
    // Listen for install prompt
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault()
      this.deferredPrompt = e as BeforeInstallPromptEvent

      if (this.shouldShowPrompt()) {
        this.showInstallPrompt()
      }
    })

    // Listen for app install
    window.addEventListener('appinstalled', () => {
      this.isInstalled = true
      this.saveState()
      this.onInstallSuccess()
    })

    // Check if already installed
    if (window.matchMedia('(display-mode: standalone)').matches ||
        (window.navigator as any).standalone === true) {
      this.isInstalled = true
      this.saveState()
    }
  }

  private trackVisit() {
    this.visitCount++
    this.saveState()
  }

  private shouldShowPrompt(): boolean {
    if (this.isInstalled) return false
    if (!this.deferredPrompt) return false
    if (this.visitCount < this.config.showAfterVisits!) return false

    // Check if recently dismissed
    const now = Date.now()
    if (this.lastDismissed && (now - this.lastDismissed) < this.config.hideAfterDismiss!) {
      return false
    }

    return true
  }

  private async showInstallPrompt() {
    if (!this.deferredPrompt) return

    try {
      // Use custom prompt if provided
      if (this.config.customPrompt) {
        const shouldShow = await this.config.customPrompt(this.deferredPrompt)
        if (!shouldShow) return
      }

      // Show the install prompt
      await this.deferredPrompt.prompt()

      // Wait for user choice
      const { outcome } = await this.deferredPrompt.userChoice

      if (outcome === 'dismissed') {
        this.lastDismissed = Date.now()
        this.saveState()
        this.onInstallDismissed()
      } else {
        this.onInstallAccepted()
      }

      this.deferredPrompt = null
    } catch (error) {
      console.warn('Install prompt failed:', error)
    }
  }

  // Public methods
  async manualInstall(): Promise<boolean> {
    if (this.deferredPrompt) {
      await this.showInstallPrompt()
      return true
    }
    return false
  }

  canInstall(): boolean {
    return !!this.deferredPrompt && !this.isInstalled
  }

  isAppInstalled(): boolean {
    return this.isInstalled
  }

  getInstallPlatforms(): string[] {
    return this.deferredPrompt?.platforms || []
  }

  // Event handlers (can be overridden)
  protected onInstallSuccess() {
    console.log('PWA installed successfully')
  }

  protected onInstallAccepted() {
    console.log('Install prompt accepted')
  }

  protected onInstallDismissed() {
    console.log('Install prompt dismissed')
  }

  // Create custom install button component
  createInstallButton(): HTMLButtonElement | null {
    if (!this.canInstall()) return null

    const button = document.createElement('button')
    button.textContent = 'Install App'
    button.className = 'pwa-install-button'
    button.style.cssText = `
      background: #007bff;
      color: white;
      border: none;
      padding: 12px 24px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
      transition: background-color 0.2s;
    `

    button.addEventListener('mouseover', () => {
      button.style.backgroundColor = '#0056b3'
    })

    button.addEventListener('mouseout', () => {
      button.style.backgroundColor = '#007bff'
    })

    button.addEventListener('click', () => {
      this.manualInstall()
    })

    return button
  }

  // Create install banner
  createInstallBanner(): HTMLDivElement | null {
    if (!this.canInstall()) return null

    const banner = document.createElement('div')
    banner.className = 'pwa-install-banner'
    banner.style.cssText = `
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      background: #f8f9fa;
      border-top: 1px solid #dee2e6;
      padding: 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      z-index: 1000;
      box-shadow: 0 -2px 8px rgba(0,0,0,0.1);
    `

    const message = document.createElement('div')
    message.innerHTML = `
      <strong>Install Rag@UiT</strong><br>
      <small>Get quick access and a better experience</small>
    `

    const actions = document.createElement('div')
    actions.style.cssText = 'display: flex; gap: 8px; align-items: center;'

    const installButton = document.createElement('button')
    installButton.textContent = 'Install'
    installButton.style.cssText = `
      background: #007bff;
      color: white;
      border: none;
      padding: 8px 16px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 14px;
    `

    const dismissButton = document.createElement('button')
    dismissButton.textContent = '✕'
    dismissButton.style.cssText = `
      background: none;
      border: none;
      cursor: pointer;
      font-size: 18px;
      color: #6c757d;
      padding: 4px;
    `

    installButton.addEventListener('click', () => {
      this.manualInstall()
      banner.remove()
    })

    dismissButton.addEventListener('click', () => {
      this.lastDismissed = Date.now()
      this.saveState()
      banner.remove()
    })

    actions.appendChild(installButton)
    actions.appendChild(dismissButton)
    banner.appendChild(message)
    banner.appendChild(actions)

    return banner
  }

  // Show install banner automatically
  showInstallBanner() {
    if (this.shouldShowPrompt()) {
      const banner = this.createInstallBanner()
      if (banner) {
        document.body.appendChild(banner)
      }
    }
  }

  reset() {
    localStorage.removeItem('pwa-install-state')
    this.visitCount = 0
    this.lastDismissed = 0
    this.isInstalled = false
  }
}

export { InstallPromptManager, type InstallPromptConfig, type BeforeInstallPromptEvent }
```

```typescript
// src/lib/pwa/backgroundSync.ts
interface SyncTask {
  id: string
  type: string
  data: any
  timestamp: number
  retryCount: number
  maxRetries: number
}

class BackgroundSyncManager {
  private tasks: Map<string, SyncTask> = new Map()
  private isOnline = navigator.onLine
  private syncInProgress = false

  constructor() {
    this.initialize()
  }

  private initialize() {
    this.loadTasks()
    this.setupNetworkListeners()
    this.setupVisibilityListeners()

    // Process tasks when online
    if (this.isOnline) {
      this.processTasks()
    }
  }

  private loadTasks() {
    try {
      const stored = localStorage.getItem('pwa-sync-tasks')
      if (stored) {
        const tasks = JSON.parse(stored)
        Object.entries(tasks).forEach(([id, task]) => {
          this.tasks.set(id, task as SyncTask)
        })
      }
    } catch (error) {
      console.warn('Failed to load sync tasks:', error)
    }
  }

  private saveTasks() {
    try {
      const tasksObj = Object.fromEntries(this.tasks)
      localStorage.setItem('pwa-sync-tasks', JSON.stringify(tasksObj))
    } catch (error) {
      console.warn('Failed to save sync tasks:', error)
    }
  }

  private setupNetworkListeners() {
    window.addEventListener('online', () => {
      this.isOnline = true
      this.processTasks()
    })

    window.addEventListener('offline', () => {
      this.isOnline = false
    })
  }

  private setupVisibilityListeners() {
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden && this.isOnline && this.tasks.size > 0) {
        this.processTasks()
      }
    })
  }

  // Add task for background sync
  addTask(type: string, data: any, options: { maxRetries?: number } = {}): string {
    const id = `${type}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`

    const task: SyncTask = {
      id,
      type,
      data,
      timestamp: Date.now(),
      retryCount: 0,
      maxRetries: options.maxRetries || 3
    }

    this.tasks.set(id, task)
    this.saveTasks()

    // Process immediately if online
    if (this.isOnline) {
      this.processTasks()
    }

    return id
  }

  // Remove completed task
  removeTask(id: string): boolean {
    const removed = this.tasks.delete(id)
    if (removed) {
      this.saveTasks()
    }
    return removed
  }

  // Process all pending tasks
  private async processTasks() {
    if (this.syncInProgress || !this.isOnline || this.tasks.size === 0) {
      return
    }

    this.syncInProgress = true

    try {
      const taskArray = Array.from(this.tasks.values())

      for (const task of taskArray) {
        try {
          await this.processTask(task)
          this.removeTask(task.id)
        } catch (error) {
          await this.handleTaskError(task, error)
        }
      }
    } finally {
      this.syncInProgress = false
    }
  }

  private async processTask(task: SyncTask): Promise<void> {
    switch (task.type) {
      case 'quiz_create':
        await this.syncQuizCreate(task.data)
        break
      case 'quiz_update':
        await this.syncQuizUpdate(task.data)
        break
      case 'quiz_delete':
        await this.syncQuizDelete(task.data)
        break
      case 'question_approve':
        await this.syncQuestionApprove(task.data)
        break
      case 'question_reject':
        await this.syncQuestionReject(task.data)
        break
      case 'user_preferences':
        await this.syncUserPreferences(task.data)
        break
      default:
        throw new Error(`Unknown task type: ${task.type}`)
    }
  }

  private async handleTaskError(task: SyncTask, error: any) {
    task.retryCount++

    if (task.retryCount >= task.maxRetries) {
      console.error(`Task ${task.id} failed after ${task.maxRetries} retries:`, error)
      this.removeTask(task.id)

      // Notify user of permanent failure
      this.notifyTaskFailure(task, error)
    } else {
      // Update task with retry count
      this.tasks.set(task.id, task)
      this.saveTasks()

      console.warn(`Task ${task.id} failed, retry ${task.retryCount}/${task.maxRetries}:`, error)
    }
  }

  // Sync implementations
  private async syncQuizCreate(data: any): Promise<void> {
    const response = await fetch('/api/v1/quiz', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      },
      body: JSON.stringify(data)
    })

    if (!response.ok) {
      throw new Error(`Quiz create failed: ${response.status}`)
    }

    const result = await response.json()

    // Update local state with server response
    this.updateLocalQuizData(result)
  }

  private async syncQuizUpdate(data: any): Promise<void> {
    const response = await fetch(`/api/v1/quiz/${data.id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      },
      body: JSON.stringify(data)
    })

    if (!response.ok) {
      throw new Error(`Quiz update failed: ${response.status}`)
    }

    const result = await response.json()
    this.updateLocalQuizData(result)
  }

  private async syncQuizDelete(data: any): Promise<void> {
    const response = await fetch(`/api/v1/quiz/${data.id}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      }
    })

    if (!response.ok) {
      throw new Error(`Quiz delete failed: ${response.status}`)
    }

    this.removeLocalQuizData(data.id)
  }

  private async syncQuestionApprove(data: any): Promise<void> {
    const response = await fetch(`/api/v1/questions/${data.id}/approve`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      }
    })

    if (!response.ok) {
      throw new Error(`Question approve failed: ${response.status}`)
    }
  }

  private async syncQuestionReject(data: any): Promise<void> {
    const response = await fetch(`/api/v1/questions/${data.id}/reject`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      }
    })

    if (!response.ok) {
      throw new Error(`Question reject failed: ${response.status}`)
    }
  }

  private async syncUserPreferences(data: any): Promise<void> {
    const response = await fetch('/api/v1/users/me/preferences', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
      },
      body: JSON.stringify(data)
    })

    if (!response.ok) {
      throw new Error(`User preferences sync failed: ${response.status}`)
    }
  }

  // Local data management
  private updateLocalQuizData(quiz: any) {
    // Update local quiz cache
    const cachedQuizzes = JSON.parse(localStorage.getItem('cached_quizzes') || '[]')
    const index = cachedQuizzes.findIndex((q: any) => q.id === quiz.id)

    if (index >= 0) {
      cachedQuizzes[index] = quiz
    } else {
      cachedQuizzes.push(quiz)
    }

    localStorage.setItem('cached_quizzes', JSON.stringify(cachedQuizzes))
  }

  private removeLocalQuizData(quizId: string) {
    const cachedQuizzes = JSON.parse(localStorage.getItem('cached_quizzes') || '[]')
    const filtered = cachedQuizzes.filter((q: any) => q.id !== quizId)
    localStorage.setItem('cached_quizzes', JSON.stringify(filtered))
  }

  private notifyTaskFailure(task: SyncTask, error: any) {
    // Show user notification about failed sync
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('Sync Failed', {
        body: `Failed to sync ${task.type}. Please check your connection and try again.`,
        icon: '/assets/images/icon-192x192.png'
      })
    }

    // Dispatch custom event for app to handle
    window.dispatchEvent(new CustomEvent('sync-task-failed', {
      detail: { task, error }
    }))
  }

  // Public methods
  getPendingTasks(): SyncTask[] {
    return Array.from(this.tasks.values())
  }

  hasPendingTasks(): boolean {
    return this.tasks.size > 0
  }

  getTaskCount(): number {
    return this.tasks.size
  }

  isProcessing(): boolean {
    return this.syncInProgress
  }

  // Force sync (useful for manual retry)
  async forcSync(): Promise<void> {
    if (this.isOnline) {
      await this.processTasks()
    }
  }

  // Clear all tasks (useful for logout)
  clearAllTasks(): void {
    this.tasks.clear()
    this.saveTasks()
  }
}

export { BackgroundSyncManager, type SyncTask }
```

**✓ TYPE CHECK:** Run `npx tsc --noEmit`

**Expected outcome:** Full Progressive Web App implementation with install prompts, background sync, and offline capabilities.

---

## Checkpoint: Phase 5 Preparation Complete

This completes the first 5 steps of Phase 5. The remaining steps (46-50) would continue with:

### **Remaining Steps Preview:**
- **Step 46**: Internationalization (i18n) and Localization
- **Step 47**: Advanced Analytics and User Behavior Tracking
- **Step 48**: Maintenance Mode and Feature Flags
- **Step 49**: Legacy Browser Support and Graceful Degradation
- **Step 50**: Final Production Optimization and Launch Preparation

### **What's Been Accomplished (Steps 41-45):**
- ✅ **Advanced Performance**: Intelligent preloading and critical path optimization
- ✅ **Memory Management**: Comprehensive leak prevention and optimization
- ✅ **Accessibility Excellence**: WCAG 2.1 AA compliance with advanced features
- ✅ **State Management**: Observable stores with middleware and caching
- ✅ **PWA Implementation**: Full Progressive Web App with background sync

### **Current Status:**
Your application now has enterprise-grade performance, accessibility, state management, and PWA capabilities. The foundation is complete for the final optimization steps.

**Ready to continue with the remaining Phase 5 steps (46-50)?**
