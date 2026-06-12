<script setup lang="ts">
import maplibregl, {
  LngLatBounds,
  type ExpressionSpecification,
  type FilterSpecification,
  type GeoJSONSource,
  type LayerSpecification,
  type Map as MapLibreMap
} from 'maplibre-gl'
import { storeToRefs } from 'pinia'
import { onMounted, onUnmounted, ref, watch } from 'vue'

import { fetchRailways, fetchStations, fetchWtrans2Stations } from '@/api/map'
import { useTrainStore } from '@/stores/train'
import type { GeoJsonFeature, GeoJsonFeatureCollection, LineStringGeometry, PointGeometry, Position } from '@/types/geojson'

const mapContainer = ref<HTMLDivElement | null>(null)
const trainStore = useTrainStore()
const { detail, route, selectedStation, stops } = storeToRefs(trainStore)

let map: MapLibreMap | null = null
let wtrans2SyncVersion = 0
const railHighlightSnapshots = new Map<string, Partial<Record<'line-color' | 'line-opacity' | 'line-width', unknown>>>()
let railHighlightMode: 'none' | 'high-speed' = 'none'

const railwayMapStyle = 'http://railmap.geogv.org/styles/wtrans2-general-default-zhcn/style.json'
const usesWarpedRailwayBase = railwayMapStyle.includes('wtrans2')
const chinaBounds: [[number, number], [number, number]] = [
  [73, 17],
  [136.5, 54.5]
]
const chinaBbox = chinaBounds.flat().join(',')
const detailZoom = {
  boundary: 3,
  expressRoad: 5.8,
  majorStation: 5.8,
  secondaryStation: 7,
  localStation: 9.5,
  localDetail: 11.2
}

const emptyCollection: GeoJsonFeatureCollection = {
  type: 'FeatureCollection',
  features: []
}

type PointFeature = GeoJsonFeature<PointGeometry, Record<string, unknown>>
type PointFeatureCollection = GeoJsonFeatureCollection<PointGeometry, Record<string, unknown>>

const railwayColorExpression = [
  'match',
  [
    'downcase',
    [
      'to-string',
      [
        'coalesce',
        ['get', 'railway_type'],
        ['get', 'service_type'],
        ['get', 'category'],
        ['get', 'traffic_type'],
        'other'
      ]
    ]
  ],
  'high_speed',
  '#ff553f',
  'highspeed',
  '#ff553f',
  'hsr',
  '#ff553f',
  'rapid',
  '#ffa033',
  'express',
  '#ffa033',
  'intercity',
  '#ffa033',
  'passenger',
  '#35a852',
  'conventional',
  '#35a852',
  'freight',
  '#83b93e',
  'cargo',
  '#83b93e',
  '#7c87c9'
] as unknown as ExpressionSpecification

function stationRankAtMost(maxRank: number): FilterSpecification {
  return ['<=', ['coalesce', ['get', 'display_rank'], 4], maxRank] as unknown as FilterSpecification
}

function stationRankEquals(rank: number): FilterSpecification {
  return ['==', ['coalesce', ['get', 'display_rank'], 4], rank] as unknown as FilterSpecification
}

function stationRankAtLeast(minRank: number): FilterSpecification {
  return ['>=', ['coalesce', ['get', 'display_rank'], 4], minRank] as unknown as FilterSpecification
}

function setSourceData(sourceId: string, data: GeoJsonFeatureCollection) {
  const source = map?.getSource(sourceId) as GeoJSONSource | undefined
  source?.setData(data as Parameters<GeoJSONSource['setData']>[0])
}

function isLineStringGeometry(geometry: unknown): geometry is LineStringGeometry {
  return (
    typeof geometry === 'object' &&
    geometry !== null &&
    (geometry as LineStringGeometry).type === 'LineString' &&
    Array.isArray((geometry as LineStringGeometry).coordinates)
  )
}

function routeCoordinates(data: GeoJsonFeatureCollection | null): Position[] {
  if (!data) return []
  return data.features.flatMap((feature) => {
    return isLineStringGeometry(feature.geometry) ? feature.geometry.coordinates : []
  })
}

function pointCoordinates(data: GeoJsonFeatureCollection<PointGeometry> | null): Position[] {
  if (!data) return []
  return data.features.flatMap((feature) => feature.geometry.type === 'Point' ? [feature.geometry.coordinates] : [])
}

