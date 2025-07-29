import { Badge, Box, Card, HStack, Text, VStack } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { QuizService } from "@/client"
import { QuestionTypeBreakdown } from "@/components/Common"
import { QuestionGenerationTrigger } from "@/components/Questions/QuestionGenerationTrigger"
import { QuizPhaseProgress } from "@/components/ui/quiz-phase-progress"
import { useFormattedDate } from "@/hooks/common"
import { QUIZ_LANGUAGE_LABELS } from "@/lib/constants"
import { queryKeys, quizQueryConfig } from "@/lib/queryConfig"

export const Route = createFileRoute("/_layout/quiz/$id/")({
  component: QuizInformation,
})

function DateDisplay({ date }: { date: string | null | undefined }) {
  const formattedDate = useFormattedDate(date, "default")

  if (!formattedDate) return <Text color="gray.500">Not available</Text>

  return <Text color="gray.600">{formattedDate}</Text>
}

function QuizInformation() {
  const { id } = Route.useParams()

  const { data: quiz } = useQuery({
    queryKey: queryKeys.quiz(id),
    queryFn: async () => {
      const response = await QuizService.getQuiz({ quizId: id })
      return response
    },
    ...quizQueryConfig,
    // Polling is now handled by the layout component based on route
  })

  // Get selected modules - parse JSON string if needed
  const selectedModules = (() => {
    if (!quiz?.selected_modules) return {}

    // If it's already an object, use it directly
    if (typeof quiz.selected_modules === "object") {
      return quiz.selected_modules
    }

    // If it's a string, parse it as JSON
    if (typeof quiz.selected_modules === "string") {
      try {
        return JSON.parse(quiz.selected_modules)
      } catch {
        return {}
      }
    }

    return {}
  })()

  const moduleNames = Object.values(selectedModules)
    .filter(
      (moduleData): moduleData is { name: string; question_count: number } =>
        typeof moduleData === "object" &&
        moduleData !== null &&
        "name" in moduleData &&
        typeof moduleData.name === "string",
    )
    .map((moduleData) => moduleData.name)

  if (!quiz) {
    return (
      <VStack gap={6} align="stretch">
        <Text>Loading quiz information...</Text>
      </VStack>
    )
  }

  return (
    <VStack gap={6} align="stretch">
      {/* Quiz Information */}
      <Card.Root>
        <Card.Header>
          <Text fontSize="xl" fontWeight="semibold">
            Course Information
          </Text>
        </Card.Header>
        <Card.Body>
          <VStack gap={4} align="stretch">
            <Box>
              <Text fontWeight="medium" color="gray.700">
                Canvas Course
              </Text>
              <Text fontSize="lg">{quiz.canvas_course_name}</Text>
              <Text fontSize="sm" color="gray.500">
                Course ID: {quiz.canvas_course_id}
              </Text>
            </Box>

            <Box>
              <Text fontWeight="medium" color="gray.700" mb={2}>
                Selected Modules
              </Text>
              {moduleNames.length > 0 ? (
                <HStack wrap="wrap" gap={2}>
                  {moduleNames.map((moduleName, index) => (
                    <Badge key={index} variant="outline" colorScheme="blue">
                      {moduleName}
                    </Badge>
                  ))}
                </HStack>
              ) : (
                <Text color="gray.500">No modules selected</Text>
              )}
            </Box>
          </VStack>
        </Card.Body>
      </Card.Root>

      {/* Quiz Settings */}
      <Card.Root>
        <Card.Header>
          <Text fontSize="xl" fontWeight="semibold">
            Settings
          </Text>
        </Card.Header>
        <Card.Body>
          <VStack gap={4} align="stretch">
            <HStack justify="space-between">
              <Text fontWeight="medium" color="gray.700">
                Question Count
              </Text>
              <Badge variant="outline">{quiz.question_count}</Badge>
            </HStack>
            <VStack align="stretch" gap={2}>
              <Box>
                <QuestionTypeBreakdown quiz={quiz} variant="detailed" />
              </Box>
            </VStack>
            <HStack justify="space-between">
              <Text fontWeight="medium" color="gray.700">
                Language
              </Text>
              <Badge variant="outline">
                {QUIZ_LANGUAGE_LABELS[quiz.language!]}
              </Badge>
            </HStack>
          </VStack>
        </Card.Body>
      </Card.Root>

      {/* Metadata */}
      <Card.Root>
        <Card.Header>
          <Text fontSize="xl" fontWeight="semibold">
            Metadata
          </Text>
        </Card.Header>
        <Card.Body>
          <VStack gap={4} align="stretch">
            <HStack justify="space-between">
              <Text fontWeight="medium" color="gray.700">
                Quiz ID
              </Text>
              <Text fontSize="sm" fontFamily="mono" color="gray.600">
                {quiz.id}
              </Text>
            </HStack>

            {quiz.created_at && (
              <HStack justify="space-between">
                <Text fontWeight="medium" color="gray.700">
                  Created
                </Text>
                <DateDisplay date={quiz.created_at} />
              </HStack>
            )}

            {quiz.updated_at && (
              <HStack justify="space-between">
                <Text fontWeight="medium" color="gray.700">
                  Last Updated
                </Text>
                <DateDisplay date={quiz.updated_at} />
              </HStack>
            )}
          </VStack>
        </Card.Body>
      </Card.Root>

      {/* Quiz Generation Progress */}
      <Card.Root>
        <Card.Header>
          <Text fontSize="xl" fontWeight="semibold">
            Generation Progress
          </Text>
        </Card.Header>
        <Card.Body>
          <QuizPhaseProgress
            status={quiz.status || "created"}
            failureReason={quiz.failure_reason}
            contentExtractedAt={quiz.content_extracted_at}
            exportedAt={quiz.exported_at}
            lastStatusUpdate={quiz.last_status_update}
            showTimestamps={true}
          />
        </Card.Body>
      </Card.Root>

      {/* Question Generation Trigger */}
      <QuestionGenerationTrigger quiz={quiz} />
    </VStack>
  )
}
