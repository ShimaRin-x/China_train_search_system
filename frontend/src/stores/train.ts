import axios from 'axios'
import { ElMessage } from 'element-plus'
import { defineStore } from 'pinia'

import { searchStations } from '@/api/stations'
import { fetchTrainDetail, fetchTrainStops, searchTrains } from '@/api/trains'
import type { GeoJsonFeatureCollection } from '@/types/geojson'
import type { StationSearchResult } from '@/types/station'
import type { TrainDetail, TrainSearchResult, TrainStop } from '@/types/train'

interface TrainState {
  query: string
  loading: boolean
  stationLoading: boolean
  selectedTrainId: string | null
  results: TrainSearchResult[]
  detail: TrainDetail | null
  stops: TrainStop[]
  route: GeoJsonFeatureCollection | null
  stationQuery: string
  stationResults: StationSearchResult[]
  selectedStation: StationSearchResult | null
}

let trainSelectionVersion = 0

function emptyRoute(): GeoJsonFeatureCollection {
  return {
    type: 'FeatureCollection',
    features: []
  }
}

function apiErrorMessage(error: unknown, fallback: string) {
  if (axios.isAxiosError(error) && !error.response) {
    return '后端服务未启动或端口不可访问'
  }
  return fallback
}

export const useTrainStore = defineStore('train', {
  state: (): TrainState => ({
    query: '',
    loading: false,
    stationLoading: false,
    selectedTrainId: null,
    results: [],
    detail: null,
    stops: [],
    route: null,
    stationQuery: '',
    stationResults: [],
    selectedStation: null
  }),
  actions: {
    async search(query: string) {
      this.query = query
      const normalized = query.trim()
      if (!normalized) {
        this.results = []
        return
      }

      this.loading = true
      try {
        this.results = await searchTrains(normalized, normalized.length === 1 ? 50 : 20)
      } catch (error) {
        ElMessage.error(apiErrorMessage(error, '车次搜索失败'))
      } finally {
        this.loading = false
      }
    },
    async searchStation(query: string) {
      this.stationQuery = query
      const normalized = query.trim()
      if (!normalized) {
        this.stationResults = []
        return
      }

      this.stationLoading = true
      try {
        this.stationResults = await searchStations(normalized)
      } catch (error) {
        ElMessage.error(apiErrorMessage(error, '车站搜索失败'))
      } finally {
        this.stationLoading = false
      }
    },
    async selectTrain(train: TrainSearchResult) {
      const selectionVersion = ++trainSelectionVersion
      this.selectedTrainId = train.id
      this.loading = true
      this.detail = null
      this.stops = []
      this.route = emptyRoute()
      try {
        const [detail, stops] = await Promise.all([
          fetchTrainDetail(train.id),
          fetchTrainStops(train.id)
        ])
        if (selectionVersion !== trainSelectionVersion || this.selectedTrainId !== train.id) {
          return
        }
        this.detail = detail
        this.stops = stops
      } catch (error) {
        if (selectionVersion === trainSelectionVersion) {
          ElMessage.error(apiErrorMessage(error, '车次信息加载失败'))
        }
        return
      } finally {
        if (selectionVersion === trainSelectionVersion) {
          this.loading = false
        }
      }

      if (selectionVersion === trainSelectionVersion && this.selectedTrainId === train.id) {
        this.route = emptyRoute()
      }
    },
    selectStation(station: StationSearchResult) {
      this.selectedStation = station
      if (station.longitude === null || station.longitude === undefined || station.latitude === null || station.latitude === undefined) {
        ElMessage.warning('当前车站暂无坐标，无法定位到地图')
      }
    },
    clearSelection() {
      trainSelectionVersion += 1
      this.selectedTrainId = null
      this.loading = false
      this.detail = null
      this.stops = []
      this.route = emptyRoute()
    },
    clearStationSelection() {
      this.selectedStation = null
    }
  }
})