function fitCoordinates(coordinates: Position[]) {
  if (!map || !coordinates.length) return
  const bounds = coordinates.reduce((box, coord) => box.extend(coord), new LngLatBounds(coordinates[0], coordinates[0]))
  map.fitBounds(bounds, {
    padding: { top: 80, right: 80, bottom: 80, left: 420 },
    duration: 700,
    maxZoom: 9
  })
}

function stopCollection(): GeoJsonFeatureCollection<PointGeometry> {
  return {
    type: 'FeatureCollection',
    features: stops.value
      .filter((stop) => stop.longitude !== null && stop.longitude !== undefined && stop.latitude !== null && stop.latitude !== undefined)
      .map((stop) => ({
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [stop.longitude as number, stop.latitude as number]
        },
        properties: stop
      }))
  }
}

function selectedStationCollection(): GeoJsonFeatureCollection<PointGeometry> {
  const station = selectedStation.value
  if (station?.longitude === null || station?.longitude === undefined || station.latitude === null || station.latitude === undefined) {
    return emptyCollection as GeoJsonFeatureCollection<PointGeometry>
  }

  return {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        geometry: {
          type: 'Point',
          coordinates: [station.longitude, station.latitude]
        },
        properties: station
      }
    ]
  }
}

function flyToCoordinates(coordinates: Position) {
  if (!map) {
    return
  }

  map.flyTo({
    center: coordinates,
    zoom: Math.max(map.getZoom(), 9.5),
    duration: 700,
    padding: { top: 80, right: 80, bottom: 80, left: 420 }
  })
}

function flyToSelectedStation() {
  const station = selectedStation.value
  if (station?.longitude === null || station?.longitude === undefined || station.latitude === null || station.latitude === undefined) {
    return
  }

  flyToCoordinates([station.longitude, station.latitude])
}

function uniqueNames(names: Array<string | null | undefined>) {
  const seen = new Set<string>()
  return names
    .map((name) => name?.trim())
    .filter((name): name is string => Boolean(name))
    .filter((name) => {
      if (seen.has(name)) return false
      seen.add(name)
      return true
    })
}

async function fetchWarpedStationPoints(names: string[]): Promise<PointFeatureCollection> {
  const stationNames = uniqueNames(names)
  if (!stationNames.length) {
    return emptyCollection as PointFeatureCollection
  }

  return fetchWtrans2Stations(stationNames) as Promise<PointFeatureCollection>
}

function warpedStopCollection(warpedStations: PointFeatureCollection): PointFeatureCollection {
  const stopByName = new Map(stops.value.map((stop) => [stop.station_name, stop]))
  return {
    type: 'FeatureCollection',
    features: warpedStations.features.map((feature) => {
      const properties = feature.properties as Record<string, unknown>
      const inputName = String(properties.input_name ?? '')
      return {
        ...feature,
        properties: {
          ...properties,
          ...(stopByName.get(inputName) ?? {}),
          station_name: inputName
        }
      }
    })
  }
}

function selectedWarpedStationCollection(warpedStations: PointFeatureCollection): PointFeatureCollection {
  const station = selectedStation.value
  const feature = warpedStations.features[0]
  if (!station || !feature) {
    return emptyCollection as PointFeatureCollection
  }

  return {
    type: 'FeatureCollection',
    features: [
      {
        ...feature,
        properties: {
          ...(feature.properties as Record<string, unknown>),
          ...station
        }
      } as PointFeature
    ]
  }
}

function layerId(layer: LayerSpecification) {
  return layer.id.toLowerCase()
}

function includesAny(value: string, needles: string[]) {
  return needles.some((needle) => value.includes(needle))
}

function hideBaseLayer(layerIdValue: string) {
  if (!map?.getLayer(layerIdValue)) return
  map.setLayoutProperty(layerIdValue, 'visibility', 'none')
}

function setBaseLayerZoom(layerIdValue: string, minzoom: number, maxzoom = 24) {
  if (!map?.getLayer(layerIdValue)) return
  map.setLayerZoomRange(layerIdValue, minzoom, maxzoom)
}

function setBaseLayerPaint(layerIdValue: string, property: string, value: unknown) {
  if (!map?.getLayer(layerIdValue)) return
  map.setPaintProperty(layerIdValue, property, value)
}

function setBaseLayerLayout(layerIdValue: string, property: string, value: unknown) {
  if (!map?.getLayer(layerIdValue)) return
  map.setLayoutProperty(layerIdValue, property, value)
}

