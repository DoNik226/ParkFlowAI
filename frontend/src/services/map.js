import apiClient from './api-client'

/**
 * Сервис работы с картой и маршрутами
 */
export const mapService = {
  /**
   * Построить маршрут от въезда до места
   * POST /routes
   */
  async buildRoute(entranceId, spotId) {
    const response = await apiClient.post('/routes', {
      entrance_id: entranceId,
      spot_id: spotId
    })
    return response.data
  },

  /**
   * Найти ближайшую свободную парковку
   * GET /parkings/{id}/nearest?entrance_id=1
   */
  async getNearestParking(parkingId, entranceId) {
    const response = await apiClient.get(`/parkings/${parkingId}/nearest`, {
      params: { entrance_id: entranceId }
    })
    return response.data
  },

  /**
   * Получить объекты карты (здания, дороги, парковки, камеры, въезды)
   * GET /map/objects
   */
  async getMapObjects() {
    const response = await apiClient.get('/map/objects')
    return response.data
  }
}