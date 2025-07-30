import type { QuestionResponse, QuestionUpdateRequest } from "@/client"
import { FormField, FormGroup } from "@/components/forms"
import type { CategorizationFormData } from "@/lib/validation/questionSchemas"
import {
  categorizationSchema,
  validationMessages,
} from "@/lib/validation/questionSchemas"
import { extractQuestionData } from "@/types/questionTypes"
import {
  Box,
  Button,
  Card,
  HStack,
  IconButton,
  Input,
  SimpleGrid,
  Text,
  Textarea,
  VStack,
} from "@chakra-ui/react"
import { zodResolver } from "@hookform/resolvers/zod"
import { memo, useCallback, useMemo } from "react"
import {
  type Control,
  Controller,
  type FieldErrors,
  useFieldArray,
  useForm,
} from "react-hook-form"
import { MdAdd, MdDelete } from "react-icons/md"
import { ErrorEditor } from "./ErrorEditor"

// Utility function to generate stable IDs
function generateId(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).substr(2, 9)}`
}

interface CategorizationEditorProps {
  question: QuestionResponse
  onSave: (updateData: QuestionUpdateRequest) => void
  onCancel: () => void
  isLoading?: boolean
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
    const categorizationData = extractQuestionData(question, "categorization")

    // Transform backend data to new form data format with stable IDs
    const defaultFormData: CategorizationFormData = useMemo(
      () => ({
        questionText: categorizationData.question_text,
        categories: categorizationData.categories.map((cat) => ({
          id: cat.id, // Preserve existing backend ID
          name: cat.name,
          items: cat.correct_items.map((itemId) => {
            const item = categorizationData.items.find((i) => i.id === itemId)
            return {
              id: itemId, // Preserve existing backend ID
              text: item?.text || "",
            }
          }),
        })),
        distractors:
          categorizationData.distractors?.map((dist) => ({
            id: dist.id, // Preserve existing backend ID
            text: dist.text,
          })) || [],
        explanation: categorizationData.explanation || "",
      }),
      [categorizationData],
    )

    const {
      control,
      handleSubmit,
      formState: { errors, isDirty },
    } = useForm<CategorizationFormData>({
      resolver: zodResolver(categorizationSchema),
      defaultValues: defaultFormData,
    })

    // Field arrays for dynamic management
    const {
      fields: categoryFields,
      append: appendCategory,
      remove: removeCategory,
    } = useFieldArray({
      control,
      name: "categories",
    })

    const {
      fields: distractorFields,
      append: appendDistractor,
      remove: removeDistractor,
    } = useFieldArray({
      control,
      name: "distractors",
    })

    // Handle form submission - transform back to backend format
    const onSubmit = useCallback(
      (formData: CategorizationFormData) => {
        // Use existing stable IDs from form data
        const items: Array<{ id: string; text: string }> = []
        const categories: Array<{
          id: string
          name: string
          correct_items: string[]
        }> = []

        // Process each category and its items with stable IDs
        formData.categories.forEach((formCategory) => {
          const categoryItemIds: string[] = []

          formCategory.items.forEach((formItem) => {
            items.push({
              id: formItem.id, // Use existing stable ID
              text: formItem.text,
            })
            categoryItemIds.push(formItem.id)
          })

          categories.push({
            id: formCategory.id, // Use existing stable ID
            name: formCategory.name,
            correct_items: categoryItemIds,
          })
        })

        const updateData: QuestionUpdateRequest = {
          question_data: {
            question_text: formData.questionText,
            categories,
            items,
            distractors: formData.distractors?.length
              ? formData.distractors.map((dist) => ({
                  id: dist.id, // Use existing stable ID
                  text: dist.text,
                }))
              : null,
            explanation: formData.explanation || null,
          },
        }

        onSave(updateData)
      },
      [onSave],
    )

    // Add new category with one empty item
    const handleAddCategory = useCallback(() => {
      if (categoryFields.length < 8) {
        appendCategory({
          id: generateId("cat"),
          name: "",
          items: [
            {
              id: generateId("item"),
              text: "",
            },
          ],
        })
      }
    }, [appendCategory, categoryFields.length])

    // Add new distractor
    const handleAddDistractor = useCallback(() => {
      if (distractorFields.length < 5) {
        appendDistractor({
          id: generateId("dist"),
          text: "",
        })
      }
    }, [appendDistractor, distractorFields.length])

    return (
      <Box as="form" onSubmit={handleSubmit(onSubmit)}>
        <VStack gap={8} align="stretch">
          {/* Form-level validation errors */}
          {errors.root?.message && (
            <Box
              p={3}
              bg="red.50"
              border="1px"
              borderColor="red.200"
              borderRadius="md"
            >
              <Text color="red.600" fontSize="sm" fontWeight="medium">
                {errors.root.message}
              </Text>
            </Box>
          )}
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

            {errors.categories?.message && (
              <Text color="red.500" fontSize="sm" mb={3}>
                {errors.categories.message}
              </Text>
            )}
            {errors.categories?.root?.message && (
              <Text color="red.500" fontSize="sm" mb={3}>
                {errors.categories.root.message}
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
              {validationMessages.categoriesHelp}
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

            {errors.distractors?.message && (
              <Text color="red.500" fontSize="sm" mb={3}>
                {errors.distractors.message}
              </Text>
            )}
            {errors.distractors?.root?.message && (
              <Text color="red.500" fontSize="sm" mb={3}>
                {errors.distractors.root.message}
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
              {validationMessages.distractorsHelp}
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
    )
  } catch (error) {
    console.error("Error rendering categorization question editor:", error)
    return (
      <ErrorEditor
        error="Error loading question data for editing"
        onCancel={onCancel}
      />
    )
  }
}

/**
 * Individual category editor component matching the display layout
 */
interface CategoryEditorProps {
  categoryIndex: number
  control: Control<CategorizationFormData>
  errors: FieldErrors<CategorizationFormData>
  onRemoveCategory: () => void
  canRemoveCategory: boolean
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
  })

  const handleAddItem = useCallback(() => {
    appendItem({
      id: generateId("item"),
      text: "",
    })
  }, [appendItem])

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
                        <Box>
                          <Input
                            {...inputField}
                            placeholder="Enter item text..."
                            size="sm"
                            bg="green.50"
                            borderColor="green.300"
                          />
                          {errors.categories?.[categoryIndex]?.items?.[
                            itemIndex
                          ]?.text?.message && (
                            <Text color="red.500" fontSize="xs" mt={1}>
                              {
                                errors.categories[categoryIndex]?.items?.[
                                  itemIndex
                                ]?.text?.message
                              }
                            </Text>
                          )}
                        </Box>
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
  )
}

/**
 * Memoized categorization editor component for performance optimization.
 */
export const CategorizationEditor = memo(CategorizationEditorComponent)
CategorizationEditor.displayName = "CategorizationEditor"