function isBoundaryLayer(id: string) {
  return id.startsWith('boundary_') || includesAny(id, ['boundary', 'admin'])
}

function isBaseRailwayLayer(id: string) {
  return (
    id.startsWith('rail_') ||
    includesAny(id, ['major_rail', 'transit_rail', 'railway'])
  )
}

function isHighSpeedRailwayLayer(id: string) {
  return id.startsWith('rail_hsr') || includesAny(id, ['high_speed', 'highspeed', 'hsr'])
}

function railwayLayerKind(id: string): 'high-speed' | 'rapid' | 'passenger' | 'freight' | 'other' {
  if (isHighSpeedRailwayLayer(id)) return 'high-speed'
  if (id.startsWith('rail_rr') || includesAny(id, ['rapid', 'intercity', 'city_rail'])) return 'rapid'
  if (id.startsWith('rail_f') || includesAny(id, ['freight', 'cargo'])) return 'freight'
  if (id.startsWith('rail_r') || includesAny(id, ['major_rail', 'passenger', 'conventional'])) return 'passenger'
  return 'other'
}

function railwayColor(kind: ReturnType<typeof railwayLayerKind>) {
  return {
    'high-speed': '#ff553f',
    rapid: '#ffa033',
    passenger: '#35a852',
    freight: '#83b93e',
    other: '#7c87c9'
  }[kind]
}

function railwayOpacity(kind: ReturnType<typeof railwayLayerKind>) {
  return {
    'high-speed': 0.86,
    rapid: 0.76,
    passenger: 0.72,
    freight: 0.64,
    other: 0.56
  }[kind]
}

function railwayWidth(kind: ReturnType<typeof railwayLayerKind>, highlighted = false): ExpressionSpecification {
  const boost = highlighted ? 0.55 : 0
  const base = kind === 'high-speed' ? 1.05 : kind === 'rapid' ? 0.95 : kind === 'freight' ? 0.75 : 0.85
  return [
    'interpolate',
    ['linear'],
    ['zoom'],
    3,
    base + boost,
    7,
    base + 0.45 + boost,
    10,
    base + 0.95 + boost,
    14,
    base + 1.65 + boost
  ] as unknown as ExpressionSpecification
}

function selectedTrainIsHighSpeed() {
  const train = detail.value
  const code = String(train?.train_code || train?.train_no || train?.train_type || '').trim().toUpperCase()
  return code.startsWith('G') || train?.train_type?.toUpperCase() === 'G'
}

function isRailwayLineLayer(layer: LayerSpecification, id: string) {
  return layer.type === 'line' && isBaseRailwayLayer(id) && !id.endsWith('_hatching')
}

function isRailwaySymbolLayer(layer: LayerSpecification, id: string) {
  return layer.type === 'symbol' && isBaseRailwayLayer(id)
}

function rememberRailPaint(layerIdValue: string) {
  if (!map || railHighlightSnapshots.has(layerIdValue)) return
  railHighlightSnapshots.set(layerIdValue, {
    'line-color': map.getPaintProperty(layerIdValue, 'line-color'),
    'line-opacity': map.getPaintProperty(layerIdValue, 'line-opacity'),
    'line-width': map.getPaintProperty(layerIdValue, 'line-width')
  })
}

function restoreRailHighlight() {
  if (!map || railHighlightMode === 'none') return

  railHighlightSnapshots.forEach((snapshot, layerIdValue) => {
    if (!map?.getLayer(layerIdValue)) return
    setBaseLayerPaint(layerIdValue, 'line-color', snapshot['line-color'] ?? null)
    setBaseLayerPaint(layerIdValue, 'line-opacity', snapshot['line-opacity'] ?? 1)
    setBaseLayerPaint(layerIdValue, 'line-width', snapshot['line-width'] ?? 1)
  })
  railHighlightSnapshots.clear()
  railHighlightMode = 'none'
}

function applyTrainRailHighlight() {
  if (!map || !usesWarpedRailwayBase) return

  if (!selectedTrainIsHighSpeed()) {
    restoreRailHighlight()
    return
  }

  railHighlightMode = 'high-speed'
  const layers = map.getStyle().layers ?? []
  layers.forEach((layer) => {
    const id = layerId(layer)
    if (!isRailwayLineLayer(layer, id)) return

    rememberRailPaint(layer.id)
    const kind = railwayLayerKind(id)
    const isFocused = kind === 'high-speed'
    setBaseLayerPaint(layer.id, 'line-color', railwayColor(kind))
    setBaseLayerPaint(layer.id, 'line-opacity', isFocused ? 0.96 : 0.12)
    setBaseLayerPaint(layer.id, 'line-width', railwayWidth(kind, isFocused))
  })
}

