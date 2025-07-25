import type { QuizLanguage } from "@/client";
import { FormField, FormGroup } from "@/components/forms";
import { QUIZ_LANGUAGES } from "@/lib/constants";
import { Box, Card, HStack, RadioGroup, Text, VStack } from "@chakra-ui/react";

interface QuizSettings {
  language: QuizLanguage;
}

interface QuizSettingsStepProps {
  settings?: QuizSettings;
  onSettingsChange: (settings: QuizSettings) => void;
}

const DEFAULT_SETTINGS: QuizSettings = {
  language: QUIZ_LANGUAGES.ENGLISH,
};

export function QuizSettingsStep({
  settings = DEFAULT_SETTINGS,
  onSettingsChange,
}: QuizSettingsStepProps) {
  const updateSettings = (updates: Partial<QuizSettings>) => {
    const newSettings = { ...settings, ...updates };
    onSettingsChange(newSettings);
  };

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
  ];

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
    </FormGroup>
  );
}
