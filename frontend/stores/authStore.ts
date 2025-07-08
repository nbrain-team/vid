import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import axios from 'axios'

interface User {
  id: number
  email: string
  username: string
  full_name?: string
  company?: string
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => void
  setToken: (token: string) => void
}

interface RegisterData {
  email: string
  username: string
  password: string
  full_name?: string
  company?: string
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      login: async (username: string, password: string) => {
        try {
          const formData = new FormData()
          formData.append('username', username)
          formData.append('password', password)

          const response = await axios.post('/api/v1/auth/token', formData)
          const { access_token } = response.data

          // Set token in axios defaults
          axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

          // Get user info
          const userResponse = await axios.get('/api/v1/auth/me')

          set({
            token: access_token,
            user: userResponse.data,
            isAuthenticated: true,
          })
        } catch (error) {
          throw error
        }
      },

      register: async (data: RegisterData) => {
        try {
          await axios.post('/api/v1/auth/register', data)
          // Auto login after registration
          await useAuthStore.getState().login(data.username, data.password)
        } catch (error) {
          throw error
        }
      },

      logout: () => {
        delete axios.defaults.headers.common['Authorization']
        set({
          user: null,
          token: null,
          isAuthenticated: false,
        })
      },

      setToken: (token: string) => {
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
        set({ token })
      },
    }),
    {
      name: 'auth-storage',
      onRehydrateStorage: () => (state) => {
        if (state?.token) {
          axios.defaults.headers.common['Authorization'] = `Bearer ${state.token}`
        }
      },
    }
  )
) 