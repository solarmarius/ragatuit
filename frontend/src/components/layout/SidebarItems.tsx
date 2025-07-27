import { Box, Flex, Icon, Text } from "@chakra-ui/react"
import { Link as RouterLink, useRouterState } from "@tanstack/react-router"
import { FiFileText, FiHome, FiSettings } from "react-icons/fi"

const items = [
  { icon: FiHome, title: "Dashboard", path: "/" },
  { icon: FiFileText, title: "Quizzes", path: "/quizzes" },
  { icon: FiSettings, title: "Settings", path: "/settings" },
]

interface SidebarItemsProps {
  onClose?: () => void
}

const SidebarItems = ({ onClose }: SidebarItemsProps) => {
  const location = useRouterState({
    select: (state) => state.location,
  })

  const listItems = items.map(({ icon, title, path }) => {
    const isActive =
      title === "Quizzes"
        ? location.pathname === path ||
          location.pathname === "/create-quiz" ||
          location.pathname.startsWith("/quiz/")
        : location.pathname === path

    return (
      <RouterLink key={title} to={path as any} params={{} as any} onClick={onClose}>
        <Flex
          direction="column"
          gap={2}
          px={4}
          py={2}
          color={isActive ? "#013343" : "white"}
          bg={isActive ? "white" : "transparent"}
          _hover={{
            background: isActive ? "white" : "#314159",
          }}
          alignItems="center"
          fontSize="sm"
        >
          <Icon as={icon} boxSize={7} />
          <Text>{title}</Text>
        </Flex>
      </RouterLink>
    )
  })

  return (
    <>
      <Box>{listItems}</Box>
    </>
  )
}

export default SidebarItems
