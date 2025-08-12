"use client"

import { ChakraProvider } from "@chakra-ui/react"
import type { PropsWithChildren } from "react"
import { system } from "../../theme"
import { Toaster } from "./toaster"

export function CustomProvider(props: PropsWithChildren) {
  return (
    <ChakraProvider value={system}>
      {props.children}
      <Toaster />
    </ChakraProvider>
  )
}
