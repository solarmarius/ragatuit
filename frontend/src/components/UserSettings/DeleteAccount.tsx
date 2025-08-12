import { Heading, Text, VStack } from "@chakra-ui/react"

import DeleteConfirmation from "./DeleteConfirmation"

const DeleteAccount = () => {
  return (
    <VStack align="stretch" gap={4} w="75%">
      <Heading size="xl">Delete Account</Heading>
      <Text>
        This will delete all your user data. Quizzes and questions you created
        will not be deleted, but they will no longer be connected to your
        account. The user ID of your quizzes will be set to "NULL".
      </Text>
      <Text>
        Make sure that any ongoing quizzes are completed before proceeding.
      </Text>
      <DeleteConfirmation />
    </VStack>
  )
}
export default DeleteAccount
