import api from './api-client'

export const getUsers = () => api.get('/admin/users')
export const getParkings = () => api.get('/admin/parkings')