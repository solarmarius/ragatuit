import type { QuizLanguage, QuizTone } from "@/client"
import { FormField, FormGroup } from "@/components/forms"
import { QUIZ_LANGUAGES, QUIZ_TONES, QUIZ_TONE_LABELS } from "@/lib/constants"
import { Box, Card, HStack, RadioGroup, Text, VStack } from "@chakra-ui/react"

interface QuizSettings {
  language: QuizLanguage
  tone: QuizTone
}

interface QuizSettingsStepProps {
  settings?: QuizSettings
  onSettingsChange: (settings: QuizSettings) => void
}

const DEFAULT_SETTINGS: QuizSettings = {
  language: QUIZ_LANGUAGES.ENGLISH,
  tone: QUIZ_TONES.ACADEMIC,
}

export function QuizSettingsStep({
  settings = DEFAULT_SETTINGS,
  onSettingsChange,
}: QuizSettingsStepProps) {
  const updateSettings = (updates: Partial<QuizSettings>) => {
    const newSettings = { ...settings, ...updates }
    onSettingsChange(newSettings)
  }

  const languageOptions = [
    {
      value: QUIZ_LANGUAGES.ENGLISH,
      label: "English",
      description: "Generate questions in English",
    },
    {
      value: QUIZ_LANGUAGES.NORWEGIAN,
      label: "Norwegian",
      description: "Generate questions in Norwegian (Norsk)",
    },
  ]

  const toneOptions = [
    {
      value: QUIZ_TONES.ACADEMIC,
      label: QUIZ_TONE_LABELS.academic,
      description: "Use formal academic language with precise terminology",
    },
    {
      value: QUIZ_TONES.CASUAL,
      label: QUIZ_TONE_LABELS.casual,
      description: "Use everyday conversational language that feels approachable",
    },
    {
      value: QUIZ_TONES.ENCOURAGING,
      label: QUIZ_TONE_LABELS.encouraging,
      description: "Use warm, supportive language with helpful hints embedded in questions",
    },
    {
      value: QUIZ_TONES.PROFESSIONAL,
      label: QUIZ_TONE_LABELS.professional,
      description: "Use clear, direct business language for workplace training",
    },
  ]

  return (
    <FormGroup gap={6}>
      <FormField label="Quiz Language" isRequired>
        <Box>
          <Text fontSize="sm" color="gray.600" mb={3}>
            Select the language for question generation
          </Text>
          <RadioGroup.Root
            value={settings.language}
            onValueChange={(details) =>
              updateSettings({ language: details.value as QuizLanguage })
            }
          >
            <VStack gap={3} align="stretch">
              {languageOptions.map((option) => (
                <Card.Root
                  key={option.value}
                  variant="outline"
                  cursor="pointer"
                  _hover={{ borderColor: "blue.300" }}
                  borderColor={
                    settings.language === option.value ? "blue.500" : "gray.200"
                  }
                  bg={settings.language === option.value ? "blue.50" : "white"}
                  onClick={() => updateSettings({ language: option.value })}
                  data-testid={`language-card-${option.value}`}
                >
                  <Card.Body>
                    <HStack>
                      <RadioGroup.Item value={option.value} />
                      <Box flex={1}>
                        <Text fontWeight="semibold">{option.label}</Text>
                        <Text fontSize="sm" color="gray.600">
                          {option.description}
                        </Text>
                      </Box>
                    </HStack>
                  </Card.Body>
                </Card.Root>
              ))}
            </VStack>
          </RadioGroup.Root>
        </Box>
      </FormField>

      <FormField label="Tone of Voice" isRequired>
        <Box>
          <Text fontSize="sm" color="gray.600" mb={3}>
            Select the tone for question generation
          </Text>
          <RadioGroup.Root
            value={settings.tone}
            onValueChange={(details) =>
              updateSettings({ tone: details.value as QuizTone })
            }
          >
            <VStack gap={3} align="stretch">
              {toneOptions.map((option) => (
                <Card.Root
                  key={option.value}
                  variant="outline"
                  cursor="pointer"
                  _hover={{ borderColor: "green.300" }}
                  borderColor={
                    settings.tone === option.value ? "green.500" : "gray.200"
                  }
                  bg={settings.tone === option.value ? "green.50" : "white"}
                  onClick={() => updateSettings({ tone: option.value })}
                  data-testid={`tone-card-${option.value}`}
                >
                  <Card.Body>
                    <HStack>
                      <RadioGroup.Item value={option.value} />
                      <Box flex={1}>
                        <Text fontWeight="semibold">{option.label}</Text>
                        <Text fontSize="sm" color="gray.600">
                          {option.description}
                        </Text>
                      </Box>
                    </HStack>
                  </Card.Body>
                </Card.Root>
              ))}
            </VStack>
          </RadioGroup.Root>
        </Box>
      </FormField>
    </FormGroup>
  )
}
