import { UsersService } from "@/client"
import ConfirmationDialog from "@/components/ui/confirmation-dialog"
import { useAuth } from "@/hooks/auth"
import { queryKeys } from "@/lib/queryConfig"

const DeleteConfirmation = () => {
  const { logout } = useAuth()

  return (
    <ConfirmationDialog
      triggerButtonText="Delete"
      triggerButtonProps={{ mt: 4 }}
      title="Confirmation Required"
      message="All your account data will be <strong>permanently deleted.</strong> If you are sure, please click <strong>'Delete'</strong> to proceed. This action cannot be undone."
      confirmButtonText="Delete"
      successMessage="Your account has been successfully deleted"
      mutationFn={() => UsersService.deleteUserMe()}
      onSuccess={logout}
      invalidateQueries={[[...queryKeys.user()]]}
    />
  )
}

export default DeleteConfirmation
