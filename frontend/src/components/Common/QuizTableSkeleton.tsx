import { Card, HStack, Table, VStack } from "@chakra-ui/react"
import { memo } from "react"

import { LoadingSkeleton } from "./LoadingSkeleton"
import { UI_SIZES } from "@/lib/constants"

interface QuizTableSkeletonProps {
  rows?: number
}

export const QuizTableSkeleton = memo(function QuizTableSkeleton({
  rows = 5,
}: QuizTableSkeletonProps) {
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
            {Array.from({ length: rows }, (_, i) => (
              <Table.Row key={i}>
                <Table.Cell>
                  <VStack align="start" gap={1}>
                    <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.MD} width={UI_SIZES.SKELETON.WIDTH.TEXT_LG} />
                    <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.SM} width={UI_SIZES.SKELETON.WIDTH.TEXT_MD} />
                  </VStack>
                </Table.Cell>
                <Table.Cell>
                  <VStack align="start" gap={1}>
                    <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.MD} width={UI_SIZES.SKELETON.WIDTH.TEXT_MD} />
                    <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.SM} width={UI_SIZES.SKELETON.WIDTH.LG} />
                  </VStack>
                </Table.Cell>
                <Table.Cell>
                  <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.LG} width={UI_SIZES.SKELETON.WIDTH.MD} />
                </Table.Cell>
                <Table.Cell>
                  <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.LG} width={UI_SIZES.SKELETON.WIDTH.LG} />
                </Table.Cell>
                <Table.Cell>
                  <HStack gap={2} align="center">
                    <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.SM} width={UI_SIZES.SKELETON.WIDTH.SM} />
                    <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.SM} width={UI_SIZES.SKELETON.WIDTH.TEXT_MD} />
                  </HStack>
                </Table.Cell>
                <Table.Cell>
                  <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.SM} width={UI_SIZES.SKELETON.WIDTH.LG} />
                </Table.Cell>
                <Table.Cell>
                  <LoadingSkeleton height={UI_SIZES.SKELETON.HEIGHT.XL} width={UI_SIZES.SKELETON.WIDTH.MD} />
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table.Root>
      </Card.Body>
    </Card.Root>
  )
})
