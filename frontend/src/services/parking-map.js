import { parkingService } from './parking'

export const parkingMapService = {
  async getLayout(parkingId) {
    return parkingService.getLayout(parkingId)
  },

  async getMap(parkingId) {
    return parkingService.getMap(parkingId)
  },

  async getOccupancy(parkingId) {
    return parkingService.getOccupancy(parkingId)
  },

  async getState(parkingId) {
    const [layout, map, occupancy] = await Promise.all([
      parkingService.getLayout(parkingId),
      parkingService.getMap(parkingId),
      parkingService.getOccupancy(parkingId),
    ])

    return {
      layout,
      map,
      occupancy,
    }
  },
}