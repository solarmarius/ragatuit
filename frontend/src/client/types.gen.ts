// This file is auto-generated by @hey-api/openapi-ts

export type HTTPValidationError = {
  detail?: Array<ValidationError>
}

export type Message = {
  message: string
}

export type UserPublic = {
  name: string
}

export type UserUpdateMe = {
  name: string
}

export type ValidationError = {
  loc: Array<string | number>
  msg: string
  type: string
}

export type AuthLoginCanvasResponse = unknown

export type AuthAuthCanvasResponse = unknown

export type AuthLogoutCanvasResponse = unknown

export type AuthRefreshCanvasTokenResponse = unknown

export type UsersReadUserMeResponse = UserPublic

export type UsersDeleteUserMeResponse = Message

export type UsersUpdateUserMeData = {
  requestBody: UserUpdateMe
}

export type UsersUpdateUserMeResponse = UserPublic

export type UtilsHealthCheckResponse = boolean
