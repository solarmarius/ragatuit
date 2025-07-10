import { FormField, FormGroup } from "@/components/forms"
import { Box, Input, Text } from "@chakra-ui/react"

interface QuizSettings {
  questionCount: number
}

interface QuizSettingsStepProps {
  settings?: QuizSettings
  onSettingsChange: (settings: QuizSettings) => void
}

const DEFAULT_SETTINGS: QuizSettings = {
  questionCount: 100,
}

export function QuizSettingsStep({
  settings = DEFAULT_SETTINGS,
  onSettingsChange,
}: QuizSettingsStepProps) {
  const updateSettings = (updates: Partial<QuizSettings>) => {
    const newSettings = { ...settings, ...updates }
    onSettingsChange(newSettings)
  }

  return (
    <FormGroup gap={6}>
      <FormField label="Question Count" isRequired>
        <Box maxW="300px">
          <Input
            type="number"
            value={settings.questionCount}
            onChange={(e) =>
              updateSettings({
                questionCount: Number.parseInt(e.target.value) || 100,
              })
            }
            min={1}
            max={200}
            placeholder="Enter number of questions"
          />
          <Text fontSize="sm" color="gray.600" mt={2}>
            Number of questions to generate (1-200)
          </Text>
        </Box>
      </FormField>
    </FormGroup>
  )
}
