import { useEffect, useRef, useState } from 'react'
import * as Cesium from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import type { FloodEvent, FloodPoint, ForecastFrame, ForecastKey } from './types'

const CORE_TILES_URL = '/data/shanghai-core/tileset.json'
const CESIUM_ION_TOKEN = import.meta.env.VITE_CESIUM_ION_TOKEN?.trim()
const BIMANGLE_ORIGIN = { lon: 116.46, lat: 39.92 }
const HUANGPU_SHP_CENTER = { lon: 121.47797014, lat: 31.21940076 }
const HUANGPU_MODEL_CENTER_LOCAL = { x: 80.3409, y: -53.0326, z: 90 }
const DEFAULT_EVENT = { lon: 121.4874, lat: 31.2297 }
const OSM_BUILDING_STYLE = new Cesium.Cesium3DTileStyle({ color: "color('#86a8b9', 0.94)" })
const FORECAST_GEOMETRY_URLS: Record<ForecastKey, string> = {
  NOW: '/demo/forecast/now.geojson',
  PLUS_10: '/demo/forecast/plus10.geojson',
  PLUS_30: '/demo/forecast/plus30.geojson',
}
const FORECAST_FILL: Record<ForecastKey, Cesium.Color> = {
  NOW: new Cesium.Color(0.14, 0.84, 0.91, 0.36),
  PLUS_10: new Cesium.Color(0.15, 0.48, 1, 0.38),
  PLUS_30: new Cesium.Color(1, 0.48, 0.18, 0.42),
}
const FORECAST_STROKE: Record<ForecastKey, Cesium.Color> = {
  NOW: new Cesium.Color(0.34, 0.91, 0.95, 0.96),
  PLUS_10: new Cesium.Color(0.48, 0.68, 1, 0.96),
  PLUS_30: new Cesium.Color(1, 0.67, 0.3, 0.98),
}
const MARKER_COLOR: Record<FloodPoint['riskLevel'], Cesium.Color> = {
  NORMAL: new Cesium.Color(0.17, 0.84, 0.78, 1),
  WARNING: new Cesium.Color(1, 0.6, 0.22, 1),
  HIGH: new Cesium.Color(0.95, 0.5, 0.3, 1),
  CRITICAL: new Cesium.Color(0.94, 0.33, 0.3, 1),
}

interface CesiumSceneProps {
  event: FloodEvent | null
  points: FloodPoint[]
  activeForecast: ForecastKey
  forecastFrame: ForecastFrame | null
  selectedPointId: string
  layers: LayerVisibility
  onPointSelect: (id: string) => void
}

type LayerVisibility = {
  base: boolean
  water: boolean
  depth: boolean
  network: boolean
  video: boolean
  measure: boolean
}

function placeHuangpuByRange(tileset: Cesium.Cesium3DTileset) {
  const sourceFrame = Cesium.Transforms.eastNorthUpToFixedFrame(
    Cesium.Cartesian3.fromDegrees(BIMANGLE_ORIGIN.lon, BIMANGLE_ORIGIN.lat, 0),
  )
  const targetFrame = Cesium.Transforms.eastNorthUpToFixedFrame(
    Cesium.Cartesian3.fromDegrees(HUANGPU_SHP_CENTER.lon, HUANGPU_SHP_CENTER.lat, 0),
  )
  const sourceCenterFrame = Cesium.Matrix4.multiply(
    sourceFrame,
    Cesium.Matrix4.fromTranslation(Cesium.Cartesian3.fromElements(
      HUANGPU_MODEL_CENTER_LOCAL.x,
      HUANGPU_MODEL_CENTER_LOCAL.y,
      HUANGPU_MODEL_CENTER_LOCAL.z,
    ), new Cesium.Matrix4()),
    new Cesium.Matrix4(),
  )
  const sourceInverse = Cesium.Matrix4.inverse(sourceCenterFrame, new Cesium.Matrix4())
  tileset.modelMatrix = Cesium.Matrix4.multiply(targetFrame, sourceInverse, new Cesium.Matrix4())
}

