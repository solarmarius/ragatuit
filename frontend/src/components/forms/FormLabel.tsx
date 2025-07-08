import { Text } from "@chakra-ui/react"
import type { ReactNode } from "react"

interface FormLabelProps {
  children: ReactNode
  htmlFor?: string
  isRequired?: boolean
}

export function FormLabel({ children, htmlFor, isRequired }: FormLabelProps) {
  return (
    <Text
      as="label"
      fontSize="sm"
      fontWeight="medium"
      color="gray.700"
      mb={1}
      display="block"
      {...(htmlFor && { htmlFor })}
    >
      {children}
      {isRequired && (
        <Text as="span" color="red.500" ml={1}>
          *
        </Text>
      )}
    </Text>
  )
}
