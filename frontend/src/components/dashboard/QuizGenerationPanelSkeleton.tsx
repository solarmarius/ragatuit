import { LoadingSkeleton } from "@/components/common"
import { UI_COLORS, UI_SIZES } from "@/lib/constants"
import { Box, Card, HStack, VStack } from "@chakra-ui/react"

export function QuizGenerationPanelSkeleton() {
  return (
    <Card.Root>
      <Card.Header>
        <HStack justify="space-between" align="center">
          <LoadingSkeleton
            height={UI_SIZES.SKELETON.HEIGHT.XL}
            width={UI_SIZES.SKELETON.WIDTH.TEXT_LG}
          />
          <LoadingSkeleton
            height={UI_SIZES.SKELETON.HEIGHT.LG}
            width={UI_SIZES.SKELETON.WIDTH.XS}
          />
        </HStack>
        <Box mt={2}>
          <LoadingSkeleton
            height={UI_SIZES.SKELETON.HEIGHT.MD}
            width={UI_SIZES.SKELETON.WIDTH.TEXT_LG}
          />
        </Box>
      </Card.Header>
      <Card.Body>
        <VStack gap={4} align="stretch">
          {[1, 2].map((i) => (
            <Box
              key={i}
              p={4}
              border="1px solid"
              borderColor={UI_COLORS.BORDER.PROCESSING}
              borderRadius="md"
              bg={UI_COLORS.BACKGROUND.PROCESSING}
            >
              <VStack align="stretch" gap={3}>
                <HStack justify="space-between" align="start">
                  <VStack align="start" gap={1} flex={1}>
                    <LoadingSkeleton
                      height={UI_SIZES.SKELETON.HEIGHT.MD}
                      width={UI_SIZES.SKELETON.WIDTH.TEXT_MD}
                    />
                    <LoadingSkeleton
                      height={UI_SIZES.SKELETON.HEIGHT.SM}
                      width={UI_SIZES.SKELETON.WIDTH.XL}
                    />
                  </VStack>
                  <LoadingSkeleton
                    height={UI_SIZES.SKELETON.HEIGHT.SM}
                    width={UI_SIZES.SKELETON.HEIGHT.SM}
                  />
                </HStack>

                <Box>
                  <HStack justify="space-between" mb={2}>
                    <LoadingSkeleton
                      height={UI_SIZES.SKELETON.HEIGHT.SM}
                      width={UI_SIZES.SKELETON.WIDTH.XXL}
                    />
                    <LoadingSkeleton
                      height={UI_SIZES.SKELETON.HEIGHT.SM}
                      width={UI_SIZES.SKELETON.WIDTH.XS}
                    />
                  </HStack>
                  <LoadingSkeleton
                    height={UI_SIZES.PANEL.PROGRESS_HEIGHT}
                    width={UI_SIZES.SKELETON.WIDTH.FULL}
                  />
                </Box>

                <HStack justify="space-between" align="center">
                  <HStack gap={2}>
                    <LoadingSkeleton
                      height={UI_SIZES.SKELETON.HEIGHT.LG}
                      width={UI_SIZES.SKELETON.WIDTH.LG}
                    />
                    <LoadingSkeleton
                      height={UI_SIZES.SKELETON.HEIGHT.LG}
                      width={UI_SIZES.SKELETON.WIDTH.MD}
                    />
                  </HStack>
                  <LoadingSkeleton
                    height={UI_SIZES.SKELETON.HEIGHT.XL}
                    width={UI_SIZES.SKELETON.WIDTH.LG}
                  />
                </HStack>
              </VStack>
            </Box>
          ))}
        </VStack>
      </Card.Body>
    </Card.Root>
  )
}
