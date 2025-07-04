import { Box } from "@chakra-ui/react"
import type { ReactNode } from "react"
import { FormLabel } from "./FormLabel"
import { FormError } from "./FormError"

interface FormFieldProps {
  children: ReactNode
  label?: string
  error?: string
  isRequired?: boolean
  id?: string
}

export function FormField({
  children,
  label,
  error,
  isRequired = false,
  id,
}: FormFieldProps) {
  return (
    <Box>
      {label && (
        <FormLabel htmlFor={id} isRequired={isRequired}>
          {label}
        </FormLabel>
      )}
      {children}
      {error && <FormError>{error}</FormError>}
    </Box>
  )
}