function isExpressRoadLayer(id: string) {
  return includesAny(id, ['motorway_casing', 'motorway', 'trunk_primary_casing', 'trunk_primary'])
}

function isRoadLabelLayer(id: string) {
  return includesAny(id, ['highway-name', 'highway-shield', 'road_shield', 'one_way_arrow'])
}

function isLocalRoadLayer(id: string) {
  return (
    id.startsWith('road_') ||
    id.startsWith('bridge_') ||
    id.startsWith('tunnel_')
  )
}

function isPlaceLabelLayer(id: string) {
  return id.startsWith('label_') || includesAny(id, ['place', 'settlement'])
}

function isRailwayStationLayer(id: string) {
  return id.startsWith('station-')
}

function stylePlainBaseLayer(layer: LayerSpecification, id: string, type: LayerSpecification['type']) {
  if (type === 'background') {
    setBaseLayerPaint(layer.id, 'background-color', '#f8f6f2')
    return true
  }

  if (id === 'natural_earth' || includesAny(id, ['hillshade', 'terrain', 'relief'])) {
    hideBaseLayer(layer.id)
    return true
  }

  if (id === 'water') {
    setBaseLayerPaint(layer.id, 'fill-color', '#b9d9f0')
    setBaseLayerPaint(layer.id, 'fill-opacity', 0.86)
    return true
  }

  return false
}

function styleBaseRailwayLayer(layer: LayerSpecification, id: string) {
  if (id.endsWith('_hatching')) {
    hideBaseLayer(layer.id)
    return
  }

  setBaseLayerZoom(layer.id, detailZoom.boundary)
  if (layer.type !== 'line') return

  const kind = railwayLayerKind(id)
  setBaseLayerPaint(layer.id, 'line-color', railwayColor(kind))
  setBaseLayerPaint(layer.id, 'line-opacity', railwayOpacity(kind))
  setBaseLayerPaint(layer.id, 'line-width', railwayWidth(kind))
}

function styleRoadLayer(layer: LayerSpecification, id: string, minzoom: number) {
  setBaseLayerZoom(layer.id, minzoom)

  if (layer.type !== 'line') return

  const isCasing = id.includes('casing')
  setBaseLayerPaint(layer.id, 'line-color', isCasing ? '#ead6b6' : '#fff0c9')
  setBaseLayerPaint(layer.id, 'line-opacity', isCasing ? 0.28 : 0.42)
  setBaseLayerPaint(
    layer.id,
    'line-width',
    isCasing
      ? ['interpolate', ['linear'], ['zoom'], minzoom, 0.45, 10, 1.2, 14, 3.4, 20, 9]
      : ['interpolate', ['linear'], ['zoom'], minzoom, 0.25, 10, 0.8, 14, 2.4, 20, 7]
  )
}

function styleTransitStationPoiLayer(layer: LayerSpecification) {
  if (!map?.getLayer(layer.id)) return

  map.setFilter(layer.id, ['==', ['get', 'class'], 'rail'] as unknown as FilterSpecification)
  setBaseLayerZoom(layer.id, detailZoom.secondaryStation + 0.3)
  setBaseLayerLayout(layer.id, 'icon-image', 'rail')
  setBaseLayerLayout(layer.id, 'icon-size', ['interpolate', ['linear'], ['zoom'], 7.3, 0.55, 10, 0.72, 13, 0.9])
  setBaseLayerLayout(layer.id, 'text-field', ['coalesce', ['get', 'name:nonlatin'], ['get', 'name'], ['get', 'name_en']])
  setBaseLayerLayout(layer.id, 'text-font', ['Noto Sans Bold', 'Noto Sans Regular'])
  setBaseLayerLayout(layer.id, 'text-size', ['interpolate', ['linear'], ['zoom'], 7.3, 11, 10, 12.5, 13, 14])
  setBaseLayerLayout(layer.id, 'text-offset', [0.75, 0])
  setBaseLayerLayout(layer.id, 'text-anchor', 'left')
  setBaseLayerPaint(layer.id, 'icon-opacity', 0.72)
  setBaseLayerPaint(layer.id, 'text-color', '#1689ff')
  setBaseLayerPaint(layer.id, 'text-halo-color', '#ffffff')
  setBaseLayerPaint(layer.id, 'text-halo-width', 1.6)
}

