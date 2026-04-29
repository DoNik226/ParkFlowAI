import apiClient from './api-client'

export const parkingMapService = {
  async getLayout(parkingId) {
    const response = await apiClient.get(`/api/parking-map/${parkingId}/layout`)
    return response.data
  },

  async getOccupancy(parkingId) {
    const response = await apiClient.get(`/api/parking-map/${parkingId}/occupancy`)
    return response.data
  },

  async getState(parkingId) {
    const response = await apiClient.get(`/api/parking-map/${parkingId}/state`)
    return response.data
  },
}