import apiClient from './api-client'

export const parkingService = {
  async getAllParkings() {
    const response = await apiClient.get('/parkings')
    return response.data
  },

  async getParking(parkingId) {
    const response = await apiClient.get(`/parkings/${parkingId}`)
    return response.data
  },

  async createParking(data) {
    const response = await apiClient.post('/parkings', data)
    return response.data
  },

  async updateParking(parkingId, data) {
    const response = await apiClient.put(`/parkings/${parkingId}`, data)
    return response.data
  },

  async deleteParking(parkingId) {
    const response = await apiClient.delete(`/parkings/${parkingId}`)
    return response.data
  },

  async getLayout(parkingId) {
    const response = await apiClient.get(`/parkings/${parkingId}/layout`)
    return response.data
  },

  async saveLayout(parkingId, layout) {
    const response = await apiClient.put(`/parkings/${parkingId}/layout`, {
      layout,
    })
    return response.data
  },

  async getMap(parkingId) {
    const response = await apiClient.get(`/parkings/${parkingId}/map`)
    return response.data
  },

  async saveMap(parkingId, map) {
    const response = await apiClient.put(`/parkings/${parkingId}/map`, {
      map,
    })
    return response.data
  },

  async getOccupancy(parkingId) {
    const response = await apiClient.get(`/parkings/${parkingId}/occupancy`)
    return response.data
  },

  async getSpots(parkingId) {
    const response = await apiClient.get(`/parkings/${parkingId}/spots`)
    return response.data
  },

  async getFreeSpots(parkingId) {
    const response = await apiClient.get(`/parkings/${parkingId}/free-spots`)
    return response.data
  },

  async getEntrances(parkingId) {
    const response = await apiClient.get(`/parkings/${parkingId}/entrances`)
    return response.data
  },

  async uploadSourceVideo(parkingId, file) {
    const formData = new FormData()
    formData.append('file', file, file.name)

    const response = await apiClient.post(
      `/parkings/${parkingId}/source-video`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )

    return response.data
  },

async deleteSourceVideo(parkingId) {
  const response = await apiClient.delete(`/parkings/${parkingId}/source-video`)
  return response.data
},


  async uploadSnapshot(parkingId, file) {
    const formData = new FormData()
    formData.append('file', file, file.name)

    const response = await apiClient.post(
      `/parkings/${parkingId}/snapshot/upload`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      }
    )

    return response.data
  },

  async captureSnapshot(parkingId) {
    const response = await apiClient.post(`/parkings/${parkingId}/snapshot/capture`)
    return response.data
  },

  async getSnapshotBlob(parkingId) {
    const response = await apiClient.get(`/parkings/${parkingId}/snapshot`, {
      responseType: 'blob',
    })

    return response.data
  },

  async getDebugFrameBlob(parkingId) {
    const response = await apiClient.get(`/parkings/${parkingId}/debug-frame`, {
      responseType: 'blob',
    })

    return response.data
  },
}