function styleRailwayStationLayer(layer: LayerSpecification, id: string) {
  setBaseLayerZoom(layer.id, id.includes('01') ? 4.2 : 5.4)
  setBaseLayerLayout(layer.id, 'visibility', 'visible')
  setBaseLayerPaint(layer.id, 'text-halo-color', 'hsla(0, 0%, 100%, 0.86)')
  setBaseLayerPaint(layer.id, 'text-halo-width', 2)
}

function configureBaseMapDetailLevels() {
  if (!map) return

  const layers = map.getStyle().layers ?? []
  layers.forEach((layer) => {
    const id = layerId(layer)
    const type = layer.type

    if (stylePlainBaseLayer(layer, id, type)) {
      return
    }

    if (isBoundaryLayer(id)) {
      setBaseLayerZoom(layer.id, detailZoom.boundary)
      return
    }

    if (isRoadLabelLayer(id)) {
      hideBaseLayer(layer.id)
      return
    }

    if (id === 'poi_transit') {
      styleTransitStationPoiLayer(layer)
      return
    }

    if (isRailwayStationLayer(id)) {
      styleRailwayStationLayer(layer, id)
      return
    }

    if (isRailwaySymbolLayer(layer, id)) {
      hideBaseLayer(layer.id)
      return
    }

    if (isRailwayLineLayer(layer, id)) {
      styleBaseRailwayLayer(layer, id)
      return
    }

    if (isExpressRoadLayer(id)) {
      styleRoadLayer(layer, id, detailZoom.expressRoad)
      return
    }

    if (isLocalRoadLayer(id)) {
      styleRoadLayer(layer, id, detailZoom.localDetail)
      return
    }

    if (isPlaceLabelLayer(id) || includesAny(id, ['water_name', 'waterway_line_label'])) {
      setBaseLayerZoom(layer.id, detailZoom.localDetail)
      return
    }

    if (id.startsWith('waterway_')) {
      setBaseLayerZoom(layer.id, detailZoom.localDetail)
      return
    }

    if (includesAny(id, ['landcover', 'landuse', 'park', 'aeroway', 'airport', 'building', 'poi'])) {
      hideBaseLayer(layer.id)
      return
    }

    if (type === 'symbol') {
      setBaseLayerZoom(layer.id, detailZoom.localDetail)
    }
  })
}

async function loadBaseLayers() {
  if (!map) return
  if (usesWarpedRailwayBase) {
    // WTRANS2 tiles use a transformed coordinate space, so raw WGS84 GeoJSON would render offset.
    setSourceData('railways', emptyCollection)
    setSourceData('stations', emptyCollection)
    return
  }
  const [railways, stations] = await Promise.all([fetchRailways(chinaBbox), fetchStations(chinaBbox)])
  setSourceData('railways', withoutSampleFeatures(railways))
  setSourceData('stations', stations)
}

function withoutSampleFeatures(data: GeoJsonFeatureCollection): GeoJsonFeatureCollection {
  return {
    ...data,
    features: data.features.filter((feature) => {
      const properties = feature.properties as Record<string, unknown> | null | undefined
      return properties?.source !== 'sample' && !String(properties?.id ?? '').startsWith('sample-')
    })
  }
}

function addRailwayDataLayers() {
  if (!map) return

  map.addSource('railways', {
    type: 'geojson',
    data: emptyCollection as never
  })
  map.addLayer({
    id: 'railways-casing',
    type: 'line',
    source: 'railways',
    paint: {
      'line-color': '#ffffff',
      'line-width': ['interpolate', ['linear'], ['zoom'], 4, 1.8, 9, 4.4],
      'line-opacity': 0.76
    }
  })
  map.addLayer({
    id: 'railways-line',
    type: 'line',
    source: 'railways',
    paint: {
      'line-color': railwayColorExpression,
      'line-width': ['interpolate', ['linear'], ['zoom'], 4, 1.1, 9, 2.8],
      'line-opacity': 0.94
    }
  })
}

function addStationCircleLayer(
  id: string,
  filter: FilterSpecification,
  minzoom: number,
  radius: ExpressionSpecification,
  color: string,
  strokeColor: string,
  strokeWidth: number,
  maxzoom?: number
) {
  map?.addLayer({
    id,
    type: 'circle',
    source: 'stations',
    minzoom,
    maxzoom,
    filter,
    paint: {
      'circle-radius': radius,
      'circle-color': color,
      'circle-stroke-color': strokeColor,
      'circle-stroke-width': strokeWidth
    }
  })
}

