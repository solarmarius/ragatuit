import { Badge, HStack, Table, Text, VStack } from "@chakra-ui/react"
import { Link as RouterLink } from "@tanstack/react-router"
import { memo } from "react"

import type { Quiz } from "@/client/types.gen"
import { Button } from "@/components/ui/button"
import { StatusLight } from "@/components/ui/status-light"
import {
  formatDate,
  getQuizStatusText,
  getSelectedModulesCount,
} from "@/lib/utils"

interface QuizTableRowProps {
  quiz: Quiz
}

export const QuizTableRow = memo(function QuizTableRow({
  quiz,
}: QuizTableRowProps) {
  const moduleCount = getSelectedModulesCount(quiz)

  return (
    <Table.Row key={quiz.id}>
      <Table.Cell>
        <VStack align="start" gap={1}>
          <Text fontWeight="medium">{quiz.title}</Text>
          <Text fontSize="sm" color="gray.500">
            {moduleCount} module{moduleCount !== 1 ? "s" : ""} selected
          </Text>
        </VStack>
      </Table.Cell>
      <Table.Cell>
        <VStack align="start" gap={1}>
          <Text>{quiz.canvas_course_name}</Text>
          <Text fontSize="sm" color="gray.500">
            ID: {quiz.canvas_course_id}
          </Text>
        </VStack>
      </Table.Cell>
      <Table.Cell>
        <Badge variant="solid" colorScheme="blue">
          {quiz.question_count}
        </Badge>
      </Table.Cell>
      <Table.Cell>
        <HStack gap={2} align="center">
          <StatusLight status={quiz.status || "created"} />
          <Text fontSize="sm" color="gray.600">
            {getQuizStatusText(quiz)}
          </Text>
        </HStack>
      </Table.Cell>
      <Table.Cell>
        <Text fontSize="sm">
          {quiz.created_at ? formatDate(quiz.created_at) : "Unknown"}
        </Text>
      </Table.Cell>
      <Table.Cell>
        <HStack gap={2}>
          <Button size="sm" variant="outline" asChild>
            <RouterLink to={`/quiz/${quiz.id}`} params={{ id: quiz.id! }}>
              View
            </RouterLink>
          </Button>
        </HStack>
      </Table.Cell>
    </Table.Row>
  )
})
