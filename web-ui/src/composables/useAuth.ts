import { ref, computed } from 'vue'
import { useRouter, type Router } from 'vue-router'
import { wsService } from '@/services/websocket'

const username = ref<string | null>(null)
const isLoggedIn = ref(false)
const isAuthReady = ref(false)
let sessionCheckPromise: Promise<boolean> | null = null
let activeRouter: Router | null = null
let socketAuthListenerAdded = false

function setAuthenticated(user: string) {
  username.value = user
  isLoggedIn.value = true
  isAuthReady.value = true
  wsService.start()
}

function clearAuthenticated() {
  username.value = null
  isLoggedIn.value = false
  wsService.stop()
}

function handleSocketUnauthorized() {
  clearAuthenticated()
  isAuthReady.value = true
  void activeRouter?.replace('/login')
}

export function useAuth() {
  const router = useRouter()
  activeRouter = router
  if (!socketAuthListenerAdded) {
    wsService.on('unauthorized', handleSocketUnauthorized)
    socketAuthListenerAdded = true
  }
  const isAuthenticated = computed(() => isLoggedIn.value)

  async function ensureSession(): Promise<boolean> {
    if (isAuthReady.value) return isLoggedIn.value
    if (sessionCheckPromise) return sessionCheckPromise

    sessionCheckPromise = (async () => {
      try {
        const response = await fetch('/auth/session', {
          credentials: 'same-origin',
          cache: 'no-store',
        })
        if (!response.ok) {
          clearAuthenticated()
          return false
        }
        const result = await response.json()
        if (result.authenticated && result.username) {
          setAuthenticated(result.username)
          return true
        }
        clearAuthenticated()
        return false
      } catch {
        clearAuthenticated()
        return false
      } finally {
        isAuthReady.value = true
        sessionCheckPromise = null
      }
    })()

    return sessionCheckPromise
  }

  async function login(user: string, pass: string): Promise<boolean> {
    const response = await fetch('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ username: user, password: pass }),
    })

    if (response.status === 401) return false
    const result = await response.json().catch(() => ({}))
    if (!response.ok) {
      throw new Error(result.detail || `HTTP error! status: ${response.status}`)
    }
    if (!result.authenticated) return false

    setAuthenticated(result.username || user)
    return true
  }

  async function logout() {
    try {
      await fetch('/auth/logout', {
        method: 'POST',
        credentials: 'same-origin',
      })
    } catch {
      // Clear local UI state even if the server is temporarily unreachable.
    }
    clearAuthenticated()
    isAuthReady.value = true
    await router.push('/login')
  }

  return {
    username,
    isAuthenticated,
    isAuthReady,
    ensureSession,
    login,
    logout,
  }
}