function addStationLabelLayer(
  id: string,
  filter: FilterSpecification,
  minzoom: number,
  size: ExpressionSpecification,
  maxzoom?: number
) {
  map?.addLayer({
    id,
    type: 'symbol',
    source: 'stations',
    minzoom,
    maxzoom,
    filter,
    layout: {
      'text-field': ['coalesce', ['get', 'name_zh'], ['get', 'name_en']],
      'text-font': ['Noto Sans Bold', 'Noto Sans Regular'],
      'text-size': size,
      'text-variable-anchor': ['right', 'left', 'top', 'bottom'],
      'text-radial-offset': 0.55,
      'text-justify': 'auto',
      'symbol-sort-key': ['coalesce', ['get', 'display_rank'], 4],
      'text-allow-overlap': false,
      'text-ignore-placement': false
    },
    paint: {
      'text-color': '#1689ff',
      'text-halo-color': '#ffffff',
      'text-halo-width': 1.8
    }
  })
}

function addStationLayers() {
  if (!map) return

  map.addSource('stations', {
    type: 'geojson',
    data: emptyCollection as never
  })

  addStationCircleLayer(
    'stations-major-circle',
    stationRankAtMost(1),
    detailZoom.majorStation,
    ['interpolate', ['linear'], ['zoom'], 5.8, 4.2, 8, 6.4, 12, 8],
    '#f4a23a',
    '#5f656a',
    2
  )
  addStationCircleLayer(
    'stations-secondary-circle',
    stationRankEquals(2),
    detailZoom.secondaryStation,
    ['interpolate', ['linear'], ['zoom'], 7, 3.6, 10, 5.4, 12, 6.4],
    '#f6e75f',
    '#71824a',
    1.7
  )
  addStationCircleLayer(
    'stations-local-circle',
    stationRankAtLeast(3),
    detailZoom.localStation,
    ['interpolate', ['linear'], ['zoom'], 9.5, 2.7, 12, 4.2, 14, 5.2],
    '#fff37a',
    '#78924a',
    1.2
  )

  addStationLabelLayer(
    'stations-major-label',
    stationRankAtMost(1),
    detailZoom.majorStation,
    ['interpolate', ['linear'], ['zoom'], 5.8, 12, 9, 14.5, 12, 16]
  )
  addStationLabelLayer(
    'stations-secondary-label',
    stationRankEquals(2),
    detailZoom.secondaryStation,
    ['interpolate', ['linear'], ['zoom'], 7, 11.5, 10, 13.5, 12, 15]
  )
  addStationLabelLayer(
    'stations-local-label',
    stationRankAtLeast(3),
    detailZoom.localStation + 0.4,
    ['interpolate', ['linear'], ['zoom'], 9.9, 10.5, 12, 12.5, 14, 13.5]
  )

  map.on('click', 'stations-major-circle', showStationPopup)
  map.on('click', 'stations-secondary-circle', showStationPopup)
  map.on('click', 'stations-local-circle', showStationPopup)
}

function addTrainLayers() {
  if (!map) return

  map.addSource('train-route', {
    type: 'geojson',
    data: emptyCollection as never
  })
  map.addLayer({
    id: 'train-route-glow',
    type: 'line',
    source: 'train-route',
    paint: {
      'line-color': '#f4a62a',
      'line-width': ['interpolate', ['linear'], ['zoom'], 4, 6, 10, 12],
      'line-opacity': 0.18
    }
  })
  map.addLayer({
    id: 'train-route-line',
    type: 'line',
    source: 'train-route',
    paint: {
      'line-color': '#e05a28',
      'line-width': ['interpolate', ['linear'], ['zoom'], 4, 2.6, 10, 5],
      'line-opacity': 0.94
    }
  })

  map.addSource('train-stops', {
    type: 'geojson',
    data: emptyCollection as never
  })
  map.addLayer({
    id: 'train-stops-circle',
    type: 'circle',
    source: 'train-stops',
    paint: {
      'circle-radius': 6,
      'circle-color': '#e05a28',
      'circle-stroke-color': '#ffffff',
      'circle-stroke-width': 2
    }
  })

  map.on('click', 'train-stops-circle', showTrainStopPopup)
}

