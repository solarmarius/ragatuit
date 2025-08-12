import type { LoadingSkeletonProps } from "@/types/components"
import { Skeleton, Stack } from "@chakra-ui/react"
import { forwardRef } from "react"

export const LoadingSkeleton = forwardRef<HTMLDivElement, LoadingSkeletonProps>(
  function LoadingSkeleton(
    { height = "20px", width = "100%", lines = 1, gap = 2, ...rest },
    ref,
  ) {
    if (lines === 1) {
      return <Skeleton height={height} width={width} ref={ref} {...rest} />
    }

    return (
      <Stack gap={gap} width="full" ref={ref}>
        {Array.from({ length: lines }).map((_, index) => (
          <Skeleton
            key={index}
            height={height}
            width={index === lines - 1 ? "80%" : width}
            {...rest}
          />
        ))}
      </Stack>
    )
  },
)
