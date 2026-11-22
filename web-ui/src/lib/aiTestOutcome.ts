export interface AiTestResponse {
  success: boolean
  message: string
  response?: string
}

export function getAiTestNotice(result: AiTestResponse): {
  kind: 'success' | 'error'
  text: string
} {
  if (!result.success) {
    return { kind: 'error', text: result.message }
  }

  return {
    kind: 'success',
    text: result.response?.trim() || result.message,
  }
}

export function formatAiTestSuccessDescription(template: string, response: string): string {
  return template.replace('{response}', () => response)
}
