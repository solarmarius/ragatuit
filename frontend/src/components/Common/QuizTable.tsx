import { Card, Table } from "@chakra-ui/react"
import { memo } from "react"

import type { Quiz } from "@/client/types.gen"
import { QuizTableRow } from "./QuizTableRow"

interface QuizTableProps {
  quizzes: Quiz[]
}

export const QuizTable = memo(function QuizTable({ quizzes }: QuizTableProps) {
  return (
    <Card.Root>
      <Card.Body p={0}>
        <Table.Root>
          <Table.Header>
            <Table.Row>
              <Table.ColumnHeader>Quiz Title</Table.ColumnHeader>
              <Table.ColumnHeader>Course</Table.ColumnHeader>
              <Table.ColumnHeader>Questions</Table.ColumnHeader>
              <Table.ColumnHeader>LLM Model</Table.ColumnHeader>
              <Table.ColumnHeader>Status</Table.ColumnHeader>
              <Table.ColumnHeader>Created</Table.ColumnHeader>
              <Table.ColumnHeader>Actions</Table.ColumnHeader>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {quizzes.map((quiz) => (
              <QuizTableRow key={quiz.id} quiz={quiz} />
            ))}
          </Table.Body>
        </Table.Root>
      </Card.Body>
    </Card.Root>
  )
})
