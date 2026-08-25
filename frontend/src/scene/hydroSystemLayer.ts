import * as Cesium from 'cesium'

export const HUANGPU_RIVER_GEOJSON_URL = '/demo/hydro/huangpu-river.geojson'
export const HUANGPU_RIVER_SOURCE_LABEL = 'SYNTHETIC DEMO · WGS84 lon/lat'

const RIVER_FILL = Cesium.Color.fromCssColorString('#123746').withAlpha(0.5)
const RIVER_STROKE = Cesium.Color.fromCssColorString('#3a6874').withAlpha(0.74)

export async function loadHuangpuHydroSystemLayer(viewer: Cesium.Viewer) {
  const dataSource = await Cesium.GeoJsonDataSource.load(HUANGPU_RIVER_GEOJSON_URL, {
    clampToGround: true,
    fill: RIVER_FILL,
    stroke: RIVER_STROKE,
    strokeWidth: 2,
  })

  dataSource.name = 'Huangpu River · synthetic demo'
  dataSource.entities.values.forEach((entity) => {
    if (!entity.polygon) return
    entity.polygon.heightReference = new Cesium.ConstantProperty(Cesium.HeightReference.CLAMP_TO_GROUND)
    entity.polygon.classificationType = new Cesium.ConstantProperty(Cesium.ClassificationType.TERRAIN)
    entity.polygon.outline = new Cesium.ConstantProperty(true)
    entity.polygon.outlineColor = new Cesium.ConstantProperty(RIVER_STROKE)
    entity.polygon.zIndex = new Cesium.ConstantProperty(1)
  })

  await viewer.dataSources.add(dataSource)
  return dataSource
}
