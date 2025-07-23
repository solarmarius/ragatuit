import { memo, useCallback } from "react";
import {
  VStack,
  HStack,
  Button,
  Text,
  Box,
  SimpleGrid,
  Card,
  IconButton,
  Textarea,
  Input,
} from "@chakra-ui/react";
import { useForm, useFieldArray, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { MdAdd, MdDelete } from "react-icons/md";
import type { QuestionResponse, QuestionUpdateRequest } from "@/client";
import { extractQuestionData } from "@/types/questionTypes";
import type { CategorizationFormData } from "@/lib/validation/questionSchemas";
import { categorizationSchema } from "@/lib/validation/questionSchemas";
import { FormField, FormGroup } from "@/components/forms";
import { ErrorEditor } from "./ErrorEditor";

interface CategorizationEditorProps {
  question: QuestionResponse;
  onSave: (updateData: QuestionUpdateRequest) => void;
  onCancel: () => void;
  isLoading?: boolean;
}

/**
 * Editor component for categorization questions.
 * Allows editing of categories, items, item assignments, distractors, and explanation.
 */
function CategorizationEditorComponent({
  question,
  onSave,
  onCancel,
  isLoading = false,
}: CategorizationEditorProps) {
  try {
    const categorizationData = extractQuestionData(question, "categorization");

    // Transform backend data to form data format
    const defaultFormData: CategorizationFormData = {
      questionText: categorizationData.question_text,
      categories: categorizationData.categories.map((cat) => ({
        name: cat.name,
        correctItems: cat.correct_items,
      })),
      items: categorizationData.items.map((item) => ({
        text: item.text,
      })),
      distractors: categorizationData.distractors?.map((dist) => ({
        text: dist.text,
      })) || [],
      explanation: categorizationData.explanation || "",
    };

    const {
      control,
      handleSubmit,
      formState: { errors, isDirty },
    } = useForm<CategorizationFormData>({
      resolver: zodResolver(categorizationSchema),
      defaultValues: defaultFormData,
    });

    // Field arrays for dynamic management
    const {
      fields: categoryFields,
      append: appendCategory,
      remove: removeCategory,
    } = useFieldArray({
      control,
      name: "categories",
    });

    const {
      fields: itemFields,
      append: appendItem,
      remove: removeItem,
    } = useFieldArray({
      control,
      name: "items",
    });

    const {
      fields: distractorFields,
      append: appendDistractor,
      remove: removeDistractor,
    } = useFieldArray({
      control,
      name: "distractors",
    });

    // Note: Item assignment to categories will be implemented in future version

    // Handle form submission
    const onSubmit = useCallback(
      (formData: CategorizationFormData) => {
        // Transform form data back to backend format
        const updateData: QuestionUpdateRequest = {
          question_data: {
            question_text: formData.questionText,
            categories: formData.categories.map((cat, index) => ({
              id: `cat_${index}`, // Generate IDs for new categories
              name: cat.name,
              correct_items: cat.correctItems,
            })),
            items: formData.items.map((item, index) => ({
              id: `item_${index}`, // Generate IDs for new items
              text: item.text,
            })),
            distractors: formData.distractors?.length
              ? formData.distractors.map((dist, index) => ({
                  id: `dist_${index}`, // Generate IDs for new distractors
                  text: dist.text,
                }))
              : null,
            explanation: formData.explanation || null,
          },
        };
        onSave(updateData);
      },
      [onSave]
    );

    // Add new category
    const handleAddCategory = useCallback(() => {
      if (categoryFields.length < 8) {
        appendCategory({ name: "", correctItems: [] });
      }
    }, [appendCategory, categoryFields.length]);

    // Add new item
    const handleAddItem = useCallback(() => {
      if (itemFields.length < 20) {
        appendItem({ text: "" });
      }
    }, [appendItem, itemFields.length]);

    // Add new distractor
    const handleAddDistractor = useCallback(() => {
      if (distractorFields.length < 5) {
        appendDistractor({ text: "" });
      }
    }, [appendDistractor, distractorFields.length]);

    return (
      <Box as="form" onSubmit={handleSubmit(onSubmit)}>
        <VStack gap={8} align="stretch">
          {/* Question Text */}
          <FormField
            label="Question Text"
            isRequired
            error={errors.questionText?.message}
          >
            <Controller
              name="questionText"
              control={control}
              render={({ field }) => (
                <Textarea
                  {...field}
                  placeholder="Enter instructions for the categorization question..."
                  rows={3}
                />
              )}
            />
          </FormField>

          {/* Categories Section */}
          <FormGroup>
            <HStack justify="space-between" mb={4}>
              <Text fontSize="md" fontWeight="semibold">
                Categories ({categoryFields.length}/8)
              </Text>
              <Button
                size="sm"
                onClick={handleAddCategory}
                disabled={categoryFields.length >= 8}
                colorScheme="blue"
                variant="outline"
              >
                <MdAdd />
                Add Category
              </Button>
            </HStack>

            {errors.categories && (
              <Text color="red.500" fontSize="sm" mb={3}>
                {errors.categories.message}
              </Text>
            )}

            <SimpleGrid columns={{ base: 1, md: 2 }} gap={4}>
              {categoryFields.map((field, index) => (
                <Card.Root key={field.id} variant="outline">
                  <Card.Header>
                    <HStack justify="space-between">
                      <Text fontSize="sm" fontWeight="medium">
                        Category {index + 1}
                      </Text>
                      <IconButton
                        aria-label={`Remove category ${index + 1}`}
                        size="sm"
                        colorScheme="red"
                        variant="ghost"
                        onClick={() => removeCategory(index)}
                        disabled={categoryFields.length <= 2}
                      >
                        <MdDelete />
                      </IconButton>
                    </HStack>
                  </Card.Header>
                  <Card.Body>
                    <VStack gap={3} align="stretch">
                      <FormField
                        label="Category Name"
                        isRequired
                        error={errors.categories?.[index]?.name?.message}
                      >
                        <Controller
                          name={`categories.${index}.name`}
                          control={control}
                          render={({ field: inputField }) => (
                            <Input
                              {...inputField}
                              placeholder="Enter category name..."
                              size="sm"
                            />
                          )}
                        />
                      </FormField>

                      <FormField
                        label="Assigned Items"
                        error={errors.categories?.[index]?.correctItems?.message}
                      >
                        <Text fontSize="sm" color="gray.600">
                          Category assignment will be implemented in a future version.
                          For now, items are automatically distributed among categories.
                        </Text>
                      </FormField>
                    </VStack>
                  </Card.Body>
                </Card.Root>
              ))}
            </SimpleGrid>

            <Text fontSize="sm" color="gray.600" mt={2}>
              At least 2 categories required, maximum 8 categories allowed.
            </Text>
          </FormGroup>

          {/* Items Section */}
          <FormGroup>
            <HStack justify="space-between" mb={4}>
              <Text fontSize="md" fontWeight="semibold">
                Items ({itemFields.length}/20)
              </Text>
              <Button
                size="sm"
                onClick={handleAddItem}
                disabled={itemFields.length >= 20}
                colorScheme="blue"
                variant="outline"
              >
                <MdAdd />
                Add Item
              </Button>
            </HStack>

            {errors.items && (
              <Text color="red.500" fontSize="sm" mb={3}>
                {errors.items.message}
              </Text>
            )}

            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={3}>
              {itemFields.map((field, index) => (
                <Card.Root key={field.id} variant="outline" size="sm">
                  <Card.Body>
                    <HStack>
                      <Box flex={1}>
                        <FormField
                          label={`Item ${index + 1}`}
                          isRequired
                          error={errors.items?.[index]?.text?.message}
                        >
                          <Controller
                            name={`items.${index}.text`}
                            control={control}
                            render={({ field: inputField }) => (
                              <Input
                                {...inputField}
                                placeholder="Enter item text..."
                                size="sm"
                              />
                            )}
                          />
                        </FormField>
                      </Box>
                      <IconButton
                        aria-label={`Remove item ${index + 1}`}
                        size="sm"
                        colorScheme="red"
                        variant="ghost"
                        onClick={() => removeItem(index)}
                        disabled={itemFields.length <= 6}
                        alignSelf="flex-end"
                        mb={2}
                      >
                        <MdDelete />
                      </IconButton>
                    </HStack>
                  </Card.Body>
                </Card.Root>
              ))}
            </SimpleGrid>

            <Text fontSize="sm" color="gray.600" mt={2}>
              At least 6 items required, maximum 20 items allowed.
            </Text>
          </FormGroup>

          {/* Distractors Section */}
          <FormGroup>
            <HStack justify="space-between" mb={4}>
              <Text fontSize="md" fontWeight="semibold">
                Distractors ({distractorFields.length}/5)
              </Text>
              <Button
                size="sm"
                onClick={handleAddDistractor}
                disabled={distractorFields.length >= 5}
                colorScheme="blue"
                variant="outline"
              >
                <MdAdd />
                Add Distractor
              </Button>
            </HStack>

            {errors.distractors && (
              <Text color="red.500" fontSize="sm" mb={3}>
                {errors.distractors.message}
              </Text>
            )}

            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={3}>
              {distractorFields.map((field, index) => (
                <Card.Root key={field.id} variant="outline" size="sm">
                  <Card.Body>
                    <HStack>
                      <Box flex={1}>
                        <FormField
                          label={`Distractor ${index + 1}`}
                          error={errors.distractors?.[index]?.text?.message}
                        >
                          <Controller
                            name={`distractors.${index}.text`}
                            control={control}
                            render={({ field: inputField }) => (
                              <Input
                                {...inputField}
                                placeholder="Enter distractor text..."
                                size="sm"
                              />
                            )}
                          />
                        </FormField>
                      </Box>
                      <IconButton
                        aria-label={`Remove distractor ${index + 1}`}
                        size="sm"
                        colorScheme="red"
                        variant="ghost"
                        onClick={() => removeDistractor(index)}
                        alignSelf="flex-end"
                        mb={2}
                      >
                        <MdDelete />
                      </IconButton>
                    </HStack>
                  </Card.Body>
                </Card.Root>
              ))}
            </SimpleGrid>

            <Text fontSize="sm" color="gray.600" mt={2}>
              Optional incorrect items that don't belong to any category. Maximum 5 allowed.
            </Text>
          </FormGroup>

          {/* Explanation */}
          <FormField
            label="Explanation (Optional)"
            error={errors.explanation?.message}
          >
            <Controller
              name="explanation"
              control={control}
              render={({ field }) => (
                <Textarea
                  {...field}
                  placeholder="Optional explanation for the correct categorization..."
                  rows={3}
                />
              )}
            />
          </FormField>

          {/* Action Buttons */}
          <HStack gap={3} justify="end" pt={4}>
            <Button variant="outline" onClick={onCancel} disabled={isLoading}>
              Cancel
            </Button>
            <Button
              type="submit"
              colorScheme="blue"
              loading={isLoading}
              disabled={!isDirty}
            >
              Save Changes
            </Button>
          </HStack>
        </VStack>
      </Box>
    );
  } catch (error) {
    console.error("Error rendering categorization question editor:", error);
    return (
      <ErrorEditor
        error="Error loading question data for editing"
        onCancel={onCancel}
      />
    );
  }
}

/**
 * Memoized categorization editor component for performance optimization.
 */
export const CategorizationEditor = memo(CategorizationEditorComponent);
CategorizationEditor.displayName = "CategorizationEditor";
