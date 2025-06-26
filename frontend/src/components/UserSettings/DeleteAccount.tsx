import { Heading, Text, VStack } from "@chakra-ui/react"

import DeleteConfirmation from "./DeleteConfirmation"

const DeleteAccount = () => {
  return (
    <VStack align="stretch" gap={4} w="75%">
      <Heading size="xl">Delete Account</Heading>
      <Text>
        Permanently delete your data and everything associated with your
        account.
      </Text>
      <Text>
        This includes any quizzes you have created. Make sure that any ongoing
        quizzes are completed before proceeding, as they will also be deleted.
      </Text>
      <DeleteConfirmation />
    </VStack>
  )
}
export default DeleteAccount
