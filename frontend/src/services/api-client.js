import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000, // Таймаут 10 секунд
})

// Автоматическое добавление JWT токена к запросам
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Централизованная обработка ошибок
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Обработка 401 Unauthorized
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user_role')
      localStorage.removeItem('user_id')
      
      // Перенаправление на логин (если не на странице входа)
      if (window.location.pathname !== '/') {
        window.location.href = '/'
      }
    }
    
    // Обработка 403 Forbidden
    if (error.response?.status === 403) {
      console.error('Доступ запрещён')
    }
    
    // Обработка 500 Internal Server Error
    if (error.response?.status === 500) {
      console.error('Внутренняя ошибка сервера')
    }
    
    return Promise.reject(error)
  }
)

export default apiClient