export function CesiumScene({ event, points, activeForecast, forecastFrame, selectedPointId, layers, onPointSelect }: CesiumSceneProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const viewerRef = useRef<Cesium.Viewer | null>(null)
  const cityLayerRef = useRef<Cesium.PrimitiveCollection | null>(null)
  const forecastDataSourceRef = useRef<Cesium.GeoJsonDataSource | null>(null)
  const layersDepthRef = useRef(layers.depth)
  const [viewerReady, setViewerReady] = useState(false)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [source, setSource] = useState<'osm' | 'local' | null>(null)
  const [forecastStatus, setForecastStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const selectedPoint = points.find((point) => point.id === selectedPointId) ?? null
  const target = event?.coordinates ?? selectedPoint?.coordinates ?? DEFAULT_EVENT

  useEffect(() => {
    if (!containerRef.current) return

    const viewer = new Cesium.Viewer(containerRef.current, {
      animation: false,
      baseLayer: false,
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      infoBox: false,
      navigationHelpButton: false,
      sceneModePicker: false,
      selectionIndicator: false,
      timeline: false,
      terrain: undefined,
    })
    const cityLayer = new Cesium.PrimitiveCollection()
    viewer.scene.primitives.add(cityLayer)
    cityLayerRef.current = cityLayer
    viewer.scene.backgroundColor = Cesium.Color.fromCssColorString('#071421')
    viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString('#0a2232')
    viewer.scene.globe.enableLighting = false
    viewer.scene.globe.showGroundAtmosphere = false
    viewer.scene.fog.enabled = true
    viewer.scene.fog.density = 0.00008
    viewer.scene.fog.screenSpaceErrorFactor = 2
    viewerRef.current = viewer
    setViewerReady(true)

    let disposed = false
    const flyToShanghai = () => {
      viewer.camera.flyToBoundingSphere(
        new Cesium.BoundingSphere(
          Cesium.Cartesian3.fromDegrees(target.lon, target.lat, 0),
          1200,
        ),
        {
          offset: new Cesium.HeadingPitchRange(
            Cesium.Math.toRadians(28),
            Cesium.Math.toRadians(-28),
            4000,
          ),
          duration: 1,
        },
      )
    }

    const loadLocalCore = async () => {
      try {
        const tileset = await Cesium.Cesium3DTileset.fromUrl(CORE_TILES_URL, { maximumScreenSpaceError: 3 })
        if (disposed) {
          tileset.destroy()
          return
        }
        placeHuangpuByRange(tileset)
        tileset.style = new Cesium.Cesium3DTileStyle({ color: "color('#6f8fa7', 0.96)" })
        cityLayer.add(tileset)
        setSource('local')
        setStatus('ready')
        viewer.camera.flyToBoundingSphere(tileset.boundingSphere, {
          offset: new Cesium.HeadingPitchRange(
            Cesium.Math.toRadians(28),
            Cesium.Math.toRadians(-42),
            6500,
          ),
          duration: 0.8,
        })
      } catch {
        if (!disposed) setStatus('error')
      }
    }

    const loadOsmBuildings = async () => {
      if (!CESIUM_ION_TOKEN) {
        await loadLocalCore()
        return
      }

      try {
        Cesium.Ion.defaultAccessToken = CESIUM_ION_TOKEN
        const tileset = await Cesium.createOsmBuildingsAsync({
          style: OSM_BUILDING_STYLE,
          showOutline: false,
          enableShowOutline: false,
        })
        if (disposed) {
          tileset.destroy()
          return
        }
        cityLayer.add(tileset)
        setSource('osm')
        setStatus('ready')
        flyToShanghai()

        if (!disposed) {
          const imageryLayer = viewer.imageryLayers.addImageryProvider(
            new Cesium.OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/' }),
          )
          imageryLayer.alpha = 0.28
          imageryLayer.brightness = 0.68
          imageryLayer.contrast = 1.08
          imageryLayer.saturation = 0.18
        }
      } catch {
        if (!disposed) await loadLocalCore()
      }
    }

    void loadOsmBuildings()

    return () => {
      disposed = true
      cityLayerRef.current = null
      forecastDataSourceRef.current = null
      viewerRef.current = null
      setViewerReady(false)
      viewer.destroy()
    }
  }, [target.lat, target.lon])

  useEffect(() => {
    layersDepthRef.current = layers.depth
    if (forecastDataSourceRef.current) forecastDataSourceRef.current.show = layers.depth
  }, [layers.depth])

  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || !viewerReady) return

    const markerData: Array<{
      id: string
      selectId: string
      name: string
      coordinates: FloodPoint['coordinates']
      depthCm: number
      riskLevel: FloodPoint['riskLevel']
    }> = points.length > 0
      ? points.map((point) => ({
        id: point.id,
        selectId: point.id,
        name: point.name,
        coordinates: point.coordinates,
        depthCm: point.depthCm,
        riskLevel: point.riskLevel,
      }))
      : event
        ? [{
          id: `event-${event.id}`,
          selectId: selectedPointId || 'FP-001',
          name: event.name,
          coordinates: event.coordinates,
          depthCm: event.currentDepthCm,
          riskLevel: event.riskLevel,
        }]
        : []

    const entities = markerData.map((marker) => {
      const selected = marker.selectId === selectedPointId
      return viewer.entities.add({
        id: `flood-point-${marker.id}`,
        name: marker.name,
        // Contract coordinates are WGS84 lon/lat; fromDegrees performs the geographic placement.
        position: Cesium.Cartesian3.fromDegrees(marker.coordinates.lon, marker.coordinates.lat, 0),
        point: new Cesium.PointGraphics({
          show: true,
          pixelSize: selected ? 16 : 10,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
          color: MARKER_COLOR[marker.riskLevel],
          outlineColor: Cesium.Color.WHITE.withAlpha(0.92),
          outlineWidth: selected ? 3 : 2,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        }),
        label: selected
          ? new Cesium.LabelGraphics({
            text: `${marker.id} · ${marker.depthCm.toFixed(1)} cm`,
            font: '11px sans-serif',
            fillColor: Cesium.Color.fromCssColorString('#ffe0ac'),
            showBackground: true,
            backgroundColor: Cesium.Color.fromCssColorString('#1d2022').withAlpha(0.8),
            pixelOffset: new Cesium.Cartesian2(14, -14),
            heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
          })
          : undefined,
        properties: { floodPointId: marker.selectId },
      })
    })

    return () => {
      if (!viewer.isDestroyed()) entities.forEach((entity) => viewer.entities.remove(entity))
    }
  }, [event, points, selectedPointId, viewerReady])

  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || !viewerReady) return

    const handleClick = (movement: Cesium.ScreenSpaceEventHandler.PositionedEvent) => {
      const picked = viewer.scene.pick(movement.position)
      const entity = picked && picked.id instanceof Cesium.Entity ? picked.id : null
      const properties = entity?.properties?.getValue(Cesium.JulianDate.now())
      if (typeof properties?.floodPointId === 'string') onPointSelect(properties.floodPointId)
    }

    viewer.screenSpaceEventHandler.setInputAction(handleClick, Cesium.ScreenSpaceEventType.LEFT_CLICK)
    return () => viewer.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_CLICK)
  }, [onPointSelect, viewerReady])

  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || !viewerReady) return

    const geometryUrl = forecastFrame?.geometryUrl ?? FORECAST_GEOMETRY_URLS[activeForecast]
    const fill = FORECAST_FILL[activeForecast]
    const stroke = FORECAST_STROKE[activeForecast]
    let cancelled = false
    let loadedDataSource: Cesium.GeoJsonDataSource | null = null
    const previousDataSource = forecastDataSourceRef.current
    forecastDataSourceRef.current = null
    if (previousDataSource) viewer.dataSources.remove(previousDataSource, true)
    setForecastStatus('loading')

    void Cesium.GeoJsonDataSource.load(geometryUrl, {
      clampToGround: true,
      fill,
      stroke,
      strokeWidth: 2,
    }).then((dataSource) => {
      if (cancelled || viewerRef.current !== viewer || viewer.isDestroyed()) return
      dataSource.entities.values.forEach((entity) => {
        if (!entity.polygon) return
        entity.polygon.heightReference = new Cesium.ConstantProperty(Cesium.HeightReference.CLAMP_TO_GROUND)
        entity.polygon.classificationType = new Cesium.ConstantProperty(Cesium.ClassificationType.TERRAIN)
        entity.polygon.outline = new Cesium.ConstantProperty(true)
        entity.polygon.outlineColor = new Cesium.ConstantProperty(stroke)
        entity.polygon.zIndex = new Cesium.ConstantProperty(2)
      })
      dataSource.show = layersDepthRef.current
      loadedDataSource = dataSource
      forecastDataSourceRef.current = dataSource
      viewer.dataSources.add(dataSource)
      setForecastStatus('ready')
    }).catch(() => {
      if (!cancelled) setForecastStatus('error')
    })

    return () => {
      cancelled = true
      if (loadedDataSource && viewerRef.current === viewer && !viewer.isDestroyed()) {
        viewer.dataSources.remove(loadedDataSource, true)
        if (forecastDataSourceRef.current === loadedDataSource) forecastDataSourceRef.current = null
      }
    }
  }, [activeForecast, forecastFrame?.geometryUrl, viewerReady])

  useEffect(() => {
    if (cityLayerRef.current) cityLayerRef.current.show = layers.base
  }, [layers.base])

  return (
    <div
      className="cesium-scene-mount"
      ref={containerRef}
      aria-label="上海 Cesium 三维城市底座"
      data-source={source ?? 'loading'}
      data-forecast-source={activeForecast}
      data-forecast-status={forecastStatus}
    >
      {status === 'loading' && <span className="cesium-scene-status">{CESIUM_ION_TOKEN ? 'OSM BUILDINGS LOADING' : 'LOCAL CITY LOADING'}</span>}
      {status === 'error' && <span className="cesium-scene-status cesium-scene-status--error">CITY DATA UNAVAILABLE</span>}
      {status === 'ready' && source && <span className="cesium-scene-source">{source === 'osm' ? 'OSM BUILDINGS · GLOBAL' : 'LOCAL HUANGPU · FALLBACK'}</span>}
    </div>
  )
}
