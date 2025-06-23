import { Container, Heading, Text } from "@chakra-ui/react"

import DeleteConfirmation from "./DeleteConfirmation"

const DeleteAccount = () => {
  return (
    <Container maxW="full">
      <Heading size="sm" py={4}>
        Delete Account
      </Heading>
      <Text>
        Permanently delete your data and everything associated with your
        account.
      </Text>
      <Text>
        This includes any quizzes you have created. Make sure that any ongoing
        quizzes are completed before proceeding, as they will also be deleted.
      </Text>
      <DeleteConfirmation />
    </Container>
  )
}
export default DeleteAccount
