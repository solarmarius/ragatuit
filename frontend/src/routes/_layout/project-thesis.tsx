import { Box, Container, Heading, List, Text, VStack } from "@chakra-ui/react"
import { createFileRoute } from "@tanstack/react-router"

export const Route = createFileRoute("/_layout/project-thesis")({
  component: ProjectThesis,
})

function ProjectThesis() {
  return (
    <Container maxW="4xl" py={8}>
      <VStack gap={8} align="stretch">
        <Heading size="2xl" textAlign="center">
          INF-3982: Project Thesis in Artificial Intelligence
        </Heading>

        <Heading size="lg" textAlign="center" color="gray.700">
          Quality metrics for Norwegian AI-generated educational questions: An
          empirical analysis using teacher validation data
        </Heading>

        <Text fontSize="lg" textAlign="center" fontWeight="semibold">
          Marius Solaas
        </Text>

        <Text fontSize="sm" color="gray.600" textAlign="center">
          Project period: August 12 - December 15, 2024
        </Text>

        <Box>
          <Heading size="lg" mb={4}>
            1. Introduction
          </Heading>
          <Text mb={4}>
            The integration of Large Language Models (LLMs) into educational
            contexts has enabled automated generation of assessments in multiple
            languages. However, ensuring the quality of such content,
            particularly in low-resource languages like Norwegian remains a
            challenge. While much research focus on English language outputs,
            there is limited empirical validation of Norwegian AI-generated
            educational content.
          </Text>
          <Text mb={4}>
            The RAG@UiT application, developed to generate quiz questions from
            Canvas course content, provides an unique opportunity to study this
            research gap. With teachers actively validating, editing, and
            rejecting AI-generated questions, the system provides rich human
            expert feedback that can be used to assess and improve automatic
            quality evaluation methods.
          </Text>
        </Box>

        <Box>
          <Heading size="lg" mb={4}>
            2. Research Questions
          </Heading>
          <Text mb={4}>
            <strong>Primary Question:</strong>
          </Text>
          <Text mb={4}>
            How can we design reliable quality metrics for Norwegian
            AI-generated educational questions that align with human expert
            feedback?
          </Text>
          <Text mb={4}>
            <strong>Secondary Questions:</strong>
          </Text>
          <Text pl={6} mb={4}>
            <List.Root>
              <List.Item>
                Which specific metrics best predict teacher approval or
                rejection?
              </List.Item>
              <List.Item>
                Can we identify metrics that distinguish between questions
                requiring minor versus major edits?
              </List.Item>
            </List.Root>
          </Text>
        </Box>

        <Box>
          <Heading size="lg" mb={4}>
            3. Methodology
          </Heading>
          <Text mb={4}>
            <strong>Data Collection:</strong>
          </Text>
          <Text mb={4}>
            The primary source of data will be collected from RAG@UiT
            application, which is deployed at Institute of Informatics. We
            expect to collect least 200 AI-generated questions, primarily in
            Norwegian, but also in English. Each question is stored along with
            the corresponding teacher action (approve/edit/delete), as well as a
            complete edit history. Data will be collected over a period of three
            months, with analysis conducted concurrently.
          </Text>
          <Text mb={4}>
            <strong>Metric Development:</strong>
          </Text>
          <Text mb={4}>
            The project will implement and evaluate multiple metrics across four
            dimensions:
          </Text>
          <Text pl={6} mb={4}>
            <List.Root>
              <List.Item>
                <strong>Content grounding:</strong> semantic similarity between
                questions and source content, internal consistency between
                questions and answer options, factual consistency
              </List.Item>
              <List.Item>
                <strong>Structural quality:</strong> question completeness,
                grammatical validity, answer option balance
              </List.Item>
              <List.Item>
                <strong>Pedagogical alignment:</strong> cognitive complexity
                indicators, plausibility of distractors
              </List.Item>
              <List.Item>
                <strong>Linguistic clarity:</strong> readability scores,
                ambiguity detection
              </List.Item>
            </List.Root>
          </Text>
          <Text mb={4}>
            The research will also go into predictive modeling; training a model
            like logistic regression or decision trees to predict teacher action
            based on metric values. Feature importance and explainability will
            be examined using for example SHAP values. Also, a comparative
            analysis will be performed between language-specific models (e.g
            NorBERT) and more general LLMs (e.g. OpenAI) to evaluate the
            robustness of the metrics.
          </Text>
        </Box>

        <Box>
          <Heading size="lg" mb={4}>
            4. Project Aims
          </Heading>
          <Text mb={4}>
            This study presents an unique opportunity to validate quality
            metrics for Norwegian AI-generated educational questions using real
            teacher feedback. The project will empirically assess the
            effectiveness of different metrics, informing the design of
            real-time validation mechanisms for AI-generated content. The
            findings will provide actionable insights in both Norwegian and
            English educational contexts and contribute to the goals supporting
            responsible use of AI in Norwegian education.
          </Text>
        </Box>

        <Box>
          <Heading size="lg" mb={4}>
            5. Project Timeline
          </Heading>
          <Text mb={4}>
            The project thesis is planned over 17 weeks, from August 12 to
            December 15. The project is iterative and the thesis document will
            be developed progressively.
          </Text>
          <Text pl={6} mb={4}>
            <List.Root>
              <List.Item>
                <strong>Week 1-3:</strong> Literature review and establishment
                of theoretical framework.
              </List.Item>
              <List.Item>
                <strong>Week 3-5:</strong> Implementations of evaluation metrics
              </List.Item>
              <List.Item>
                <strong>Week 6-10:</strong> Data collection and concurrent
                preliminary analysis
              </List.Item>
              <List.Item>
                <strong>Week 11-13:</strong> Complete analysis and model
                developments
              </List.Item>
              <List.Item>
                <strong>Week 14-16:</strong> Writing, recommendations and final
                validation
              </List.Item>
              <List.Item>
                <strong>Week 17:</strong> Submission of the final thesis
              </List.Item>
            </List.Root>
          </Text>
        </Box>

        <Box>
          <Heading size="lg" mb={4}>
            6. Reading Materials
          </Heading>
          <Text mb={4}>
            Relevant literature will include but is not limited to:
          </Text>
          <Text pl={6} mb={4}>
            <List.Root>
              <List.Item>
                Research on Norwegian NLP and language specific challenges
              </List.Item>
              <List.Item>Papers on LLM evaluation metrics</List.Item>
              <List.Item>
                Studies on explainability in ML models (SHAP)
              </List.Item>
              <List.Item>
                Pedagogical literature on question quality and cognitive
                complexity
              </List.Item>
              <List.Item>Technical documentation of models</List.Item>
            </List.Root>
          </Text>
        </Box>

        <Box>
          <Heading size="lg" mb={4}>
            7. Contact Information
          </Heading>
          <Text>
            For questions about this research project, please contact: Marius
            Solaas, mso270@uit.no
          </Text>
        </Box>
      </VStack>
    </Container>
  )
}
