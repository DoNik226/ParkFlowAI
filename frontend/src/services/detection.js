import apiClient from './api-client'

export const detectionService = {
  async getStatus(parkingId) {
    const response = await apiClient.get(`/parkings/${parkingId}/detector/status`)
    return response.data
  },

  async start(parkingId) {
    const response = await apiClient.post(`/parkings/${parkingId}/detector/start`)
    return response.data
  },

  async stop(parkingId) {
    const response = await apiClient.post(`/parkings/${parkingId}/detector/stop`)
    return response.data
  },
}