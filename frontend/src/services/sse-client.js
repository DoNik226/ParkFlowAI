/**
 * Клиент для Server-Sent Events (SSE)
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const sseClient = {
  eventSource: null,
  reconnectAttempts: 0,
  maxReconnectAttempts: 5,
  reconnectDelay: 3000,

  /**
   * Подключиться к потоку SSE-обновлений
   * @param {Function} onUpdate - Callback для обработки обновлений
   * @param {Function} onError - Callback для обработки ошибок
   * @returns {Function} - Функция для отключения
   */
  connect(onUpdate, onError) {
    const token = localStorage.getItem('access_token')
    const url = token
      ? `${API_BASE_URL}/sse/updates?token=${token}`
      : `${API_BASE_URL}/sse/updates`

    console.log('Подключение к SSE:', url)

    this.eventSource = new EventSource(url)

    // Обработка обычных сообщений
    this.eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        console.log('SSE событие:', data)
        onUpdate(data)
      } catch (error) {
        console.error('Ошибка парсинга SSE-сообщения:', error)
      }
    }

    // Обработка открытия соединения
    this.eventSource.onopen = () => {
      console.log('SSE-соединение установлено')
      this.reconnectAttempts = 0
    }

    // Обработка ошибок
    this.eventSource.onerror = (error) => {
      console.error('SSE ошибка:', error)

      if (onError) {
        onError(error)
      }

      // Автоматическое переподключение
      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++
        console.log(`Попытка переподключения ${this.reconnectAttempts}/${this.maxReconnectAttempts}...`)

        setTimeout(() => {
          this.close()
          this.connect(onUpdate, onError)
        }, this.reconnectDelay)
      } else {
        console.error('Превышено максимальное количество попыток переподключения SSE')
      }
    }

    // Функция для отключения
    return () => this.close()
  },

  /**
   * Подписаться на обновления конкретной парковки
   */
  subscribeToParking(parkingId, callback) {
    return this.connect(
      (event) => {
        if (event.parking_id === parkingId) {
          callback(event)
        }
      },
      (error) => {
        console.error(`SSE ошибка для парковки ${parkingId}:`, error)
      }
    )
  },

  /**
   * Закрыть SSE-соединение
   */
  close() {
    if (this.eventSource) {
      console.log('Закрытие SSE-соединения')
      this.eventSource.close()
      this.eventSource = null
    }
  }
}