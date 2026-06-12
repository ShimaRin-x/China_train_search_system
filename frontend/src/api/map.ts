import { http } from './http'
import type { GeoJsonFeatureCollection, PointGeometry } from '@/types/geojson'

export async function fetchRailways(bbox?: string): Promise<GeoJsonFeatureCollection> {
  const response = await http.get<GeoJsonFeatureCollection>('/map/railways', {
    params: { bbox }
  })
  return response.data
}

export async function fetchStations(bbox?: string): Promise<GeoJsonFeatureCollection> {
  const response = await http.get<GeoJsonFeatureCollection>('/map/stations', {
    params: { bbox }
  })
  return response.data
}

export interface Wtrans2StationProperties extends Record<string, unknown> {
  order: number
  input_name: string
  matched_name?: string | null
  kid?: string | null
  minzoom?: number | null
  location?: string | null
}

export async function fetchWtrans2Stations(names: string[]): Promise<GeoJsonFeatureCollection<PointGeometry, Wtrans2StationProperties>> {
  const response = await http.post<GeoJsonFeatureCollection<PointGeometry, Wtrans2StationProperties>>('/map/wtrans2/stations', {
    names
  })
  return response.data
}
