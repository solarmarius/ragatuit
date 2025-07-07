import { createFileRoute, redirect } from "@tanstack/react-router"

export const Route = createFileRoute("/login/success")({
  beforeLoad: ({ search }) => {
    const token = typeof search.token === 'string' ? search.token : undefined

    if (token) {
      localStorage.setItem("access_token", token)

      // Redirect immediately from beforeLoad
      throw redirect({
        to: "/",
      })
    }
    throw redirect({
      to: "/login",
      search: { error: "No authentication token received" },
    })
  },
  component: () => <div />,
  validateSearch: (search: Record<string, unknown>) => {
    return {
      token: typeof search.token === 'string' ? search.token : undefined,
    }
  },
})
