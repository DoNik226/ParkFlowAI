import apiClient from './api-client'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'

function normalizeLoginResponse(data) {
  return {
    token: data.token || data.access_token,
    role: data.role || data.user_role || data.user?.role || 'user',
    user_id: data.user_id || data.user?.id || null,
    raw: data,
  }
}

export const authService = {
  async login(username, password) {
    if (USE_MOCK) {
      await new Promise(resolve => setTimeout(resolve, 300))

      if (username === 'admin' && password === 'admin') {
        return {
          token: 'mock-jwt-token-admin',
          role: 'admin',
          user_id: 1,
        }
      }

      if (username === 'user' && password === 'user') {
        return {
          token: 'mock-jwt-token-user',
          role: 'user',
          user_id: 12345,
        }
      }

      const error = new Error('Неверный логин или пароль')
      error.response = { status: 401 }
      throw error
    }

    const response = await apiClient.post('/auth/login', {
      login: username,
      username,
      password,
    })

    return normalizeLoginResponse(response.data)
  },

  async forgotPassword(username) {
    if (USE_MOCK) {
      await new Promise(resolve => setTimeout(resolve, 300))
      return { message: 'Заявка отправлена администратору' }
    }

    return {
      message: `Пользователь ${username}: восстановление пароля пока не подключено на backend`,
    }
  },

  async logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_role')
    localStorage.removeItem('user_id')
    localStorage.removeItem('username')

    if (USE_MOCK) {
      return { message: 'Выход выполнен' }
    }

    try {
      const response = await apiClient.post('/auth/logout')
      return response.data
    } catch {
      return { message: 'Локальный выход выполнен' }
    }
  },
}