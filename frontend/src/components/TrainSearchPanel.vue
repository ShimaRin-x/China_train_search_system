<script setup lang="ts">
import { Close, Expand, Fold, Location, Search } from '@element-plus/icons-vue'
import { storeToRefs } from 'pinia'
import { computed, ref } from 'vue'

import { useTrainStore } from '@/stores/train'
import type { StationSearchResult } from '@/types/station'
import type { TrainSearchResult } from '@/types/train'

const trainStore = useTrainStore()
const {
  detail,
  loading,
  results,
  selectedStation,
  selectedTrainId,
  stationLoading,
  stationResults,
  stops
} = storeToRefs(trainStore)

const collapsed = ref(false)
const trainPrefix = ref('G')
const trainNumber = ref('')
const stationKeyword = ref('')
const trainPrefixes = [
  { label: 'G', value: 'G' },
  { label: 'D', value: 'D' },
  { label: 'C', value: 'C' },
  { label: 'Z', value: 'Z' },
  { label: 'T', value: 'T' },
  { label: 'K', value: 'K' },
  { label: 'S', value: 'S' },
  { label: 'Y', value: 'Y' },
  { label: '普速', value: '0' }
]

const title = computed(() => detail.value?.train_code || detail.value?.train_no || '未选择车次')
const subtitle = computed(() => {
  if (!detail.value) return '搜索车次后查看经停站与高亮经路'
  const origin = detail.value.origin_station_name ?? '始发站'
  const destination = detail.value.destination_station_name ?? '终到站'
  return `${origin} → ${destination}`
})

const trainKeyword = computed(() => {
  const number = trainNumber.value.trim()
  return trainPrefix.value === '0' ? number || '0' : `${trainPrefix.value}${number}`
})
const trainNumberPlaceholder = computed(() => (trainPrefix.value === '0' ? '输入纯数字车次，如 1461' : '输入编号，可留空'))

function runSearch() {
  trainStore.search(trainKeyword.value)
}

function normalizeTrainNumber(value: string | number) {
  trainNumber.value = String(value).replace(/\D/g, '')
}

function runStationSearch() {
  trainStore.searchStation(stationKeyword.value)
}

function selectTrain(train: TrainSearchResult) {
  trainStore.selectTrain(train)
}

function selectStation(station: StationSearchResult) {
  trainStore.selectStation(station)
}

function clearTrainSelection() {
  trainStore.clearSelection()
}

function clearTrainSearch() {
  trainNumber.value = ''
  trainStore.results = []
  trainStore.clearSelection()
}

function clearStationSelection() {
  trainStore.clearStationSelection()
}

function formatStopTime(value?: string | null) {
  return value ? value.slice(0, 5) : '--'
}
</script>

<template>
  <aside class="search-panel" :class="{ collapsed }">
    <button class="panel-toggle" type="button" :aria-label="collapsed ? '展开搜索面板' : '收起搜索面板'" @click="collapsed = !collapsed">
      <el-icon>
        <Expand v-if="collapsed" />
        <Fold v-else />
      </el-icon>
    </button>

    <template v-if="!collapsed">
      <header class="panel-header">
        <span class="eyebrow">V1</span>
        <h1>中国铁路车次经路可视化平台</h1>
      </header>

    <section class="search-box">
      <div class="section-title">车次搜索</div>
      <div class="train-search-row">
        <el-select v-model="trainPrefix" class="prefix-select" aria-label="车次首字母">
          <el-option v-for="prefix in trainPrefixes" :key="prefix.value" :label="prefix.label" :value="prefix.value" />
        </el-select>
        <el-input
          v-model="trainNumber"
          clearable
          :placeholder="trainNumberPlaceholder"
          @input="normalizeTrainNumber"
          @keyup.enter="runSearch"
        />
        <el-button :icon="Search" :loading="loading" aria-label="搜索车次" @click="runSearch" />
        <el-button :icon="Close" aria-label="清除车次搜索和高亮" @click="clearTrainSearch" />
      </div>
    </section>

    <section class="result-list">
      <div class="section-title">车次结果</div>
      <el-empty v-if="!results.length && !loading" :image-size="72" description="暂无结果" />
      <el-skeleton v-if="loading && !results.length" :rows="4" animated />
      <button
        v-for="train in results"
        :key="train.id"
        class="train-result"
        :class="{ active: selectedTrainId === train.id }"
        type="button"
        @click="selectTrain(train)"
      >
        <span class="train-code">{{ train.train_code || train.train_no }}</span>
        <span class="train-route">
          {{ train.origin_station_name || '始发站' }} → {{ train.destination_station_name || '终到站' }}
        </span>
      </button>
    </section>

    <section class="search-box">
      <div class="section-title">车站搜索</div>
      <div class="station-search-row">
        <el-input
          v-model="stationKeyword"
          clearable
          placeholder="输入车站，如 北京南"
          @clear="clearStationSelection"
          @keyup.enter="runStationSearch"
        >
          <template #append>
            <el-button :icon="Search" :loading="stationLoading" aria-label="搜索车站" @click="runStationSearch" />
          </template>
        </el-input>
        <el-button :icon="Close" aria-label="清除车站定位" @click="clearStationSelection" />
      </div>
      <el-skeleton v-if="stationLoading && !stationResults.length" :rows="2" animated />
      <div v-if="stationResults.length" class="station-results">
        <button
          v-for="station in stationResults"
          :key="station.id"
          class="station-result"
          :class="{ active: selectedStation?.id === station.id }"
          type="button"
          @click="selectStation(station)"
        >
          <span class="station-name">
            <el-icon><Location /></el-icon>
            {{ station.name_zh }}
          </span>
          <span class="station-meta">
            {{ station.city_name || station.province_name || station.telecode || '车站' }}
            <template v-if="station.longitude === null || station.longitude === undefined"> · 暂无坐标</template>
          </span>
        </button>
      </div>
    </section>

    <section class="train-summary">
      <div class="section-title">经停站</div>
      <div class="summary-title">{{ title }}</div>
      <div class="summary-subtitle">{{ subtitle }}</div>
      <el-timeline v-if="stops.length" class="stop-timeline">
        <el-timeline-item
          v-for="stop in stops"
          :key="stop.id"
          :timestamp="`${formatStopTime(stop.arrive_time)} / ${formatStopTime(stop.depart_time)}`"
          placement="top"
        >
          <div class="stop-row">
            <span class="stop-index">{{ stop.stop_order }}</span>
            <span class="stop-name">{{ stop.station_name }}</span>
            <span class="stop-mileage">{{ stop.mileage_km ?? '--' }} km</span>
          </div>
        </el-timeline-item>
      </el-timeline>
    </section>
      <button v-if="selectedTrainId" class="clear-link" type="button" @click="clearTrainSelection">
        清除当前高亮线路
      </button>
    </template>
  </aside>
