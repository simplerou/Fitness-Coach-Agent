import type { ShapeCircumference, ShapeMetric, ShapePhotoView, ShapeSource } from '@/api/types'

export const CIRCUMFERENCES: ShapeCircumference[] = ['waist_cm', 'hip_cm', 'chest_cm', 'arm_cm', 'thigh_cm']
export const SHAPE_METRICS: ShapeMetric[] = [...CIRCUMFERENCES, 'body_fat_percent', 'skeletal_muscle_kg']
export const SHAPE_LABELS: Record<ShapeMetric, string> = {
  waist_cm: '腰围', hip_cm: '臀围', chest_cm: '胸围', arm_cm: '臂围', thigh_cm: '腿围',
  body_fat_percent: '体脂率', skeletal_muscle_kg: '骨骼肌',
}
export const SHAPE_UNITS: Record<ShapeMetric, string> = {
  waist_cm: 'cm', hip_cm: 'cm', chest_cm: 'cm', arm_cm: 'cm', thigh_cm: 'cm',
  body_fat_percent: '%', skeletal_muscle_kg: 'kg',
}
export const SHAPE_RANGES: Record<ShapeMetric, [number, number]> = {
  waist_cm: [30, 250], hip_cm: [40, 250], chest_cm: [40, 250], arm_cm: [10, 100], thigh_cm: [20, 150],
  body_fat_percent: [3, 65], skeletal_muscle_kg: [5, 100],
}
export const PHOTO_VIEWS: ShapePhotoView[] = ['front', 'side', 'back']
export const PHOTO_LABELS: Record<ShapePhotoView, string> = { front: '正面', side: '侧面', back: '背面' }
export const SOURCE_LABELS: Record<ShapeSource, string> = {
  scale_reading: '体脂秤读数（手动录入）', professional_measurement: '专业检测报告', manual: '其他实测记录',
}
