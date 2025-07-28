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

import { type QuestionBatch, type QuizLanguage, QuizService } from "@/client"
import { CourseSelectionStep } from "@/components/QuizCreation/CourseSelectionStep"
import { ModuleQuestionSelectionStep } from "@/components/QuizCreation/ModuleQuestionSelectionStep"
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
  moduleQuestions?: { [id: string]: QuestionBatch[] }
  title?: string
  language?: QuizLanguage
}

const TOTAL_STEPS = 4 // Course selection, Module selection, Questions per module, Quiz settings

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

  const handleModuleSelection = useCallback(
    (modules: { [id: number]: string }) => {
      const moduleQuestions = { ...formData.moduleQuestions }

      // Initialize empty arrays for newly selected modules
      Object.keys(modules).forEach((moduleId) => {
        if (!moduleQuestions[moduleId]) {
          moduleQuestions[moduleId] = []
        }
      })

      // Remove deselected modules
      Object.keys(moduleQuestions).forEach((moduleId) => {
        if (!modules[Number(moduleId)]) {
          delete moduleQuestions[moduleId]
        }
      })

      updateFormData({
        selectedModules: modules,
        moduleQuestions,
      })
    },
    [formData.moduleQuestions, updateFormData],
  )

  const handleModuleQuestionChange = useCallback(
    (moduleId: string, batches: QuestionBatch[]) => {
      updateFormData({
        moduleQuestions: {
          ...formData.moduleQuestions,
          [moduleId]: batches,
        },
      })
    },
    [formData.moduleQuestions, updateFormData],
  )

  const handleCreateQuiz = async () => {
    if (
      !formData.selectedCourse ||
      !formData.selectedModules ||
      !formData.moduleQuestions ||
      !formData.title
    ) {
      showErrorToast("Missing required quiz data")
      return
    }

    setIsCreating(true)

    try {
      // Transform data to new backend format
      const selectedModulesWithBatches = Object.entries(
        formData.selectedModules,
      ).reduce(
        (acc, [moduleId, moduleName]) => ({
          ...acc,
          [moduleId]: {
            name: moduleName,
            question_batches: formData.moduleQuestions?.[moduleId] || [],
          },
        }),
        {},
      )

      const quizData = {
        canvas_course_id: formData.selectedCourse.id,
        canvas_course_name: formData.selectedCourse.name,
        selected_modules: selectedModulesWithBatches,
        title: formData.title,
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
        return "Configure Question Types"
      case 4:
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
            onModulesSelect={handleModuleSelection}
          />
        )
      case 3:
        return (
          <ModuleQuestionSelectionStep
            selectedModules={Object.fromEntries(
              Object.entries(formData.selectedModules || {}).map(
                ([id, name]) => [id, name],
              ),
            )}
            moduleQuestions={formData.moduleQuestions || {}}
            onModuleQuestionChange={handleModuleQuestionChange}
          />
        )
      case 4:
        return (
          <QuizSettingsStep
            settings={{
              language: formData.language || QUIZ_LANGUAGES.ENGLISH,
            }}
            onSettingsChange={(settings) =>
              updateFormData({
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
        // Validate question batches instead of simple counts
        if (!formData.moduleQuestions) return false

        const hasValidBatches = Object.values(formData.moduleQuestions).every(
          (batches) => {
            // Each module must have at least one batch
            if (batches.length === 0) return false

            // All batches must have valid counts
            return batches.every(
              (batch) => batch.count >= 1 && batch.count <= 20,
            )
          },
        )

        return (
          hasValidBatches && Object.keys(formData.moduleQuestions).length > 0
        )
      }
      case 4:
        // Step 4 is always valid since we have default values
        return true
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