</template>

<style scoped>
.search-panel {
  position: relative;
  display: flex;
  width: 380px;
  min-width: 320px;
  height: 100vh;
  flex-direction: column;
  gap: 18px;
  border-right: 1px solid #d8e0e3;
  background: #fbfcfc;
  padding: 22px;
  overflow: auto;
  transition: width 0.18s ease, min-width 0.18s ease, padding 0.18s ease;
  z-index: 2;
}

.search-panel.collapsed {
  width: 48px;
  min-width: 48px;
  padding: 0;
  overflow: visible;
}

.panel-toggle {
  position: sticky;
  top: 8px;
  z-index: 3;
  display: inline-grid;
  width: 30px;
  height: 30px;
  place-items: center;
  align-self: flex-end;
  border: 1px solid #cbd8dc;
  border-radius: 6px;
  background: #ffffff;
  color: #315560;
  cursor: pointer;
}

.search-panel.collapsed .panel-toggle {
  position: absolute;
  top: 14px;
  right: 9px;
}

.panel-header {
  display: grid;
  gap: 8px;
}

.eyebrow {
  width: fit-content;
  border: 1px solid #bed4dc;
  border-radius: 4px;
  color: #23606e;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0;
  padding: 2px 6px;
}

h1 {
  margin: 0;
  color: #15252b;
  font-size: 22px;
  line-height: 1.25;
}

.search-box {
  display: grid;
  gap: 10px;
}

.train-search-row,
.station-search-row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr) 42px 42px;
  gap: 8px;
  align-items: center;
}

.station-search-row {
  grid-template-columns: minmax(0, 1fr) 42px;
}

.prefix-select {
  width: 72px;
}

.result-list,
.train-summary {
  display: grid;
  gap: 10px;
}

.station-results {
  display: grid;
  gap: 8px;
}

.clear-link {
  width: fit-content;
  border: 0;
  background: transparent;
  color: #b93516;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
  padding: 0;
}

.clear-link:hover {
  color: #81230f;
  text-decoration: underline;
}

.section-title {
  color: #617178;
  font-size: 13px;
  font-weight: 700;
}

.train-result {
  display: grid;
  width: 100%;
  gap: 4px;
  border: 1px solid #d7e0e3;
  border-radius: 6px;
  background: #ffffff;
  color: #17202a;
  cursor: pointer;
  padding: 10px 12px;
  text-align: left;
}

.station-result {
  display: grid;
  width: 100%;
  gap: 3px;
  border: 1px solid #d7e0e3;
  border-radius: 6px;
  background: #ffffff;
  color: #17202a;
  cursor: pointer;
  padding: 8px 10px;
  text-align: left;
}

.train-result:hover,
.train-result.active,
.station-result:hover,
.station-result.active {
  border-color: #178a9e;
  background: #eef9fb;
}

.train-code {
  color: #0f5260;
  font-size: 18px;
  font-weight: 800;
}

.train-route,
.summary-subtitle,
.station-meta {
  color: #596970;
  font-size: 13px;
}

.station-name {
  display: inline-flex;
  gap: 5px;
  align-items: center;
  color: #0f5260;
  font-weight: 800;
}

.summary-title {
  color: #142429;
  font-size: 26px;
  font-weight: 800;
}

.stop-timeline {
  padding: 8px 0 0 2px;
}

.stop-row {
  display: grid;
  grid-template-columns: 26px 1fr auto;
  gap: 8px;
  align-items: center;
}

.stop-index {
  display: inline-grid;
  width: 22px;
  height: 22px;
  place-items: center;
  border-radius: 50%;
  background: #dceff3;
  color: #0f5260;
  font-size: 12px;
  font-weight: 800;
}

.stop-name {
  overflow: hidden;
  color: #17202a;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stop-mileage {
  color: #66777e;
  font-size: 12px;
}

@media (max-width: 860px) {
  .search-panel {
    width: 100%;
    height: 44vh;
    border-right: 0;
    border-bottom: 1px solid #d8e0e3;
  }

  .search-panel.collapsed {
    width: 100%;
    min-width: 100%;
    height: 44px;
  }
}
</style>
