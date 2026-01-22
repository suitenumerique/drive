import { baseApiUrl } from '../api/utils'

export const authUrl = ({
  silent = false,
  returnTo = window.location.href,
} = {}) => {
  return new URL(
    `authenticate/?silent=${encodeURIComponent(silent)}&returnTo=${encodeURIComponent(returnTo)}`,
    baseApiUrl()
  )
}
