import { API_BASE_URL } from './apiClient'
import type { VisionDepthObservation } from '../types'

async function readObservation(response: Response, path: string): Promise<VisionDepthObservation> {
  if (!response.ok) {
    throw new Error(`VisionDepth API ${response.status} ${path}`)
  }
  return response.json() as Promise<VisionDepthObservation>
}

export async function analyzeVisionDepthUpload(file: File): Promise<VisionDepthObservation> {
  const body = new FormData()
  body.append('file', file)
  const path = '/api/v1/vision-depth/analyze/upload'
  return readObservation(await fetch(`${API_BASE_URL}${path}`, { method: 'POST', body }), path)
}

export async function analyzeVisionDepthUrl(url: string): Promise<VisionDepthObservation> {
  const path = '/api/v1/vision-depth/analyze/url'
  return readObservation(await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  }), path)
}
