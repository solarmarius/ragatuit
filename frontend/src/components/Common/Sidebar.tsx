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
      <Box
        display={{ base: "none", md: "flex" }}
        position="sticky"
        bg="#013343"
        top={0}
        minW="150px"
        h="100vh"
        pl={4}
      >
        <Flex direction="column" w="100%" h="100%" alignItems="center">
          <Link to="/">
            <Image src={Logo} maxW="130px" p={2} />
          </Link>
          <Box w="100%">
            <SidebarItems />
          </Box>
          <Button onClick={handleLogout} w="90%" mt={4} colorPalette="blue">
            Log out
          </Button>
        </Flex>
      </Box>
    </>
  );
};

export default Sidebar;
