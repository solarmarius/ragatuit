import { OpenAPI, type UserPublic, UsersService, AuthService } from "@/client";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";

const isLoggedIn = () => {
  return localStorage.getItem("access_token") !== null;
};

const useAuth = () => {
  const navigate = useNavigate();
  const { data: user } = useQuery<UserPublic | null, Error>({
    queryKey: ["currentUser"],
    queryFn: UsersService.readUserMe,
    enabled: isLoggedIn(),
  });

  const initiateCanvasLogin = () => {
    // Simply redirect to the backend endpoint - it will handle the Canvas redirect
    window.location.href = `${OpenAPI.BASE}/api/v1/auth/login/canvas`;
  };

  const logout = async () => {
    try {
      await AuthService.logoutCanvas();
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      localStorage.removeItem("access_token");
      navigate({ to: "/login" });
    }
  };

  return {
    initiateCanvasLogin,
    logout,
    user,
  };
};

export { isLoggedIn };
export default useAuth;
