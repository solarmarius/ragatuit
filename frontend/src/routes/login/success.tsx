import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/login/success")({
  beforeLoad: ({ search }) => {
    const token = search.token as string;

    if (token) {
      localStorage.setItem("access_token", token);

      // Redirect immediately from beforeLoad
      throw redirect({
        to: "/",
      });
    } else {
      throw redirect({
        to: "/login",
        search: { error: "No authentication token received" },
      });
    }
  },
  component: () => <div></div>,
  validateSearch: (search: Record<string, unknown>) => {
    return {
      token: search.token as string | undefined,
    };
  },
});
