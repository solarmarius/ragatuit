import {
  Alert,
  Box,
  Card,
  HStack,
  Input,
  RadioGroup,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"

import { CanvasService } from "@/client"
import { LoadingSkeleton } from "@/components/common"
import { Field } from "@/components/ui/field"
import { analyzeCanvasError } from "@/lib/utils"

interface Course {
  id: number
  name: string
}

interface CourseSelectionStepProps {
  selectedCourse?: Course
  onCourseSelect: (course: Course) => void
  title?: string
  onTitleChange: (title: string) => void
}

export function CourseSelectionStep({
  selectedCourse,
  onCourseSelect,
  title,
  onTitleChange,
}: CourseSelectionStepProps) {
  const {
    data: courses,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["canvas-courses"],
    queryFn: CanvasService.getCourses,
    retry: 1, // Only retry once instead of default 3 times
    retryDelay: 1000, // Wait 1 second between retries
    staleTime: 30000, // Consider data stale after 30 seconds
  })

  if (isLoading) {
    return (
      <VStack gap={4} align="stretch">
        <Text fontSize="lg" fontWeight="semibold">
          Loading your courses...
        </Text>
        <LoadingSkeleton height="60px" lines={3} />
      </VStack>
    )
  }

  if (error) {
    const errorInfo = analyzeCanvasError(error)

    return (
      <Alert.Root status="error">
        <Alert.Indicator />
        <Alert.Title>Failed to load courses</Alert.Title>
        <Alert.Description>
          <Text mb={2}>{errorInfo.userFriendlyMessage}</Text>
          <Text fontSize="sm" color="gray.600">
            {errorInfo.actionableGuidance}
          </Text>
        </Alert.Description>
      </Alert.Root>
    )
  }

  if (!courses || courses.length === 0) {
    return (
      <Alert.Root status="info">
        <Alert.Indicator />
        <Alert.Title>No teacher courses found</Alert.Title>
        <Alert.Description>
          You don't have any courses where you are enrolled as a teacher. Please
          check your Canvas account or contact your administrator.
        </Alert.Description>
      </Alert.Root>
    )
  }

  return (
    <VStack gap={4} align="stretch">
      <Box>
        <Text fontSize="lg" fontWeight="semibold" mb={2}>
          Select a course to create a quiz for
        </Text>
        <Text color="gray.600" fontSize="sm">
          Here is the courses we found where you have a teacher role.
        </Text>
        <Text color="gray.600" fontSize="sm">
          Choose the course where you want to generate quiz questions from the
          module materials.
        </Text>
      </Box>

      <RadioGroup.Root value={selectedCourse?.id?.toString() || ""}>
        <VStack gap={3} align="stretch">
          {courses.map((course) => (
            <Card.Root
              key={course.id}
              variant="outline"
              cursor="pointer"
              _hover={{ borderColor: "blue.300" }}
              borderColor={
                selectedCourse?.id === course.id ? "blue.500" : "gray.200"
              }
              bg={selectedCourse?.id === course.id ? "blue.50" : "white"}
              onClick={() => {
                onCourseSelect(course)
              }}
              data-testid={`course-card-${course.id}`}
            >
              <Card.Body p={4}>
                <HStack gap={3}>
                  <RadioGroup.Item value={course.id.toString()}>
                    <RadioGroup.ItemControl />
                  </RadioGroup.Item>
                  <Box flex={1}>
                    <Text fontWeight="medium" fontSize="md" lineClamp={2}>
                      {course.name || "Unnamed Course"}
                    </Text>
                    <Text fontSize="sm" color="gray.600">
                      Course ID: {course.id || "Unknown"}
                    </Text>
                  </Box>
                </HStack>
              </Card.Body>
            </Card.Root>
          ))}
        </VStack>
      </RadioGroup.Root>

      {selectedCourse && (
        <VStack gap={4} align="stretch">
          <Alert.Root status="success">
            <Alert.Indicator />
            <Alert.Description>
              Selected: <strong>{selectedCourse.name}</strong>
            </Alert.Description>
          </Alert.Root>

          <Box>
            <Field label="Quiz Title" required>
              <Input
                value={title || ""}
                onChange={(e) => onTitleChange(e.target.value)}
                placeholder="Enter quiz title"
                data-testid="quiz-title-input"
              />
            </Field>
            <Text fontSize="sm" color="gray.600" mt={1}>
              This is the quiz title shown in Canvas and when browsing quizzes.
              You can modify it before continuing.
            </Text>
          </Box>
        </VStack>
      )}
    </VStack>
  )
}
