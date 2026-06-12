import { http } from './http'
import type { GeoJsonFeatureCollection } from '@/types/geojson'
import type { TrainDetail, TrainSearchResult, TrainStop } from '@/types/train'

export async function searchTrains(query: string, limit = 20): Promise<TrainSearchResult[]> {
  const response = await http.get<TrainSearchResult[]>('/trains/search', {
    params: { q: query, limit }
  })
  return response.data
}

export async function fetchTrainDetail(trainId: string): Promise<TrainDetail> {
  const response = await http.get<TrainDetail>(`/trains/${trainId}`)
  return response.data
}

export async function fetchTrainStops(trainId: string): Promise<TrainStop[]> {
  const response = await http.get<TrainStop[]>(`/trains/${trainId}/stops`)
  return response.data
}

export async function fetchTrainRoute(trainId: string): Promise<GeoJsonFeatureCollection> {
  const response = await http.get<GeoJsonFeatureCollection>(`/trains/${trainId}/route`)
  return response.data
}
