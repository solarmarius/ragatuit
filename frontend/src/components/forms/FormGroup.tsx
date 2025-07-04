import { VStack } from "@chakra-ui/react"
import type { ReactNode } from "react"

interface FormGroupProps {
  children: ReactNode
  gap?: number
}

export function FormGroup({ children, gap = 4 }: FormGroupProps) {
  return (
    <VStack gap={gap} align="stretch">
      {children}
    </VStack>
  )
}
