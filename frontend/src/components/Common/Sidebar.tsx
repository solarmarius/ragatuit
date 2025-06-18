import { Box, Button, Flex, Image } from "@chakra-ui/react";
import { Link } from "@tanstack/react-router";

import Logo from "/assets/images/logo.svg";

import useAuth from "@/hooks/useCanvasAuth";
import SidebarItems from "./SidebarItems";

const Sidebar = () => {
  const { logout } = useAuth();

  const handleLogout = async () => {
    logout();
  };

  return (
    <>
      {/* Desktop */}

      <Box
        display={{ base: "none", md: "flex" }}
        position="sticky"
        bg="bg.subtle"
        top={0}
        minW="280px"
        h="100vh"
        p={4}
      >
        <Flex direction="column" w="100%" h="100%">
          <Link to="/">
            <Image src={Logo} maxW="3xs" p={2} />
          </Link>
          <Box w="100%">
            <SidebarItems />
          </Box>
          <Button onClick={handleLogout} w="100%" mt={4} colorPalette="blue">
            Log out
          </Button>
        </Flex>
      </Box>
    </>
  );
};

export default Sidebar;
