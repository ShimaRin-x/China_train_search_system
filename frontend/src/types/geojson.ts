export type Position = [number, number]

export interface GeoJsonFeature<G = unknown, P = unknown> {
  type: 'Feature'
  geometry: G
  properties: P
}

export interface GeoJsonFeatureCollection<G = unknown, P = unknown> {
  type: 'FeatureCollection'
  features: Array<GeoJsonFeature<G, P>>
}

export interface PointGeometry {
  type: 'Point'
  coordinates: Position
}

export interface LineStringGeometry {
  type: 'LineString'
  coordinates: Position[]
}
