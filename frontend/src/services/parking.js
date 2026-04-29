import apiClient from './api-client'

/**
 * Сервис работы с парковками
 */
export const parkingService = {
  /**
   * Получить список всех парковок
   * GET /parkings
   */
  async getAllParkings() {
    const response = await apiClient.get('/parkings')
    return response.data
  },

  /**
   * Получить данные конкретной парковки
   * GET /parkings/{id}
   */
  async getParkingById(id) {
    const response = await apiClient.get(`/parkings/${id}`)
    return response.data
  },

  /**
   * Создать парковку (только админ)
   * POST /parkings
   */
  async createParking(parkingData) {
    const response = await apiClient.post('/parkings', parkingData)
    return response.data
  },

  /**
   * Обновить парковку (только админ)
   * PUT /parkings/{id}
   */
  async updateParking(id, parkingData) {
    const response = await apiClient.put(`/parkings/${id}`, parkingData)
    return response.data
  },

  /**
   * Удалить парковку (только админ)
   * DELETE /parkings/{id}
   */
  async deleteParking(id) {
    const response = await apiClient.delete(`/parkings/${id}`)
    return response.data
  },

  /**
   * Получить кэш загруженности парковки
   * GET /parkings/{id}/occupancy
   */
  async getParkingOccupancy(id) {
    const response = await apiClient.get(`/parkings/${id}/occupancy`)
    return response.data
  },

  /**
   * Получить места парковки
   * GET /parkings/{id}/spots
   */
  async getParkingSpots(id) {
    const response = await apiClient.get(`/parkings/${id}/spots`)
    return response.data
  },

  /**
   * Получить свободные места с расстояниями
   * GET /parkings/{id}/free-spots?entrance_id=1
   */
  async getFreeSpots(parkingId, entranceId) {
    const response = await apiClient.get(`/parkings/${parkingId}/free-spots`, {
      params: { entrance_id: entranceId }
    })
    return response.data
  },

  /**
   * Изменить статус места (только админ)
   * PUT /parking-spots/{id}/status
   */
  async updateSpotStatus(id, status) {
    const response = await apiClient.put(`/parking-spots/${id}/status`, { status })
    return response.data
  },

  /**
   * Получить точки въезда
   * GET /parkings/{id}/entrances
   */
  async getEntrances(parkingId) {
    const response = await apiClient.get(`/parkings/${parkingId}/entrances`)
    return response.data
  }
}