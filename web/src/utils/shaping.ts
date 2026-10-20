import type { ShapePhoto } from '@/api/types'

export function photoUrl(photo: ShapePhoto): string {
  return `/api/shaping/photo/${photo.id}/image?v=${encodeURIComponent(photo.updated_at)}`
}

export function signedDifference(current: number | null, previous: number | null, unit: string): string {
  if (current == null || previous == null) return '暂无可比记录'
  const difference = Math.round((current - previous) * 10) / 10
  return `${difference > 0 ? '+' : ''}${difference.toFixed(1)} ${unit}`
}

export async function prepareShapePhoto(file: File): Promise<string> {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) throw new Error('请选择 JPG、PNG 或 WebP 图片。')
  if (file.size > 12 * 1024 * 1024) throw new Error('原图请控制在 12 MB 以内。')
  const objectUrl = URL.createObjectURL(file)
  try {
    const image = new Image()
    image.src = objectUrl
    await image.decode()
    if (image.naturalWidth * image.naturalHeight > 24_000_000) throw new Error('图片尺寸过大，请选择 2400 万像素以内的照片。')
    const factor = Math.min(1, 1280 / Math.max(image.naturalWidth, image.naturalHeight))
    const canvas = document.createElement('canvas')
    canvas.width = Math.max(1, Math.round(image.naturalWidth * factor))
    canvas.height = Math.max(1, Math.round(image.naturalHeight * factor))
    const context = canvas.getContext('2d')
    if (!context) throw new Error('当前浏览器无法处理图片，请更换浏览器。')
    context.drawImage(image, 0, 0, canvas.width, canvas.height)
    return canvas.toDataURL('image/jpeg', 0.88)
  } finally { URL.revokeObjectURL(objectUrl) }
}
