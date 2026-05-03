import apiClient from './api-client'

/**
 * Сервис работы с картой и маршрутами
 */
export const mapService = {
  /**
   * Построить маршрут от въезда до места.
   *
   * Новый вызов:
   *   buildRoute(parkingId, entranceId, spotId)
   *
   * Для совместимости оставлен старый вариант buildRoute(entranceId, spotId),
   * но лучше всегда передавать parkingId, чтобы backend не угадывал парковку.
   */
  async buildRoute(parkingId, entranceId, spotId) {
    let payload

    if (spotId === undefined) {
      payload = {
        entrance_id: parkingId,
        spot_id: entranceId,
      }
    } else {
      payload = {
        parking_id: parkingId,
        entrance_id: entranceId,
        spot_id: spotId,
        entrance_vertex_id: entranceId,
        spot_vertex_id: spotId,
      }
    }

    const response = await apiClient.post('/routes', payload)
    return response.data
  },

  /**
   * Найти ближайшее свободное место от выбранного въезда.
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
