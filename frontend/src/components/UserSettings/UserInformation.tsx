import {
  Alert,
  Box,
  Button,
  Container,
  Flex,
  Heading,
  Input,
  Link,
  Text,
} from "@chakra-ui/react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { type SubmitHandler, useForm } from "react-hook-form"

import {
  type ApiError,
  type UserPublic,
  type UserUpdateMe,
  UsersService,
} from "@/client"
import useAuth from "@/hooks/useCanvasAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { Field } from "../ui/field"

const UserInformation = () => {
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()
  const [editMode, setEditMode] = useState(false)
  const { user: currentUser } = useAuth()
  const {
    register,
    handleSubmit,
    reset,
    getValues,
    formState: { isSubmitting, isDirty },
  } = useForm<UserPublic>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      name: currentUser?.name,
    },
  })

  const toggleEditMode = () => {
    setEditMode(!editMode)
  }

  const mutation = useMutation({
    mutationFn: (data: UserUpdateMe) =>
      UsersService.updateUserMe({ requestBody: data }),
    onSuccess: () => {
      showSuccessToast("User updated successfully.")
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
    onSettled: () => {
      queryClient.invalidateQueries()
    },
  })

  const onSubmit: SubmitHandler<UserUpdateMe> = async (data) => {
    mutation.mutate(data)
  }

  const onCancel = () => {
    reset()
    toggleEditMode()
  }

  return (
    <>
      <Container maxW="full">
        <Heading size="sm" py={4}>
          User Information
        </Heading>
        <Box
          w={{ sm: "full", md: "sm" }}
          as="form"
          onSubmit={handleSubmit(onSubmit)}
        >
          <Field label="Name">
            {editMode ? (
              <Input
                {...register("name", { maxLength: 30 })}
                type="text"
                size="md"
              />
            ) : (
              <Text
                fontSize="md"
                py={2}
                color={!currentUser?.name ? "gray" : "inherit"}
                truncate
                maxW="sm"
              >
                {currentUser?.name || "N/A"}
              </Text>
            )}
          </Field>
          <Flex mt={4} gap={3}>
            <Button
              variant="solid"
              onClick={toggleEditMode}
              type={editMode ? "button" : "submit"}
              loading={editMode ? isSubmitting : false}
              disabled={editMode ? !isDirty || !getValues("name") : false}
            >
              {editMode ? "Save" : "Edit"}
            </Button>
            {editMode && (
              <Button
                variant="subtle"
                colorPalette="gray"
                onClick={onCancel}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
            )}
          </Flex>
        </Box>

        <Alert.Root status="info" variant="subtle" mt={6} colorPalette="teal">
          <Alert.Content>
            <Alert.Description>
              Review our{" "}
              <Link
                href="/privacy-policy"
                color="blue.500"
                textDecoration="underline"
              >
                Privacy Policy
              </Link>{" "}
              to understand how we handle your data.
            </Alert.Description>
          </Alert.Content>
        </Alert.Root>
      </Container>
    </>
  )
}

export default UserInformation
