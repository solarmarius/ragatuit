import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query"
import { RouterProvider, createRouter } from "@tanstack/react-router"
import { StrictMode } from "react"
import ReactDOM from "react-dom/client"
import { routeTree } from "./routeTree.gen"

import { ApiError } from "./client"
import { CustomProvider } from "./components/ui/provider"
import { clearAuthToken, configureApiClient } from "./lib/api/client"

// Configure API client
configureApiClient()

const handleApiError = (error: Error) => {
  if (error instanceof ApiError && error.status === 401) {
    clearAuthToken()
    window.location.href = "/login"
  }
}
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Cache quiz data for 10 minutes to reduce API calls
      staleTime: 10 * 60 * 1000, // 10 minutes
      // Keep cached data for 30 minutes
      gcTime: 30 * 60 * 1000, // 30 minutes (renamed from cacheTime)
      // Retry failed requests up to 2 times
      retry: 2,
      // Don't refetch on window focus for better UX
      refetchOnWindowFocus: false,
      // Keep previous data while fetching new data
      placeholderData: (previousData: unknown) => previousData,
    },
    mutations: {
      // Retry failed mutations once
      retry: 1,
    },
  },
  queryCache: new QueryCache({
    onError: handleApiError,
  }),
  mutationCache: new MutationCache({
    onError: handleApiError,
  }),
})

const router = createRouter({ routeTree })
declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <CustomProvider>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </CustomProvider>
  </StrictMode>,
)
