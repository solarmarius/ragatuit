import {
  VStack,
  Text,
  Box,
  Card,
  RadioGroup,
  Alert,
  Skeleton,
  HStack,
} from "@chakra-ui/react";
import { useQuery } from "@tanstack/react-query";

import { CanvasService } from "@/client";

interface Course {
  id: number;
  name: string;
}

interface CourseSelectionStepProps {
  selectedCourse?: Course;
  onCourseSelect: (course: Course) => void;
}

export function CourseSelectionStep({
  selectedCourse,
  onCourseSelect,
}: CourseSelectionStepProps) {
  const {
    data: courses,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["canvas-courses"],
    queryFn: CanvasService.getCourses,
  });

  if (isLoading) {
    return (
      <VStack gap={4} align="stretch">
        <Text fontSize="lg" fontWeight="semibold">
          Loading your courses...
        </Text>
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} height="60px" borderRadius="md" />
        ))}
      </VStack>
    );
  }

  if (error) {
    return (
      <Alert.Root status="error">
        <Alert.Indicator />
        <Alert.Title>Failed to load courses</Alert.Title>
        <Alert.Description>
          There was an error loading your Canvas courses. Please try again or
          check your Canvas connection.
        </Alert.Description>
      </Alert.Root>
    );
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
    );
  }

  return (
    <VStack gap={4} align="stretch">
      <Box>
        <Text fontSize="lg" fontWeight="semibold" mb={2}>
          Select a course to create a quiz for
        </Text>
        <Text color="gray.600" fontSize="sm">
          Choose the course where you want to generate quiz questions from the
          course materials.
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
                onCourseSelect(course);
              }}
            >
              <Card.Body p={4}>
                <HStack gap={3}>
                  <RadioGroup.Item value={course.id.toString()}>
                    <RadioGroup.ItemControl />
                  </RadioGroup.Item>
                  <Box flex={1}>
                    <Text fontWeight="medium" fontSize="md">
                      {course.name}
                    </Text>
                    <Text fontSize="sm" color="gray.600">
                      Course ID: {course.id}
                    </Text>
                  </Box>
                </HStack>
              </Card.Body>
            </Card.Root>
          ))}
        </VStack>
      </RadioGroup.Root>

      {selectedCourse && (
        <Alert.Root status="success">
          <Alert.Indicator />
          <Alert.Description>
            Selected: <strong>{selectedCourse.name}</strong>
          </Alert.Description>
        </Alert.Root>
      )}
    </VStack>
  );
}
