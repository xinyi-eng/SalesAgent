type ErrorResponse = {
  response?: {
    data?: {
      detail?: unknown
    }
  }
}

type MessageError = { message?: unknown }

export function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) return error.message
  if (typeof error === 'object' && error !== null) {
    const responseError = error as ErrorResponse
    if (typeof responseError.response?.data?.detail === 'string') {
      return responseError.response.data.detail
    }
    const messageError = error as MessageError
    if (typeof messageError.message === 'string') return messageError.message
  }
  return fallback
}
