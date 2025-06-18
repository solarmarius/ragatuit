import { OpenAPI } from "@/client";
import { useNavigate } from "@tanstack/react-router";

const isLoggedIn = () => {
  return localStorage.getItem("access_token") !== null;
};

const useCanvasAuth = () => {
  const navigate = useNavigate();

  const initiateCanvasLogin = () => {
    // Simply redirect to the backend endpoint - it will handle the Canvas redirect
    window.location.href = `${OpenAPI.BASE}/api/v1/auth/login/canvas`;
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    navigate({ to: "/login" });
  };

  return {
    initiateCanvasLogin,
    logout,
  };
};

export { isLoggedIn };
export default useCanvasAuth;
