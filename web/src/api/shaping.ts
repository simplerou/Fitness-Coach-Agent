import { request } from './client'
import type { ShapeDashboard, ShapeMeasurementPayload, ShapeMutationResult, ShapePhotoView, ShapeTargetMetric } from './types'

export const getShaping = () => request<ShapeDashboard>('/api/shaping')
export const saveShapeMeasurement = (payload: ShapeMeasurementPayload) => request<ShapeMutationResult>(
  '/api/shaping/measurement', { method: 'PUT', body: JSON.stringify(payload) })
export const deleteShapeMeasurement = (date: string) => request<ShapeMutationResult>(
  `/api/shaping/measurement/${date}`, { method: 'DELETE' })
export const saveShapeTarget = (metric: ShapeTargetMetric, target_value: number) => request<ShapeMutationResult>(
  '/api/shaping/target', { method: 'PUT', body: JSON.stringify({ metric, target_value }) })
export const deleteShapeTarget = (metric: ShapeTargetMetric) => request<ShapeMutationResult>(
  `/api/shaping/target/${metric}`, { method: 'DELETE' })
export const saveShapePhoto = (recorded_on: string, view: ShapePhotoView, image_data: string) => request<ShapeMutationResult>(
  '/api/shaping/photo', { method: 'PUT', body: JSON.stringify({ recorded_on, view, image_data }) })
export const deleteShapePhoto = (id: number) => request<ShapeMutationResult>(`/api/shaping/photo/${id}`, { method: 'DELETE' })
