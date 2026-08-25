import * as Cesium from 'cesium'

const DEMO_BLOCKS = [
  { id: 'demo-block-01', lon: 121.4808, lat: 31.2392, width: 180, depth: 240, height: 150 },
  { id: 'demo-block-02', lon: 121.4898, lat: 31.2382, width: 220, depth: 180, height: 210 },
  { id: 'demo-block-03', lon: 121.5002, lat: 31.2362, width: 160, depth: 210, height: 120 },
  { id: 'demo-block-04', lon: 121.4778, lat: 31.2282, width: 210, depth: 160, height: 96 },
  { id: 'demo-block-05', lon: 121.4938, lat: 31.2248, width: 150, depth: 230, height: 180 },
  { id: 'demo-block-06', lon: 121.5054, lat: 31.2204, width: 230, depth: 180, height: 132 },
  { id: 'demo-block-07', lon: 121.4708, lat: 31.2172, width: 180, depth: 190, height: 112 },
  { id: 'demo-block-08', lon: 121.4842, lat: 31.2118, width: 220, depth: 150, height: 86 },
  { id: 'demo-block-09', lon: 121.5018, lat: 31.2078, width: 150, depth: 190, height: 144 },
] as const

const BUILDING_COLORS = [
  '#c8c2b8',
  '#d0cbc2',
  '#b9b6b0',
  '#c4bdb2',
  '#d3cdc2',
  '#b5b3ae',
] as const

export function addDemoCityBlocks(collection: Cesium.PrimitiveCollection) {
  const geometryInstances = DEMO_BLOCKS.map((block, index) => new Cesium.GeometryInstance({
    id: block.id,
    geometry: Cesium.BoxGeometry.fromDimensions({
      dimensions: new Cesium.Cartesian3(block.width, block.depth, block.height),
      vertexFormat: Cesium.PerInstanceColorAppearance.VERTEX_FORMAT,
    }),
    modelMatrix: Cesium.Transforms.eastNorthUpToFixedFrame(
      Cesium.Cartesian3.fromDegrees(block.lon, block.lat, block.height / 2),
    ),
    attributes: {
      color: Cesium.ColorGeometryInstanceAttribute.fromColor(
        Cesium.Color.fromCssColorString(BUILDING_COLORS[index % BUILDING_COLORS.length]),
      ),
    },
  }))

  return collection.add(new Cesium.Primitive({
    geometryInstances,
    appearance: new Cesium.PerInstanceColorAppearance({
      flat: false,
      translucent: false,
      closed: true,
      faceForward: true,
    }),
    asynchronous: false,
  }))
}
