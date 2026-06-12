import { http } from './http'
import type { StationSearchResult } from '@/types/station'

export async function searchStations(query: string): Promise<StationSearchResult[]> {
  const response = await http.get<StationSearchResult[]>('/stations/search', {
    params: { q: query }
  })
  return response.data
}
