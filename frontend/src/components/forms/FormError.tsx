import { Text } from "@chakra-ui/react"
import type { ReactNode } from "react"

interface FormErrorProps {
  children: ReactNode
}

export function FormError({ children }: FormErrorProps) {
  return (
    <Text fontSize="sm" color="red.500" mt={1}>
      {children}
    </Text>
  )
}
