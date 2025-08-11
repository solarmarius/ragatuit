import { Box, Container, Heading, List, Text, VStack } from "@chakra-ui/react";
import { Link, createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/_layout/privacy-policy")({
  component: PrivacyPolicy,
});

function PrivacyPolicy() {
  return (
    <Container maxW="4xl" py={8}>
      <VStack gap={8} align="stretch">
        <Heading size="2xl" textAlign="center">
          Privacy Policy
        </Heading>

        <Text fontSize="sm" color="gray.600" textAlign="center">
          Last updated: {new Date().toLocaleDateString()}
        </Text>

        <Box>
          <Heading size="lg" mb={4}>
            1. Introduction
          </Heading>
          <Text mb={4}>
            RAG@UiT is an application developed at UiT The Arctic University of
            Norway to assist instructors and course coordinators in generating
            quizzes based on course content from Canvas LMS. The application
            streamlines the creation of question banks for quizzes and exams
            while also serving as a research platform for a project thesis on
            quality metrics for Norwegian AI-generated educational questions.
          </Text>
          <Text mb={4}>
            As part of the research, anonymized quiz and question data is
            retained for analysis to improve AI-generated question quality.
            Details of the project can be found in the thesis document:{" "}
            <Link
              to="/project-thesis"
              style={{ color: "#3182CE", textDecoration: "underline" }}
            >
              Read the Project Thesis
            </Link>
          </Text>
          <Text>This Privacy Policy explains:</Text>
          <Text pl={6} mb={4}>
            <List.Root>
              <List.Item>What data we collect</List.Item>
              <List.Item>How we use and store it</List.Item>
              <List.Item>How we protect your data </List.Item>
              <List.Item>Your rights under GDPR</List.Item>
            </List.Root>
          </Text>
        </Box>

        <Box>
          <Heading size="lg" mb={4}>
            2. Data We Collect
          </Heading>
          <Heading size="md" mb={4}>
            2.1 User Data
          </Heading>
          <Text mb={4}>
            Collected when you log in with your Canvas LMS account via OAuth2:
          </Text>
          <Text pl={6} mb={4}>
            <List.Root>
              <List.Item>
                Personal identifiers: Name, Canvas LMS user ID (canvas_id)
              </List.Item>
              <List.Item>
                Authentication data: Encrypted Canvas OAuth access and refresh
                tokens, token expiry
              </List.Item>
              <List.Item>
                Usage preferences: Onboarding completion status
              </List.Item>
              <List.Item>
                System metadata: Account creation and update timestamps
              </List.Item>
            </List.Root>
          </Text>
          <Heading size="md" mb={4}>
            2.2 Quiz Data
          </Heading>
          <Text mb={4}>Collected when you create quizzes:</Text>
          <Text pl={6} mb={4}>
            <List.Root>
              <List.Item>
                Course data: Canvas course ID and name, selected modules
              </List.Item>
              <List.Item>
                Content data: Extracted course content for retrieval-augmented
                generation (RAG) metrics
              </List.Item>
              <List.Item>
                Quiz settings: Question count, AI model parameters, language,
                tone
              </List.Item>
              <List.Item>
                Processing data: Status, error tracking, timestamps for content
                extraction and export
              </List.Item>
            </List.Root>
          </Text>
          <Heading size="md" mb={4}>
            2.3 Question Data
          </Heading>
          <Text mb={4}>Generated during quiz creation:</Text>
          <Text pl={6} mb={4}>
            <List.Root>
              <List.Item>
                Question content: Type, text, options, correct answers,
                explanations, difficulty, tags
              </List.Item>
              <List.Item>
                Approval workflow: Approval status, timestamps
              </List.Item>
              <List.Item>
                Edit history: Complete audit trail of changes
              </List.Item>
              <List.Item>
                Integration data: Canvas quiz item ID after export
              </List.Item>
            </List.Root>
          </Text>
        </Box>

        <Box>
          <Heading size="lg" mb={4}>
            3. How We Use Your Data
          </Heading>
          <Text mb={4}>Your data is used for:</Text>
          <Text pl={6} mb={4}>
            <List.Root as="ol">
              <List.Item>
                Providing core functionality: Generating quizzes and exporting
                them to Canvas
              </List.Item>
              <List.Item>
                Improving the application: Analyzing anonymized quiz/question
                data to refine AI question generation
              </List.Item>
              <List.Item>
                Academic research: Supporting the thesis project "Quality
                metrics for Norwegian AI-generated educational questions" by
                measuring and validating AI-generated content against teacher
                feedback
              </List.Item>
              <List.Item>
                Security and troubleshooting: Maintaining secure OAuth tokens
                and diagnosing technical issues
              </List.Item>
            </List.Root>
          </Text>
        </Box>

        <Box>
          <Heading size="lg" mb={4}>
            4. Data Retention Policy
          </Heading>
          <Text mb={4}>We operate a selective data retention model:</Text>
          <Text mb={4}>When you delete your account:</Text>
          <Text pl={6} mb={4}>
            <List.Root>
              <List.Item>
                Deleted immediately: All personal identifiers (name, Canvas ID),
                OAuth tokens, preferences, and direct user-to-quiz associations.
              </List.Item>
              <List.Item>
                Preserved (anonymized): Quiz data, extracted course content,
                generated questions, and edit histories for research purposes.
              </List.Item>
            </List.Root>
          </Text>
          <Text mb={4}>Retention periods:</Text>
          <Text pl={6} mb={4}>
            <List.Root>
              <List.Item>
                Personal data: Deleted immediately upon request/account deletion
              </List.Item>
              <List.Item>
                Anonymized quiz/question data: Retained for 1 year for research
                and system improvement
              </List.Item>
            </List.Root>
          </Text>
        </Box>

        <Box>
          <Heading size="lg" mb={4}>
            5. Legal Basis for Processing
          </Heading>
          <Text mb={4}>
            Consent: Authentication via Canvas LMS to access and process your
            course data
          </Text>
          <Text>
            Legitimate Interest: Retention of anonymized data for academic
            research and AI system improvement
          </Text>
        </Box>

        <Box>
          <Heading size="lg" mb={4}>
            6. Data Protection Measures
          </Heading>
          <Text mb={4}>We implement data protection by design:</Text>
          <Text pl={6} mb={4}>
            <List.Root>
              <List.Item>
                Encryption at rest: OAuth tokens are encrypted with an
                application secret key
              </List.Item>
              <List.Item>
                Anonymization: All personal identifiers are removed upon account
                deletion
              </List.Item>
              <List.Item>
                Soft delete: Anonymized data is retained without being
                accessible in normal user views
              </List.Item>
              <List.Item>
                Access control: Only authorized researchers have access to
                anonymized datasets
              </List.Item>
              <List.Item>
                Audit trails: Edit histories maintained for transparency and
                research validity
              </List.Item>
            </List.Root>
          </Text>
        </Box>

        <Box>
          <Heading size="lg" mb={4}>
            7. Your Rights under GDPR
          </Heading>
          <Text mb={4}>You have the rights to:</Text>
          <Text pl={6} mb={4}>
            <List.Root>
              <List.Item>Access your personal data</List.Item>
              <List.Item>Rectify inaccurate data</List.Item>
              <List.Item>
                Erase your account and all associated personal data
              </List.Item>
              <List.Item>
                Object to processing for non-essential purposes
              </List.Item>
            </List.Root>
          </Text>
        </Box>

        <Box>
          <Heading size="lg" mb={4}>
            8. Data Sharing
          </Heading>
          <Text mb={4}>
            We do not sell or share your personal data with third parties for
            marketing. Anonymized datasets may be shared with academic
            collaborators for research purposes.
          </Text>
        </Box>

        <Box>
          <Heading size="lg" mb={4}>
            9. Changes to This Policy
          </Heading>
          <Text mb={4}>
            We review this upon schema changes. Updates will be communicated
            through this application.
          </Text>
        </Box>

        <Box>
          <Heading size="lg" mb={4}>
            7. Contact Information
          </Heading>
          <Text>
            If you have any questions about this privacy policy, please contact
            us at: Marius Solaas, mso270@uit.no
          </Text>
        </Box>
      </VStack>
    </Container>
  );
}
