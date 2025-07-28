import { Heading, Text, VStack } from "@chakra-ui/react"

import DeleteConfirmation from "./DeleteConfirmation"

const DeleteAccount = () => {
  return (
    <VStack align="stretch" gap={4} w="75%">
      <Heading size="xl">Delete Account</Heading>
      <Text>
        Permanently delete your user. The quizzes and question associated will
        not be deleted, but the corresponding user ID of the quiz will be
        nullified.
      </Text>
      <Text>
        Make sure that any ongoing quizzes are completed before proceeding, as
        they will also be deleted.
      </Text>
      <DeleteConfirmation />
    </VStack>
  )
}
export default DeleteAccount
