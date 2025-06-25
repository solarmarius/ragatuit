import {
  Badge,
  Box,
  Card,
  HStack,
  Progress,
  Skeleton,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"

import { QuizService } from "@/client"

interface QuestionStatsProps {
  quizId: string
}

export function QuestionStats({ quizId }: QuestionStatsProps) {
  const {
    data: stats,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["quiz", quizId, "questions", "stats"],
    queryFn: async () => {
      return await QuizService.getQuizQuestionStats({ quizId })
    },
  })

  if (isLoading) {
    return <QuestionStatsSkeleton />
  }

  if (error || !stats) {
    return (
      <Card.Root>
        <Card.Body>
          <Text color="red.500">Failed to load question statistics</Text>
        </Card.Body>
      </Card.Root>
    )
  }

  const progressPercentage =
    stats.total > 0 ? (stats.approved / stats.total) * 100 : 0

  return (
    <Card.Root>
      <Card.Header>
        <Text fontSize="xl" fontWeight="semibold">
          Question Review Progress
        </Text>
      </Card.Header>
      <Card.Body>
        <VStack gap={4} align="stretch">
          <HStack justify="space-between">
            <Text fontWeight="medium" color="gray.700">
              Approved Questions
            </Text>
            <Badge variant="outline" colorScheme="green" size="lg">
              {stats.approved} of {stats.total}
            </Badge>
          </HStack>

          <Box>
            <HStack justify="space-between" mb={2}>
              <Text fontWeight="medium" color="gray.700">
                Progress
              </Text>
              <Text fontSize="sm" color="gray.600">
                {progressPercentage.toFixed(0)}%
              </Text>
            </HStack>
            <Progress.Root
              value={progressPercentage}
              size="lg"
              colorPalette="green"
            >
              <Progress.Track>
                <Progress.Range />
              </Progress.Track>
            </Progress.Root>
          </Box>

          {stats.total > 0 && stats.approved === stats.total && (
            <Box
              p={3}
              bg="green.50"
              borderRadius="md"
              border="1px solid"
              borderColor="green.200"
            >
              <Text
                fontSize="sm"
                fontWeight="medium"
                color="green.700"
                textAlign="center"
              >
                🎉 All questions have been reviewed and approved!
              </Text>
              <Text
                fontSize="sm"
                fontWeight="medium"
                color="green.700"
                textAlign="center"
              >
                TODO: Add post to Canvas button after all has been reviewed
              </Text>
            </Box>
          )}

          {stats.total === 0 && (
            <Box
              p={3}
              bg="gray.50"
              borderRadius="md"
              border="1px solid"
              borderColor="gray.200"
            >
              <Text fontSize="sm" color="gray.600" textAlign="center">
                No questions generated yet. Questions will appear here once
                generation is complete.
              </Text>
            </Box>
          )}
        </VStack>
      </Card.Body>
    </Card.Root>
  )
}

function QuestionStatsSkeleton() {
  return (
    <Card.Root>
      <Card.Header>
        <Skeleton height="24px" width="200px" />
      </Card.Header>
      <Card.Body>
        <VStack gap={4} align="stretch">
          <HStack justify="space-between">
            <Skeleton height="20px" width="120px" />
            <Skeleton height="24px" width="40px" />
          </HStack>
          <HStack justify="space-between">
            <Skeleton height="20px" width="140px" />
            <Skeleton height="24px" width="40px" />
          </HStack>
          <Box>
            <HStack justify="space-between" mb={2}>
              <Skeleton height="20px" width="80px" />
              <Skeleton height="16px" width="30px" />
            </HStack>
            <Skeleton height="8px" width="100%" />
          </Box>
        </VStack>
      </Card.Body>
    </Card.Root>
  )
}
