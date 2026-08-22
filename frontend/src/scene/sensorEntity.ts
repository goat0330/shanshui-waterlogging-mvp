import * as Cesium from 'cesium'
import type { Coordinates, FloodPoint } from '../types'

export interface GeographicSensorInput {
  entityId: string
  sensorId: string
  floodPointId: string
  name: string
  coordinates: Coordinates
  depthCm: number
  riskLevel: FloodPoint['riskLevel']
  selected: boolean
}

const SENSOR_COLOR: Record<FloodPoint['riskLevel'], Cesium.Color> = {
  NORMAL: new Cesium.Color(0.17, 0.84, 0.78, 1),
  WARNING: new Cesium.Color(1, 0.6, 0.22, 1),
  HIGH: new Cesium.Color(0.95, 0.5, 0.3, 1),
  CRITICAL: new Cesium.Color(0.94, 0.33, 0.3, 1),
}

export function addGeographicSensorEntity(viewer: Cesium.Viewer, sensor: GeographicSensorInput) {
  const position = Cesium.Cartesian3.fromDegrees(sensor.coordinates.lon, sensor.coordinates.lat, 0)
  return viewer.entities.add({
    id: `geographic-sensor-${sensor.entityId}`,
    name: sensor.name,
    position,
    point: new Cesium.PointGraphics({
      show: true,
      pixelSize: sensor.selected ? 16 : 10,
      heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
      color: SENSOR_COLOR[sensor.riskLevel],
      outlineColor: Cesium.Color.WHITE.withAlpha(0.92),
      outlineWidth: sensor.selected ? 3 : 2,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    }),
    label: sensor.selected
      ? new Cesium.LabelGraphics({
        text: `${sensor.floodPointId} · ${sensor.depthCm.toFixed(1)} cm`,
        font: '11px sans-serif',
        fillColor: Cesium.Color.fromCssColorString('#ffe0ac'),
        showBackground: true,
        backgroundColor: Cesium.Color.fromCssColorString('#1d2022').withAlpha(0.8),
        pixelOffset: new Cesium.Cartesian2(14, -14),
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      })
      : undefined,
    properties: {
      floodPointId: sensor.floodPointId,
      sensorId: sensor.sensorId,
      coordinateSystem: 'WGS84 lon/lat',
    },
  })
}
