export interface TrainSearchResult {
  id: string
  train_no: string
  train_code?: string | null
  train_type?: string | null
  service_date?: string | null
  origin_station_name?: string | null
  destination_station_name?: string | null
}

export interface TrainStop {
  id: string
  station_id: string
  station_name: string
  telecode?: string | null
  stop_order: number
  arrive_time?: string | null
  depart_time?: string | null
  day_offset: number
  dwell_minutes?: number | null
  mileage_km?: number | null
  longitude?: number | null
  latitude?: number | null
}

export interface TrainDetail extends TrainSearchResult {
  data_source: string
}
