import { OpenAPI } from "@/client"
import { STORAGE_KEYS } from "@/lib/constants"

export const configureApiClient = () => {
  OpenAPI.BASE = import.meta.env.VITE_API_URL
  OpenAPI.TOKEN = async () => {
    return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN) || ""
  }
}

export const isAuthenticated = (): boolean => {
  return localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN) !== null
}

export const clearAuthToken = (): void => {
  localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN)
}

export const setAuthToken = (token: string): void => {
  localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, token)
}
