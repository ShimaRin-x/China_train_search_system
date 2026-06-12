export interface StationSearchResult {
  id: string
  name_zh: string
  name_en?: string | null
  telecode?: string | null
  pinyin?: string | null
  city_name?: string | null
  province_name?: string | null
  display_rank?: number | null
  longitude?: number | null
  latitude?: number | null
}
