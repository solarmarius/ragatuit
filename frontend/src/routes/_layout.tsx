import { Flex } from "@chakra-ui/react";
import { Outlet, createFileRoute, redirect } from "@tanstack/react-router";
import { useEffect } from "react";

import { Sidebar } from "@/components/layout";
import { isAuthenticated } from "@/lib/api/client";
import { toaster } from "@/components/ui/toaster";

export const Route = createFileRoute("/_layout")({
  component: Layout,
  beforeLoad: async () => {
    if (!isAuthenticated()) {
      throw redirect({
        to: "/login",
      });
    }
  },
});

function Layout() {
  useEffect(() => {
    // Show deployment warning toast on every page load
    const timer = setTimeout(() => {
      toaster.create({
        title: "⚠️ Development Version",
        description:
          "This application is not officially deployed yet. Data may be deleted without notice.",
        type: "warning",
        duration: 8000, // Show for 8 seconds
      });
    }, 1000); // Delay 1 second after page load

    return () => clearTimeout(timer);
  }, []);

  return (
    <Flex direction="column" h="100vh">
      <Flex flex="1" overflow="hidden">
        <Sidebar />
        <Flex flex="1" direction="column" p={4} overflowY="auto">
          <Outlet />
        </Flex>
      </Flex>
    </Flex>
  );
}

export default Layout;