function addSelectedStationLayer() {
  if (!map) return

  map.addSource('selected-station', {
    type: 'geojson',
    data: emptyCollection as never
  })
  map.addLayer({
    id: 'selected-station-halo',
    type: 'circle',
    source: 'selected-station',
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 6, 12, 10, 17],
      'circle-color': '#ffe95f',
      'circle-opacity': 0.38,
      'circle-stroke-color': '#d85a1f',
      'circle-stroke-width': 2
    }
  })
  map.addLayer({
    id: 'selected-station-core',
    type: 'circle',
    source: 'selected-station',
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 6, 5.5, 10, 8],
      'circle-color': '#ffb72b',
      'circle-stroke-color': '#ffffff',
      'circle-stroke-width': 2.5
    }
  })
  map.addLayer({
    id: 'selected-station-label',
    type: 'symbol',
    source: 'selected-station',
    layout: {
      'text-field': ['coalesce', ['get', 'name_zh'], ['get', 'matched_name'], ['get', 'input_name'], ['get', 'name_en']],
      'text-font': ['Noto Sans Bold', 'Noto Sans Regular'],
      'text-size': ['interpolate', ['linear'], ['zoom'], 6, 13, 10, 16],
      'text-offset': [0, 1.35],
      'text-anchor': 'top',
      'text-allow-overlap': true,
      'icon-allow-overlap': true
    },
    paint: {
      'text-color': '#b93516',
      'text-halo-color': '#ffffff',
      'text-halo-width': 2
    }
  })
}

function escapeHtml(value: unknown) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function showStationPopup(event: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) {
  const feature = event.features?.[0]
  if (!feature?.geometry || feature.geometry.type !== 'Point') return
  const coordinates = feature.geometry.coordinates as [number, number]
  const name = feature.properties?.name_zh ?? '车站'
  new maplibregl.Popup().setLngLat(coordinates).setHTML(`<strong>${escapeHtml(name)}</strong>`).addTo(map as MapLibreMap)
}

function showTrainStopPopup(event: maplibregl.MapMouseEvent & { features?: maplibregl.MapGeoJSONFeature[] }) {
  const feature = event.features?.[0]
  if (!feature?.geometry || feature.geometry.type !== 'Point') return
  const coordinates = feature.geometry.coordinates as [number, number]
  const properties = feature.properties ?? {}
  const name = properties.station_name ?? properties.input_name ?? '经停站'
  const arrive = properties.arrive_time ? String(properties.arrive_time).slice(0, 5) : '--'
  const depart = properties.depart_time ? String(properties.depart_time).slice(0, 5) : '--'
  new maplibregl.Popup()
    .setLngLat(coordinates)
    .setHTML(`<strong>${escapeHtml(name)}</strong><br />到达 ${escapeHtml(arrive)} / 发车 ${escapeHtml(depart)}`)
    .addTo(map as MapLibreMap)
}

function addLayers() {
  configureBaseMapDetailLevels()
  addRailwayDataLayers()
  addStationLayers()
  addTrainLayers()
  addSelectedStationLayer()
}

async function syncWarpedDynamicLayers(options: { fitRoute?: boolean; flySelected?: boolean } = {}) {
  const version = ++wtrans2SyncVersion
  const [warpedStops, warpedSelectedStation] = await Promise.all([
    fetchWarpedStationPoints(stops.value.map((stop) => stop.station_name)),
    fetchWarpedStationPoints(selectedStation.value ? [selectedStation.value.name_zh] : [])
  ])

  if (version !== wtrans2SyncVersion || !map) return

  const trainStops = warpedStopCollection(warpedStops)
  const selected = selectedWarpedStationCollection(warpedSelectedStation)

  setSourceData('train-stops', trainStops)
  setSourceData('train-route', emptyCollection)
  setSourceData('selected-station', selected)

  if (options.fitRoute) {
    fitCoordinates(pointCoordinates(trainStops))
  }

  if (options.flySelected) {
    const [coordinates] = pointCoordinates(selected)
    if (coordinates) {
      flyToCoordinates(coordinates)
    }
  }
}

function syncDynamicLayers() {
  if (usesWarpedRailwayBase) {
    void syncWarpedDynamicLayers()
    return
  }

  setSourceData('train-route', route.value ?? emptyCollection)
  setSourceData('train-stops', stopCollection())
  setSourceData('selected-station', selectedStationCollection())
}

