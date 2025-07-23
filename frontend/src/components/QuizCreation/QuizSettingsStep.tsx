import type { QuestionType, QuizLanguage } from "@/client";
import { FormField, FormGroup } from "@/components/forms";
import { QUESTION_TYPES, QUIZ_LANGUAGES } from "@/lib/constants";
import { Box, Card, HStack, RadioGroup, Text, VStack } from "@chakra-ui/react";

interface QuizSettings {
  language: QuizLanguage;
  questionType: QuestionType;
}

interface QuizSettingsStepProps {
  settings?: QuizSettings;
  onSettingsChange: (settings: QuizSettings) => void;
}

const DEFAULT_SETTINGS: QuizSettings = {
  language: QUIZ_LANGUAGES.ENGLISH,
  questionType: QUESTION_TYPES.MULTIPLE_CHOICE,
};

export function QuizSettingsStep({
  settings = DEFAULT_SETTINGS,
  onSettingsChange,
}: QuizSettingsStepProps) {
  const updateSettings = (updates: Partial<QuizSettings>) => {
    const newSettings = { ...settings, ...updates };
    onSettingsChange(newSettings);
  };

  const questionTypeOptions = [
    {
      value: QUESTION_TYPES.MULTIPLE_CHOICE,
      label: "Multiple Choice Questions",
      description: "Generate questions with multiple answer options",
    },
    {
      value: QUESTION_TYPES.FILL_IN_BLANK,
      label: "Fill in the Blank",
      description: "Generate questions with blank spaces to fill in",
    },
    {
      value: QUESTION_TYPES.MATCHING,
      label: "Matching Questions",
      description: "Generate matching questions with pairs and distractors",
    },
  ];

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
      <FormField label="Question Type" isRequired>
        <Box>
          <Text fontSize="sm" color="gray.600" mb={3}>
            Select the type of questions to generate
          </Text>
          <RadioGroup.Root
            value={settings.questionType}
            onValueChange={(details) =>
              updateSettings({ questionType: details.value as QuestionType })
            }
          >
            <VStack gap={3} align="stretch" maxW="500px">
              {questionTypeOptions.map((option) => (
                <Card.Root
                  key={option.value}
                  variant="outline"
                  cursor="pointer"
                  _hover={{ borderColor: "blue.300" }}
                  borderColor={
                    settings.questionType === option.value
                      ? "blue.500"
                      : "gray.200"
                  }
                  bg={
                    settings.questionType === option.value ? "blue.50" : "white"
                  }
                  onClick={() =>
                    updateSettings({ questionType: option.value })
                  }
                  data-testid={`question-type-card-${option.value}`}
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
            <VStack gap={3} align="stretch" maxW="500px">
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
