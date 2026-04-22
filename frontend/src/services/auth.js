import apiClient from './api-client'

/**
 * Сервис аутентификации и авторизации
 */
export const authService = {
  /**
   * POST /auth/login — Вход в систему
   * @param {string} username - Логин пользователя
   * @param {string} password - Пароль пользователя
   * @returns {Promise<{token: string, role: string, user_id: number}>}
   */
  async login(username, password) {
    // ===== ФЛАГ ПЕРЕКЛЮЧЕНИЯ РЕЖИМА =====
    // true = mock-данные 
    // false = реальный API 
    const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true' || true

    if (USE_MOCK) {
      // ===== MOCK-РЕЖИМ: имитация задержки сети =====
      await new Promise(resolve => setTimeout(resolve, 500))

      // Тестовые учётные данные
      if (username === 'admin' && password === 'admin') {
        return {
          token: 'mock-jwt-token-admin',
          role: 'admin',
          user_id: 1
        }
      } else if (username === 'user' && password === 'user') {
        return {
          token: 'mock-jwt-token-user',
          role: 'user',
          user_id: 12345
        }
      } else {
        // Имитация ошибки 401
        const error = new Error('Неверный логин или пароль')
        error.response = { status: 401 }
        throw error
      }
    }

    // ===== REAL-РЕЖИМ: реальный запрос к API =====
    const response = await apiClient.post('/auth/login', {
      username,
      password,
    })
    return response.data
  },

  /**
   * POST /auth/forgot-password — Запрос на сброс пароля
   * @param {string} username - Логин пользователя
   * @returns {Promise<{message: string}>}
   */
  async forgotPassword(username) {
    const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true' || true

    if (USE_MOCK) {
      // ===== MOCK-РЕЖИМ =====
      await new Promise(resolve => setTimeout(resolve, 500))
      return { message: 'Заявка отправлена администратору' }
    }

    // ===== REAL-РЕЖИМ =====
    const response = await apiClient.post('/auth/forgot-password', { username })
    return response.data
  },

  /**
   * POST /auth/logout — Выход из системы
   * @returns {Promise<{message: string}>}
   */
  async logout() {
    const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true' || true

    // Очистка localStorage 
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_role')
    localStorage.removeItem('user_id')

    if (USE_MOCK) {
      // ===== MOCK-РЕЖИМ =====
      await new Promise(resolve => setTimeout(resolve, 300))
      return { message: 'Выход выполнен' }
    }

    // ===== REAL-РЕЖИМ =====
    const token = localStorage.getItem('access_token') // Может быть уже удалён
    const response = await apiClient.post('/auth/logout', { token })
    return response.data
  }
}