import type { LoadingSkeletonProps } from "@/types/components"
import { Skeleton, VStack } from "@chakra-ui/react"
import { memo } from "react"

export const LoadingSkeleton = memo(function LoadingSkeleton({
  height = "20px",
  width = "100%",
  lines = 1,
}: LoadingSkeletonProps) {
  if (lines === 1) {
    return <Skeleton height={height} width={width} />
  }

  return (
    <VStack gap={2} align="stretch">
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton
          key={index}
          height={height}
          width={index === lines - 1 ? "80%" : width}
        />
      ))}
    </VStack>
  )
})
