import apiClient from './api-client'

/**
 * Сервис графического редактора разметки парковочных мест
 */
export const editorService = {
  /**
   * Получить зоны парковки
   * GET /editor/parking/{id}/zones
   */
  async getZones(parkingId) {
    const response = await apiClient.get(`/editor/parking/${parkingId}/zones`)
    return response.data
  },

  /**
   * Создать новую зону
   * POST /editor/parking/{id}/zones
   */
  async createZone(parkingId, zoneData) {
    const response = await apiClient.post(`/editor/parking/${parkingId}/zones`, zoneData)
    return response.data
  },

  /**
   * Обновить позицию места
   * PUT /editor/spots/{id}
   */
  async updateSpotPosition(id, vertices) {
    const response = await apiClient.put(`/editor/spots/${id}`, { vertices })
    return response.data
  },

  /**
   * Удалить место
   * DELETE /editor/spots/{id}
   */
  async deleteSpot(id) {
    const response = await apiClient.delete(`/editor/spots/${id}`)
    return response.data
  },

  /**
   * Отключить/включить место
   * PUT /editor/spots/{id}/toggle
   */
  async toggleSpot(id, enabled) {
    const response = await apiClient.put(`/editor/spots/${id}/toggle`, { enabled })
    return response.data
  },

  /**
   * Калибровка масштаба
   * POST /editor/parking/{id}/calibrate
   */
  async calibrateScale(parkingId, pixelDistance, realDistance) {
    const response = await apiClient.post(`/editor/parking/${parkingId}/calibrate`, {
      pixel_distance: pixelDistance,
      real_distance: realDistance
    })
    return response.data
  },

  /**
   * Экспорт конфигурации в JSON
   * POST /editor/parking/{id}/export/json
   */
  async exportConfigJson(parkingId) {
    const response = await apiClient.post(`/editor/parking/${parkingId}/export/json`)
    return response.data
  },

  /**
   * Экспорт изображения с разметкой (PNG)
   * GET /editor/parking/{id}/export/png?overlay=true
   */
  async exportConfigPng(parkingId, overlay = true) {
    const response = await apiClient.get(`/editor/parking/${parkingId}/export/png`, {
      params: { overlay },
      responseType: 'blob'
    })
    return response.data
  },

  /**
   * Сохранить конфигурацию
   * POST /editor/parking/{id}/save
   */
  async saveConfig(parkingId, configFile) {
    const response = await apiClient.post(`/editor/parking/${parkingId}/save`, {
      config_file: configFile
    })
    return response.data
  }
}