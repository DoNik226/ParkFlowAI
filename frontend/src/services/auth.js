import apiClient from './api-client'

export const authService = {
  // мок-данные для тестирования без бэкенда
  async login(username, password) {
    // Имитация задержки сети
    await new Promise(resolve => setTimeout(resolve, 500))

    // Тестовые учётные данные
    if (username === 'admin') {
      return {
        token: 'mock-jwt-token-admin',
        role: 'admin',
        user_id: 1
      }
    } else {
      return {
        token: 'mock-jwt-token-user',
        role: 'user',
        user_id: 12345
      }
    }

    // Реальный запрос:
    /*
    const response = await apiClient.post('/auth/login', {
      username,
      password,
    })
    return response.data
    */
  },

  async forgotPassword(username) {
    await new Promise(resolve => setTimeout(resolve, 500))
    return { message: 'Новый пароль отправлен на email' }
  },

  async logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_role')
    localStorage.removeItem('user_id')
  }
}