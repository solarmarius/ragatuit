import { Box } from "@chakra-ui/react"
import type { ReactNode } from "react"
import { FormError } from "./FormError"
import { FormLabel } from "./FormLabel"

/**
 * Props for the FormField component.
 * A wrapper component that provides consistent layout for form inputs
 * with label, validation, and error display functionality.
 *
 * @example
 * ```tsx
 * // Basic form field with label
 * <FormField label="Quiz Title" id="title">
 *   <Input id="title" placeholder="Enter quiz title" />
 * </FormField>
 *
 * // Required field with validation error
 * <FormField
 *   label="Course Name"
 *   id="course"
 *   isRequired
 *   error={errors.course?.message}
 * >
 *   <Input
 *     id="course"
 *     placeholder="Select a course"
 *     {...register('course', { required: 'Course is required' })}
 *   />
 * </FormField>
 *
 * // Field with complex input (textarea, select, etc.)
 * <FormField label="Description" id="description">
 *   <Textarea
 *     id="description"
 *     placeholder="Enter description"
 *     rows={4}
 *   />
 * </FormField>
 *
 * // Field without label (for checkboxes, etc.)
 * <FormField error={errors.terms?.message}>
 *   <Checkbox>I agree to the terms and conditions</Checkbox>
 * </FormField>
 * ```
 */
interface FormFieldProps {
  /** The form input element(s) to wrap */
  children: ReactNode
  /** Optional label text to display above the input */
  label?: string
  /** Optional error message to display below the input */
  error?: string
  /** Whether the field is required (adds asterisk to label) */
  isRequired?: boolean
  /** ID to associate the label with the input element */
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
