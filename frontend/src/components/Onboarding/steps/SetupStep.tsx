import { Box, Stack, Text, AspectRatio } from "@chakra-ui/react";

export const SetupStep = () => {
  return (
    <Stack gap={6} align="center">
      <Box textAlign="center">
        <Text fontSize="2xl" fontWeight="bold" color="ui.main" mb={4}>
          Walkthrough of the application
        </Text>
        <AspectRatio ratio={16 / 9}>
          <iframe
            width="560"
            height="315"
            src="https://www.youtube.com/embed/jLdLfmT_rXM?si=Sro-STOkK5ZkGLRk"
            title="YouTube video player"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            referrerPolicy="strict-origin-when-cross-origin"
            allowFullScreen
            style={{
              borderRadius: "8px",
              border: "none",
            }}
          />
        </AspectRatio>
      </Box>
    </Stack>
  );
};
