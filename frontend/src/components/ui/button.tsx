import type { ButtonProps as ChakraButtonProps } from "@chakra-ui/react"
import {
  AbsoluteCenter,
  Button as ChakraButton,
  Span,
  Spinner,
} from "@chakra-ui/react"
import * as React from "react"

/**
 * Props for button loading state functionality.
 * Extends the base button with loading indicators and text.
 */
interface ButtonLoadingProps {
  /** Whether the button is in a loading state */
  loading?: boolean
  /** Text to display when loading. If not provided, only spinner is shown */
  loadingText?: React.ReactNode
}

/**
 * Props for the enhanced Button component.
 * Extends Chakra UI's ButtonProps with loading state functionality.
 *
 * @example
 * ```tsx
 * // Basic button usage
 * <Button>Click me</Button>
 *
 * // Button with loading state
 * <Button loading={isSubmitting}>
 *   Submit Form
 * </Button>
 *
 * // Button with loading text
 * <Button loading={isCreating} loadingText="Creating...">
 *   Create Quiz
 * </Button>
 *
 * // Button with Chakra UI props
 * <Button
 *   colorScheme="blue"
 *   size="lg"
 *   loading={isLoading}
 *   onClick={handleClick}
 * >
 *   Save Changes
 * </Button>
 * ```
 */
export interface ButtonProps extends ChakraButtonProps, ButtonLoadingProps {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(props, ref) {
    const { loading, disabled, loadingText, children, ...rest } = props
    return (
      <ChakraButton disabled={loading || disabled} ref={ref} {...rest}>
        {loading && !loadingText ? (
          <>
            <AbsoluteCenter display="inline-flex">
              <Spinner size="inherit" color="inherit" />
            </AbsoluteCenter>
            <Span opacity={0}>{children}</Span>
          </>
        ) : loading && loadingText ? (
          <>
            <Spinner size="inherit" color="inherit" />
            {loadingText}
          </>
        ) : (
          children
        )}
      </ChakraButton>
    )
  },
)
