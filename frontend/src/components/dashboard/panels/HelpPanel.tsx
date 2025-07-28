import {
  Alert,
  Badge,
  Box,
  Card,
  HStack,
  Link,
  Text,
  VStack,
} from "@chakra-ui/react"
import { LuExternalLink } from "react-icons/lu"

export function HelpPanel() {
  return (
    <Card.Root>
      <Card.Header>
        <Text fontSize="lg" fontWeight="semibold">
          Help and Resources
        </Text>
        <Text fontSize="sm" color="gray.600">
          Learn how to use Rag@UiT effectively
        </Text>
      </Card.Header>
      <Card.Body>
        <VStack gap={6} align="stretch">
          {/* About Section */}
          <Box>
            <Text fontSize="sm" fontWeight="semibold" mb={2} color="gray.700">
              About Rag@UiT
            </Text>
            <Text fontSize="sm" color="gray.600" lineHeight="relaxed">
              Rag@UiT uses LLMs to generate multiple-choice questions from your
              Canvas course materials. The system analyzes the modules from a
              course and creates relevant questions that you can review,
              approve, and export directly to Canvas.
            </Text>
          </Box>

          {/* How It Works Section */}
          <Box>
            <Text fontSize="sm" fontWeight="semibold" mb={3} color="gray.700">
              How It Works
            </Text>
            <VStack gap={2} align="stretch">
              <HStack gap={3}>
                <Badge variant="solid" colorScheme="blue" size="sm" minW="4">
                  1
                </Badge>
                <Text fontSize="sm" color="gray.600">
                  Select course and modules from Canvas
                </Text>
              </HStack>
              <HStack gap={3}>
                <Badge variant="solid" colorScheme="blue" size="sm" minW="4">
                  2
                </Badge>
                <Text fontSize="sm" color="gray.600">
                  The app extracts PDFs and pages from modules
                </Text>
              </HStack>
              <HStack gap={3}>
                <Badge variant="solid" colorScheme="blue" size="sm" minW="4">
                  3
                </Badge>
                <Text fontSize="sm" color="gray.600">
                  LLM generate questions per module
                </Text>
              </HStack>
              <HStack gap={3}>
                <Badge variant="solid" colorScheme="blue" size="sm" minW="4">
                  4
                </Badge>
                <Text fontSize="sm" color="gray.600">
                  Review and approve questions
                </Text>
              </HStack>
              <HStack gap={3}>
                <Badge variant="solid" colorScheme="blue" size="sm" minW="4">
                  5
                </Badge>
                <Text fontSize="sm" color="gray.600">
                  Export to Canvas as a quiz
                </Text>
              </HStack>
            </VStack>
          </Box>

          {/* Helpful Links Section */}
          <Box>
            <Text fontSize="sm" fontWeight="semibold" mb={3} color="gray.700">
              Helpful Links
            </Text>
            <VStack gap={2} align="stretch">
              <Link
                href="https://uit.instructure.com"
                target="_blank"
                rel="noopener noreferrer"
                fontSize="sm"
                color="blue.600"
                _hover={{ textDecoration: "underline" }}
              >
                Canvas UiT
                <LuExternalLink />
              </Link>
              <Link
                href="mailto:marius.r.solaas@uit.no"
                fontSize="sm"
                color="blue.600"
                _hover={{ textDecoration: "underline" }}
              >
                Contact Developer
              </Link>
              <Link
                href="https://github.com/uit-no/ragatuit"
                fontSize="sm"
                color="blue.600"
                _hover={{ textDecoration: "underline" }}
              >
                GitHub Repository
                <LuExternalLink />
              </Link>
            </VStack>
          </Box>

          {/* Tips Section */}
          <Box
            p={3}
            bg="blue.50"
            borderRadius="md"
            border="1px solid"
            borderColor="blue.200"
          >
            <Text fontSize="sm" fontWeight="semibold" color="blue.700" mb={2}>
              💡 Tips for Best Results
            </Text>
            <VStack gap={1} align="stretch">
              <Text fontSize="sm" color="blue.600">
                • Adjust question count based on module content length
              </Text>
              <Text fontSize="sm" color="blue.600">
                • Review all generated questions before approval
              </Text>
              <Text fontSize="sm" color="blue.600">
                • Make sure diagrams and images in the course are explained with
                text
              </Text>
            </VStack>
          </Box>
          <Alert.Root status="info" variant="subtle" colorPalette="orange">
            <Alert.Content>
              <Alert.Description>
                Review our{" "}
                <Link
                  href="/privacy-policy"
                  color="blue.500"
                  textDecoration="underline"
                >
                  Privacy Policy
                </Link>{" "}
                to understand how we handle your data.
              </Alert.Description>
            </Alert.Content>
          </Alert.Root>
        </VStack>
      </Card.Body>
    </Card.Root>
  )
}
