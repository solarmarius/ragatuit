import { Container, Heading, Text, VStack, Box, List } from "@chakra-ui/react";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/_layout/privacy-policy")({
  component: PrivacyPolicy,
});

function PrivacyPolicy() {
  return (
    <Container maxW="4xl" py={8}>
      <VStack spacing={8} align="stretch">
        <Heading size="2xl" textAlign="center">
          Privacy Policy
        </Heading>

        <Text fontSize="sm" color="gray.600" textAlign="center">
          Last updated: {new Date().toLocaleDateString()}
        </Text>

        <Box>
          <Heading size="lg" mb={4}>
            1. Information We Collect
          </Heading>
          <Text mb={4}>
            We collect the following information when you use our service:
          </Text>
          <Text pl={6} mb={4}>
            <List.Root>
              <List.Item>
                Canvas ID number and name associated with your Canvas account
                when you sign up.
              </List.Item>
              <List.Item>
                Quiz generation data including: number of questions per quiz,
                LLM settings (temperature, score, model), and instances of
                question regeneration or editing
              </List.Item>
            </List.Root>
          </Text>
          <Text mb={4}>
            Quiz generation data is collected anonymously - no name or Canvas ID
            is associated with this information.
          </Text>
        </Box>

        <Box>
          <Heading size="lg" mb={4}>
            2. How We Use Your Information
          </Heading>
          <Text mb={4}>We use the information we collect to:</Text>
          <Text pl={6} mb={4}>
            <List.Root>
              <List.Item>Provide, maintain, and improve our services</List.Item>
              <List.Item>
                Authenticate users through Canvas integration
              </List.Item>
              <List.Item>
                Conduct research on LLM usage in multiple choice question
                generation
              </List.Item>
              <List.Item>
                Create aggregated and summarized reports for academic research
                purposes
              </List.Item>
            </List.Root>
          </Text>
          <Text mb={4}>
            The anonymized quiz generation data will be used in a research
            project paper examining LLM usage in multiple choice question
            generation. All data will be aggregated and summarized in reports
            without any personal identifiers.
          </Text>
        </Box>

        <Box>
          <Heading size="lg" mb={4}>
            3. Information Sharing
          </Heading>
          <Text mb={4}>
            We will not sell, trade, or rent your personal information to third
            parties.
          </Text>
        </Box>

        <Box>
          <Heading size="lg" mb={4}>
            4. Data Security
          </Heading>
          <Text mb={4}>
            We implement appropriate technical and organizational measures to
            protect your personal information against unauthorized access,
            alteration, disclosure, or destruction.
          </Text>
        </Box>

        <Box>
          <Heading size="lg" mb={4}>
            5. Your Rights
          </Heading>
          <Text mb={4}>
            You have the right to access, update, or delete your personal
            information. To delete your account, refer to "Danger zone" under
            settings.
          </Text>
        </Box>

        <Box>
          <Heading size="lg" mb={4}>
            6. Changes to This Policy
          </Heading>
          <Text mb={4}>
            We may update this privacy policy from time to time. We will notify
            you of any changes by posting the new privacy policy on this page
            and updating the "Last updated" date.
          </Text>
        </Box>

        <Box>
          <Heading size="lg" mb={4}>
            7. Contact Us
          </Heading>
          <Text>
            If you have any questions about this privacy policy, please contact
            us at: mso270@uit.no
          </Text>
        </Box>
      </VStack>
    </Container>
  );
}
