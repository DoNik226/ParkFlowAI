import axios from 'axios'

const apiClient = axios.create({
  baseURL: 'http://localhost:8000', // Адрес вашего backend (раздел 4.3 документа)
  headers: {
    'Content-Type': 'application/json',
  },
})

// Автоматическое добавление JWT токена к запросам (раздел 4.5)
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default apiClient