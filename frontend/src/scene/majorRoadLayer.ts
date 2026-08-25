import * as Cesium from 'cesium'

export const MAJOR_ROADS_GEOJSON_URL = '/data/scene/shanghai-major-roads.geojson'
export const MAJOR_ROADS_FALLBACK_GEOJSON_URL = '/demo/roads/shanghai-major-roads.geojson'
export const MAJOR_ROADS_SOURCE_LABEL = '© OpenStreetMap contributors · Geofabrik Shanghai · 2026-08-24 · WGS84'
export const MAJOR_ROADS_FALLBACK_SOURCE_LABEL = 'SYNTHETIC DEMO · approximate WGS84 lon/lat centerlines'

export interface MajorRoadLayerResult {
  dataSource: Cesium.GeoJsonDataSource
  sourceUrl: string
  sourceLabel: string
  fallback: boolean
}

const ROAD_COLORS = {
  major: Cesium.Color.fromCssColorString('#41545b').withAlpha(0.5),
  elevated: Cesium.Color.fromCssColorString('#60747b').withAlpha(0.62),
  minor: Cesium.Color.fromCssColorString('#314147').withAlpha(0.24),
} as const

function getRoadClass(entity: Cesium.Entity) {
  const properties = entity.properties?.getValue(Cesium.JulianDate.now())
  return typeof properties?.fclass === 'string'
    ? properties.fclass
    : typeof properties?.roadClass === 'string'
      ? properties.roadClass
      : 'major'
}

async function loadRoadDataSource(url: string) {
  return Cesium.GeoJsonDataSource.load(url, {
    clampToGround: true,
    stroke: ROAD_COLORS.major,
    strokeWidth: 1.4,
  })
}

export async function loadMajorRoadLayer(viewer: Cesium.Viewer): Promise<MajorRoadLayerResult> {
  let dataSource: Cesium.GeoJsonDataSource
  let sourceUrl = MAJOR_ROADS_GEOJSON_URL
  let sourceLabel = MAJOR_ROADS_SOURCE_LABEL
  let fallback = false

  try {
    dataSource = await loadRoadDataSource(MAJOR_ROADS_GEOJSON_URL)
  } catch {
    dataSource = await loadRoadDataSource(MAJOR_ROADS_FALLBACK_GEOJSON_URL)
    sourceUrl = MAJOR_ROADS_FALLBACK_GEOJSON_URL
    sourceLabel = MAJOR_ROADS_FALLBACK_SOURCE_LABEL
    fallback = true
  }

  dataSource.name = fallback ? 'Shanghai major roads · synthetic fallback' : 'Shanghai major roads · OSM Geofabrik'
  dataSource.entities.values.forEach((entity) => {
    if (!entity.polyline) return
    const roadClass = getRoadClass(entity)
    const elevated = roadClass === 'motorway' || roadClass === 'trunk' || roadClass === 'elevated'
    const minor = roadClass === 'tertiary' || roadClass === 'secondary'
    entity.polyline.material = new Cesium.ColorMaterialProperty(elevated ? ROAD_COLORS.elevated : minor ? ROAD_COLORS.minor : ROAD_COLORS.major)
    entity.polyline.width = new Cesium.ConstantProperty(elevated ? 2.4 : minor ? 1 : 1.4)
    entity.polyline.clampToGround = new Cesium.ConstantProperty(true)
    entity.polyline.zIndex = new Cesium.ConstantProperty(3)
  })

  await viewer.dataSources.add(dataSource)
  return { dataSource, sourceUrl, sourceLabel, fallback }
}
