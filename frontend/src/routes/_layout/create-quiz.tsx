import {
  Box,
  Button,
  Card,
  Container,
  HStack,
  Progress,
  Text,
  VStack,
} from "@chakra-ui/react"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { useCallback, useState } from "react"

import { type QuizLanguage, QuizService } from "@/client"
import { CourseSelectionStep } from "@/components/QuizCreation/CourseSelectionStep"
import { ModuleSelectionStep } from "@/components/QuizCreation/ModuleSelectionStep"
import { QuizSettingsStep } from "@/components/QuizCreation/QuizSettingsStep"
import { useCustomToast, useErrorHandler } from "@/hooks/common"
import { QUIZ_LANGUAGES } from "@/lib/constants"

export const Route = createFileRoute("/_layout/create-quiz")({
  component: CreateQuiz,
})

interface QuizFormData {
  selectedCourse?: {
    id: number
    name: string
  }
  selectedModules?: { [id: number]: string }
  title?: string
  questionCount?: number
  language?: QuizLanguage
}

const TOTAL_STEPS = 3 // Course selection, Module selection, Quiz settings

function CreateQuiz() {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(1)
  const [formData, setFormData] = useState<QuizFormData>({})
  const [isCreating, setIsCreating] = useState(false)
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const { handleError } = useErrorHandler()

  const handleNext = () => {
    if (currentStep < TOTAL_STEPS) {
      setCurrentStep(currentStep + 1)
    }
  }

  const handlePrevious = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleCancel = () => {
    navigate({ to: "/" })
  }

  const updateFormData = useCallback((data: Partial<QuizFormData>) => {
    setFormData((prev) => ({ ...prev, ...data }))
  }, [])

  const handleCreateQuiz = async () => {
    if (
      !formData.selectedCourse ||
      !formData.selectedModules ||
      !formData.title
    ) {
      showErrorToast("Missing required quiz data")
      return
    }

    setIsCreating(true)

    try {
      const quizData = {
        canvas_course_id: formData.selectedCourse.id,
        canvas_course_name: formData.selectedCourse.name,
        selected_modules: formData.selectedModules,
        title: formData.title,
        question_count: formData.questionCount || 100,
        language: formData.language || QUIZ_LANGUAGES.ENGLISH,
      }

      const response = await QuizService.createNewQuiz({
        requestBody: quizData,
      })

      if (response) {
        showSuccessToast("Quiz created successfully!")
        navigate({ to: `/quiz/${response.id}`, params: { id: response.id! } })
      } else {
        throw new Error("Failed to create quiz")
      }
    } catch (error) {
      handleError(error)
    } finally {
      setIsCreating(false)
    }
  }

  const getStepTitle = () => {
    switch (currentStep) {
      case 1:
        return "Select Course"
      case 2:
        return "Select Modules"
      case 3:
        return "Quiz Configuration"
      default:
        return "Create Quiz"
    }
  }

  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <CourseSelectionStep
            selectedCourse={formData.selectedCourse}
            onCourseSelect={(course) =>
              updateFormData({
                selectedCourse: course,
                title: course.name, // Auto-fill title with course name
              })
            }
            title={formData.title}
            onTitleChange={(title) => updateFormData({ title })}
          />
        )
      case 2:
        return (
          <ModuleSelectionStep
            courseId={formData.selectedCourse?.id || 0}
            selectedModules={formData.selectedModules || {}}
            onModulesSelect={(modules) =>
              updateFormData({ selectedModules: modules })
            }
          />
        )
      case 3:
        return (
          <QuizSettingsStep
            settings={{
              questionCount: formData.questionCount || 100,
              language: formData.language || QUIZ_LANGUAGES.ENGLISH,
            }}
            onSettingsChange={(settings) =>
              updateFormData({
                questionCount: settings.questionCount,
                language: settings.language,
              })
            }
          />
        )
      default:
        return null
    }
  }

  const isStepValid = () => {
    switch (currentStep) {
      case 1:
        return (
          formData.selectedCourse != null &&
          formData.title != null &&
          formData.title.trim().length > 0
        )
      case 2:
        return (
          formData.selectedModules != null &&
          Object.keys(formData.selectedModules).length > 0
        )
      case 3: {
        // Step 3 is always valid since we have default values
        const questionCount = formData.questionCount || 100
        return questionCount >= 1 && questionCount <= 200
      }
      default:
        return false
    }
  }

  return (
    <Container maxW="4xl" py={8}>
      <VStack gap={6} align="stretch">
        {/* Header */}
        <Box>
          <Text fontSize="3xl" fontWeight="bold">
            Create New Quiz
          </Text>
          <Text color="gray.600">
            Step {currentStep} of {TOTAL_STEPS}: {getStepTitle()}
          </Text>
        </Box>

        {/* Progress Bar */}
        <Progress.Root
          value={(currentStep / TOTAL_STEPS) * 100}
          colorScheme="blue"
          size="lg"
          borderRadius="md"
        >
          <Progress.Track>
            <Progress.Range />
          </Progress.Track>
        </Progress.Root>

        {/* Step Content */}
        <Card.Root>
          <Card.Body p={8}>{renderStep()}</Card.Body>
        </Card.Root>

        {/* Navigation Buttons */}
        <HStack justify="space-between">
          <Button variant="outline" onClick={handleCancel}>
            Cancel
          </Button>

          <HStack>
            {currentStep > 1 && (
              <Button variant="outline" onClick={handlePrevious}>
                Previous
              </Button>
            )}

            {currentStep < TOTAL_STEPS ? (
              <Button
                colorScheme="blue"
                onClick={handleNext}
                disabled={!isStepValid()}
              >
                Next
              </Button>
            ) : (
              <Button
                colorScheme="green"
                disabled={!isStepValid()}
                onClick={handleCreateQuiz}
                loading={isCreating}
              >
                Create Quiz
              </Button>
            )}
          </HStack>
        </HStack>
      </VStack>
    </Container>
  )
}
