import { AuthService, type UserPublic, UsersService } from '@/client'
import { queryKeys } from '@/lib/api'
import { clearAuthToken, isAuthenticated } from '@/lib/api/client'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'

export function useAuth() {
  const navigate = useNavigate()

  const { data: user, isLoading, error } = useQuery<UserPublic | null, Error>({
    queryKey: queryKeys.auth.currentUser(),
    queryFn: UsersService.readUserMe,
    enabled: isAuthenticated(),
  })

  const initiateCanvasLogin = () => {
    window.location.href = `${import.meta.env.VITE_API_URL}/api/v1/auth/login/canvas`
  }

  const logout = async () => {
    try {
      await AuthService.logoutCanvas()
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      clearAuthToken()
      navigate({ to: '/login' })
    }
  }

  return {
    user,
    isLoading,
    error,
    isAuthenticated: isAuthenticated(),
    initiateCanvasLogin,
    logout,
  }
}
