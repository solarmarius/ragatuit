import { Box, Flex, Icon, Text } from "@chakra-ui/react";
import { Link as RouterLink } from "@tanstack/react-router";
import { FiFileText, FiHome, FiSettings } from "react-icons/fi";
import type { IconType } from "react-icons/lib";

const items = [
  { icon: FiHome, title: "Dashboard", path: "/" },
  { icon: FiFileText, title: "Quizzes", path: "/quiz" },
  { icon: FiSettings, title: "User Settings", path: "/settings" },
];

interface SidebarItemsProps {
  onClose?: () => void;
}

interface Item {
  icon: IconType;
  title: string;
  path: string;
}

const SidebarItems = ({ onClose }: SidebarItemsProps) => {
  const listItems = items.map(({ icon, title, path }) => (
    <RouterLink key={title} to={path} onClick={onClose}>
      <Flex
        gap={4}
        px={4}
        py={2}
        _hover={{
          background: "gray.subtle",
        }}
        alignItems="center"
        fontSize="sm"
      >
        <Icon as={icon} alignSelf="center" />
        <Text ml={2}>{title}</Text>
      </Flex>
    </RouterLink>
  ));

  return (
    <>
      <Box>{listItems}</Box>
    </>
  );
};

export default SidebarItems;
