import { FormField, FormGroup } from "@/components/forms"
import { Button } from "@/components/ui/button"
import {
  Box,
  Card,
  HStack,
  Input,
  Portal,
  Select,
  Slider,
  Text,
  VStack,
  createListCollection,
} from "@chakra-ui/react"
import { useState } from "react"

interface QuizSettings {
  questionCount: number
  llmModel: string
  llmTemperature: number
}

interface QuizSettingsStepProps {
  settings?: QuizSettings
  onSettingsChange: (settings: QuizSettings) => void
}

const DEFAULT_SETTINGS: QuizSettings = {
  questionCount: 100,
  llmModel: "o3",
  llmTemperature: 1,
}

const SUPPORTED_MODELS = createListCollection({
  items: [
    { value: "gpt-4o", label: "GPT-4o" },
    { value: "gpt-4.1-mini", label: "GPT-4.1 Mini" },
    { value: "gpt-o3", label: "GPT-o3" },
    { value: "o3", label: "o3" },
  ],
})

export function QuizSettingsStep({
  settings = DEFAULT_SETTINGS,
  onSettingsChange,
}: QuizSettingsStepProps) {
  const [activeTab, setActiveTab] = useState<"recommended" | "advanced">(
    "recommended",
  )
  const [currentSettings, setCurrentSettings] = useState<QuizSettings>(settings)

  const updateSettings = (updates: Partial<QuizSettings>) => {
    const newSettings = { ...currentSettings, ...updates }
    setCurrentSettings(newSettings)
    onSettingsChange(newSettings)
  }

  const resetToRecommended = () => {
    setCurrentSettings(DEFAULT_SETTINGS)
    onSettingsChange(DEFAULT_SETTINGS)
  }

  return (
    <FormGroup gap={6}>
      <FormField label="Question Count" isRequired>
        <Box maxW="300px">
          <Input
            type="number"
            value={currentSettings.questionCount}
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

      {/* LLM Settings Tabs */}
      <Box>
        <Text fontSize="lg" fontWeight="semibold" mb={4}>
          LLM Settings
        </Text>
        <VStack gap={4} align="stretch">
          {/* Tab Buttons */}
          <HStack>
            <Button
              variant={activeTab === "recommended" ? "solid" : "outline"}
              onClick={() => setActiveTab("recommended")}
              size="sm"
            >
              Recommended Settings
            </Button>
            <Button
              variant={activeTab === "advanced" ? "solid" : "outline"}
              onClick={() => setActiveTab("advanced")}
              size="sm"
            >
              Advanced Settings
            </Button>
          </HStack>

          {/* Tab Content */}
          {activeTab === "recommended" ? (
            <Card.Root>
              <Card.Body>
                <VStack gap={4} align="stretch">
                  <Text fontSize="lg" fontWeight="semibold">
                    Recommended Configuration
                  </Text>

                  <Box>
                    <Text fontWeight="medium">Model:</Text>
                    <Text color="gray.600">o3</Text>
                    <Text fontSize="sm" color="gray.500">
                      Optimized for educational content generation
                    </Text>
                  </Box>

                  <Box>
                    <Text fontWeight="medium">Temperature:</Text>
                    <Text color="gray.600">1</Text>
                    <Text fontSize="sm" color="gray.500">
                      Balanced creativity and consistency for quiz questions
                    </Text>
                  </Box>
                </VStack>
              </Card.Body>
            </Card.Root>
          ) : (
            <Card.Root>
              <Card.Body>
                <VStack gap={6} align="stretch">
                  <Text fontSize="lg" fontWeight="semibold">
                    Advanced Configuration
                  </Text>

                  <FormField label="Model" isRequired>
                    <Select.Root
                      collection={SUPPORTED_MODELS}
                      value={[currentSettings.llmModel]}
                      onValueChange={(e) =>
                        updateSettings({ llmModel: e.value[0] })
                      }
                      size="sm"
                    >
                      <Select.Control>
                        <Select.Trigger>
                          <Select.ValueText placeholder="Select model" />
                        </Select.Trigger>
                        <Select.IndicatorGroup>
                          <Select.Indicator />
                        </Select.IndicatorGroup>
                      </Select.Control>
                      <Portal>
                        <Select.Positioner>
                          <Select.Content>
                            {SUPPORTED_MODELS.items.map((model) => (
                              <Select.Item item={model} key={model.value}>
                                {model.label}
                                <Select.ItemIndicator />
                              </Select.Item>
                            ))}
                          </Select.Content>
                        </Select.Positioner>
                      </Portal>
                    </Select.Root>
                    <Text fontSize="sm" color="gray.500" mt={1}>
                      Choose the OpenAI model for question generation
                    </Text>
                  </FormField>

                  <FormField label="Temperature" isRequired>
                    <VStack gap={2} align="stretch">
                      <HStack justify="space-between">
                        <Text fontSize="sm" color="gray.600">
                          Current: {currentSettings.llmTemperature}
                        </Text>
                      </HStack>
                      <Slider.Root
                        value={[currentSettings.llmTemperature]}
                        onValueChange={(e) =>
                          updateSettings({ llmTemperature: e.value[0] })
                        }
                        min={0}
                        max={2}
                        step={0.1}
                        size="sm"
                      >
                        <Slider.Control>
                          <Slider.Track>
                            <Slider.Range />
                          </Slider.Track>
                          <Slider.Thumb index={0} />
                        </Slider.Control>
                      </Slider.Root>
                      <HStack justify="space-between">
                        <Text fontSize="xs" color="gray.500">
                          More Focused (0.0)
                        </Text>
                        <Text fontSize="xs" color="gray.500">
                          More Creative (2.0)
                        </Text>
                      </HStack>
                    </VStack>
                    <Text fontSize="sm" color="gray.500" mt={1}>
                      Controls creativity vs consistency in question generation
                    </Text>
                  </FormField>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={resetToRecommended}
                    disabled={
                      currentSettings.llmModel === DEFAULT_SETTINGS.llmModel &&
                      currentSettings.llmTemperature ===
                        DEFAULT_SETTINGS.llmTemperature
                    }
                  >
                    Use Recommended Settings
                  </Button>
                </VStack>
              </Card.Body>
            </Card.Root>
          )}
        </VStack>
      </Box>
    </FormGroup>
  )
}
