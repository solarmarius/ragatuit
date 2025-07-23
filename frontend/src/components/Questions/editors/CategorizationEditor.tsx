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
 * Allows editing of categories with their items, distractors, and explanation.
 * Mirrors the layout of CategorizationDisplay for intuitive editing.
 */
function CategorizationEditorComponent({
  question,
  onSave,
  onCancel,
  isLoading = false,
}: CategorizationEditorProps) {
  try {
    const categorizationData = extractQuestionData(question, "categorization");

    // Transform backend data to new form data format
    const defaultFormData: CategorizationFormData = {
      questionText: categorizationData.question_text,
      categories: categorizationData.categories.map((cat) => ({
        name: cat.name,
        items: cat.correct_items.map((itemId) => {
          const item = categorizationData.items.find((i) => i.id === itemId);
          return { text: item?.text || "" };
        }),
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
      fields: distractorFields,
      append: appendDistractor,
      remove: removeDistractor,
    } = useFieldArray({
      control,
      name: "distractors",
    });

    // Handle form submission - transform back to backend format
    const onSubmit = useCallback(
      (formData: CategorizationFormData) => {
        // Generate items array and category mappings
        const items: Array<{ id: string; text: string }> = [];
        const categories: Array<{
          id: string;
          name: string;
          correct_items: string[];
        }> = [];

        let itemIndex = 0;

        // Process each category and its items
        formData.categories.forEach((formCategory, catIndex) => {
          const categoryItemIds: string[] = [];

          formCategory.items.forEach((formItem) => {
            const itemId = `item_${itemIndex}`;
            items.push({
              id: itemId,
              text: formItem.text,
            });
            categoryItemIds.push(itemId);
            itemIndex++;
          });

          categories.push({
            id: `cat_${catIndex}`,
            name: formCategory.name,
            correct_items: categoryItemIds,
          });
        });

        const updateData: QuestionUpdateRequest = {
          question_data: {
            question_text: formData.questionText,
            categories,
            items,
            distractors: formData.distractors?.length
              ? formData.distractors.map((dist, index) => ({
                  id: `dist_${index}`,
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

    // Add new category with one empty item
    const handleAddCategory = useCallback(() => {
      if (categoryFields.length < 8) {
        appendCategory({
          name: "",
          items: [{ text: "" }]
        });
      }
    }, [appendCategory, categoryFields.length]);

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

          {/* Categories Section - Mirrors Display Layout */}
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

            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={4}>
              {categoryFields.map((field, categoryIndex) => (
                <CategoryEditor
                  key={field.id}
                  categoryIndex={categoryIndex}
                  control={control}
                  errors={errors}
                  onRemoveCategory={() => removeCategory(categoryIndex)}
                  canRemoveCategory={categoryFields.length > 2}
                />
              ))}
            </SimpleGrid>

            <Text fontSize="sm" color="gray.600" mt={2}>
              At least 2 categories required, maximum 8 categories allowed.
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

            <SimpleGrid columns={{ base: 2, md: 3, lg: 4 }} gap={3}>
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
 * Individual category editor component matching the display layout
 */
interface CategoryEditorProps {
  categoryIndex: number;
  control: any;
  errors: any;
  onRemoveCategory: () => void;
  canRemoveCategory: boolean;
}

function CategoryEditor({
  categoryIndex,
  control,
  errors,
  onRemoveCategory,
  canRemoveCategory,
}: CategoryEditorProps) {
  const {
    fields: itemFields,
    append: appendItem,
    remove: removeItem,
  } = useFieldArray({
    control,
    name: `categories.${categoryIndex}.items`,
  });

  const handleAddItem = useCallback(() => {
    appendItem({ text: "" });
  }, [appendItem]);

  return (
    <Card.Root variant="outline">
      <Card.Header>
        <HStack justify="space-between">
          <Text fontSize="sm" fontWeight="medium">
            Category {categoryIndex + 1}
          </Text>
          <IconButton
            aria-label={`Remove category ${categoryIndex + 1}`}
            size="sm"
            colorScheme="red"
            variant="ghost"
            onClick={onRemoveCategory}
            disabled={!canRemoveCategory}
          >
            <MdDelete />
          </IconButton>
        </HStack>
      </Card.Header>
      <Card.Body>
        <VStack gap={3} align="stretch">
          {/* Category Name */}
          <FormField
            label="Category Name"
            isRequired
            error={errors.categories?.[categoryIndex]?.name?.message}
          >
            <Controller
              name={`categories.${categoryIndex}.name`}
              control={control}
              render={({ field }) => (
                <Input
                  {...field}
                  placeholder="Enter category name..."
                  size="sm"
                />
              )}
            />
          </FormField>

          {/* Items in Category */}
          <Box>
            <HStack justify="space-between" mb={2}>
              <Text fontSize="sm" fontWeight="medium">
                Items ({itemFields.length})
              </Text>
              <Button
                size="xs"
                onClick={handleAddItem}
                colorScheme="green"
                variant="outline"
              >
                <MdAdd />
                Add Item
              </Button>
            </HStack>

            <VStack gap={2} align="stretch">
              {itemFields.map((field, itemIndex) => (
                <HStack key={field.id}>
                  <Box flex={1}>
                    <Controller
                      name={`categories.${categoryIndex}.items.${itemIndex}.text`}
                      control={control}
                      render={({ field: inputField }) => (
                        <Input
                          {...inputField}
                          placeholder="Enter item text..."
                          size="sm"
                          bg="green.50"
                          borderColor="green.300"
                        />
                      )}
                    />
                  </Box>
                  <IconButton
                    aria-label={`Remove item ${itemIndex + 1}`}
                    size="sm"
                    colorScheme="red"
                    variant="ghost"
                    onClick={() => removeItem(itemIndex)}
                    disabled={itemFields.length <= 1}
                  >
                    <MdDelete />
                  </IconButton>
                </HStack>
              ))}
            </VStack>

            {errors.categories?.[categoryIndex]?.items && (
              <Text color="red.500" fontSize="sm" mt={1}>
                {errors.categories?.[categoryIndex]?.items?.message}
              </Text>
            )}
          </Box>
        </VStack>
      </Card.Body>
    </Card.Root>
  );
}

/**
 * Memoized categorization editor component for performance optimization.
 */
export const CategorizationEditor = memo(CategorizationEditorComponent);
CategorizationEditor.displayName = "CategorizationEditor";
