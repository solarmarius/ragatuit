import { Button } from "@chakra-ui/react"
import { SiCanvas } from "react-icons/si"

import useCanvasAuth from "@/hooks/useCanvasAuth"

interface CanvasLoginButtonProps {
  size?: "sm" | "md" | "lg"
  variant?: "solid" | "outline"
  isLoading?: boolean
}

const CanvasLoginButton = ({
  size = "md",
  variant = "solid",
  isLoading = false,
}: CanvasLoginButtonProps) => {
  const { initiateCanvasLogin } = useCanvasAuth()

  return (
    <Button
      onClick={initiateCanvasLogin}
      size={size}
      variant={variant}
      colorPalette="red"
      loading={isLoading}
      width="100%"
    >
      <SiCanvas /> Continue with Canvas
    </Button>
  )
}

export default CanvasLoginButton