onMounted(() => {
  if (!mapContainer.value) return

  map = new maplibregl.Map({
    container: mapContainer.value,
    style: railwayMapStyle,
    center: [105.8, 34.6],
    zoom: 4.1,
    minZoom: 3,
    maxZoom: 14,
    maxBounds: chinaBounds,
    renderWorldCopies: false,
    localIdeographFontFamily: '"Microsoft YaHei", "Noto Sans CJK SC", sans-serif'
  })

  map.addControl(new maplibregl.NavigationControl({ showCompass: true }), 'top-right')
  map.on('load', () => {
    addLayers()
    syncDynamicLayers()
    loadBaseLayers()
    applyTrainRailHighlight()
  })
})

watch(route, (value) => {
  if (usesWarpedRailwayBase) {
    return
  }

  setSourceData('train-route', value ?? emptyCollection)
  fitCoordinates(routeCoordinates(value))
})

watch(stops, () => {
  if (usesWarpedRailwayBase) {
    void syncWarpedDynamicLayers({ fitRoute: true })
    return
  }

  setSourceData('train-stops', stopCollection())
})

watch(selectedStation, () => {
  if (usesWarpedRailwayBase) {
    void syncWarpedDynamicLayers({ flySelected: true })
    return
  }

  setSourceData('selected-station', selectedStationCollection())
  flyToSelectedStation()
})

watch(detail, () => {
  applyTrainRailHighlight()
})

onUnmounted(() => {
  restoreRailHighlight()
  map?.remove()
  map = null
})
</script>

<template>
  <div class="railway-map-shell">
    <div ref="mapContainer" class="railway-map" />
    <div class="railway-legend" aria-label="铁路图例">
      <div class="legend-title">铁路</div>
      <div class="legend-row">
        <span class="legend-swatch high-speed" />
        <span>高速铁路</span>
      </div>
      <div class="legend-row">
        <span class="legend-swatch rapid" />
        <span>快速铁路、城际铁路</span>
      </div>
      <div class="legend-row">
        <span class="legend-swatch passenger" />
        <span>普通铁路（客运）</span>
      </div>
      <div class="legend-row">
        <span class="legend-swatch freight" />
        <span>普通铁路（货运）</span>
      </div>
      <div class="legend-row">
        <span class="legend-swatch other" />
        <span>其他（专用线、联络线）</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.railway-map-shell {
  position: relative;
  width: 100%;
  height: 100vh;
}

.railway-map {
  width: 100%;
  height: 100%;
}

.railway-legend {
  position: absolute;
  right: 18px;
  bottom: 18px;
  display: grid;
  gap: 8px;
  min-width: 286px;
  border: 1px solid rgb(42 54 60 / 12%);
  border-radius: 6px;
  background: rgb(246 250 252 / 92%);
  box-shadow: 0 10px 28px rgb(20 35 45 / 14%);
  color: #2a3a43;
  font-size: 14px;
  padding: 12px 14px;
}

.legend-title {
  color: #24333b;
  font-size: 16px;
  font-weight: 800;
}

.legend-row {
  display: grid;
  grid-template-columns: 112px 1fr;
  gap: 10px;
  align-items: center;
  white-space: nowrap;
}

.legend-swatch {
  position: relative;
  display: inline-block;
  width: 112px;
  height: 12px;
}

.legend-swatch::before,
.legend-swatch::after {
  position: absolute;
  left: 0;
  width: 112px;
  height: 3px;
  content: '';
}

.legend-swatch::before {
  top: 2px;
}

.legend-swatch::after {
  bottom: 2px;
}

.legend-swatch.high-speed::before,
.legend-swatch.high-speed::after {
  background: #ff553f;
}

.legend-swatch.rapid::before,
.legend-swatch.rapid::after {
  background: #ffa033;
}

.legend-swatch.passenger::before,
.legend-swatch.passenger::after {
  background: #35a852;
}

.legend-swatch.freight::before,
.legend-swatch.freight::after {
  background: #83b93e;
}

.legend-swatch.other::before,
.legend-swatch.other::after {
  background: #7c87c9;
}

@media (max-width: 860px) {
  .railway-map-shell {
    height: 56vh;
  }

  .railway-legend {
    right: 10px;
    bottom: 10px;
    min-width: 250px;
    font-size: 12px;
  }

  .legend-row {
    grid-template-columns: 88px 1fr;
  }

  .legend-swatch,
  .legend-swatch::before,
  .legend-swatch::after {
    width: 88px;
  }
}
</style>
