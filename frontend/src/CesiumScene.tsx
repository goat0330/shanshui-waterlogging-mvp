import { useEffect, useRef, useState } from 'react'
import * as Cesium from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import type { FloodEvent, FloodPoint, ForecastFrame, ForecastKey, SensorState } from './types'
import { addDemoCityBlocks } from './scene/demoCityLayer'
import { HUANGPU_RIVER_GEOJSON_URL, HUANGPU_RIVER_SOURCE_LABEL, loadHuangpuHydroSystemLayer } from './scene/hydroSystemLayer'
import { addGeographicSensorEntity } from './scene/sensorEntity'

const CORE_TILES_URL = '/data/runtime/shanghai-core/tileset.json'
const CESIUM_ION_TOKEN = import.meta.env.VITE_CESIUM_ION_TOKEN?.trim()
const SENSOR_STATE_SOURCE = 'sensor-state-input'
const FLOOD_POINT_FALLBACK_SOURCE = 'floodpoint-fallback'
const EVENT_FALLBACK_SOURCE = 'event-fallback'
const BIMANGLE_ORIGIN = { lon: 116.46, lat: 39.92 }
const HUANGPU_SHP_CENTER = { lon: 121.47797014, lat: 31.21940076 }
const HUANGPU_MODEL_CENTER_LOCAL = { x: 80.3409, y: -53.0326, z: 90 }
const DEFAULT_EVENT = { lon: 121.4874, lat: 31.2297 }
const OSM_BUILDING_STYLE = new Cesium.Cesium3DTileStyle({ color: "color('#86a8b9', 0.94)" })
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
interface CesiumSceneProps {
  event: FloodEvent | null
  points: FloodPoint[]
  sensor?: SensorState | null
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

function flyToTarget(viewer: Cesium.Viewer, target: { lon: number; lat: number }, duration = 0.8) {
  viewer.camera.flyToBoundingSphere(
    new Cesium.BoundingSphere(
      Cesium.Cartesian3.fromDegrees(target.lon, target.lat, 0),
      900,
    ),
    {
      offset: new Cesium.HeadingPitchRange(
        Cesium.Math.toRadians(28),
        Cesium.Math.toRadians(-34),
        3200,
      ),
      duration,
    },
  )
}

export function CesiumScene({ event, points, sensor = null, activeForecast, forecastFrame, selectedPointId, layers, onPointSelect }: CesiumSceneProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const viewerRef = useRef<Cesium.Viewer | null>(null)
  const cityLayerRef = useRef<Cesium.PrimitiveCollection | null>(null)
  const hydroDataSourceRef = useRef<Cesium.GeoJsonDataSource | null>(null)
  const forecastDataSourceRef = useRef<Cesium.GeoJsonDataSource | null>(null)
  const layersDepthRef = useRef(layers.depth)
  const [viewerReady, setViewerReady] = useState(false)
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [source, setSource] = useState<'osm' | 'local' | 'demo' | null>(null)
  const [hydroStatus, setHydroStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [forecastStatus, setForecastStatus] = useState<'loading' | 'ready' | 'empty' | 'error'>('loading')
  const [sensorEntityCount, setSensorEntityCount] = useState(0)
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
        if (disposed) return
        try {
          addDemoCityBlocks(cityLayer)
          setSource('demo')
          setStatus('ready')
          flyToTarget(viewer, target)
        } catch {
          setStatus('error')
        }
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
        flyToTarget(viewer, target, 1)

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
      hydroDataSourceRef.current = null
      forecastDataSourceRef.current = null
      viewerRef.current = null
      setViewerReady(false)
      viewer.destroy()
    }
  }, [])

  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || !viewerReady) return
    flyToTarget(viewer, target)
  }, [target.lat, target.lon, viewerReady])

  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || !viewerReady) return

    let cancelled = false
    setHydroStatus('loading')
    void loadHuangpuHydroSystemLayer(viewer).then((dataSource) => {
      if (cancelled || viewerRef.current !== viewer || viewer.isDestroyed()) {
        if (!viewer.isDestroyed()) viewer.dataSources.remove(dataSource, true)
        return
      }
      dataSource.show = layers.water
      hydroDataSourceRef.current = dataSource
      setHydroStatus('ready')
    }).catch(() => {
      if (!cancelled) setHydroStatus('error')
    })

    return () => {
      cancelled = true
      if (hydroDataSourceRef.current && viewerRef.current === viewer && !viewer.isDestroyed()) {
        viewer.dataSources.remove(hydroDataSourceRef.current, true)
        hydroDataSourceRef.current = null
      }
    }
  }, [viewerReady])

  useEffect(() => {
    layersDepthRef.current = layers.depth
    if (forecastDataSourceRef.current) forecastDataSourceRef.current.show = layers.depth
  }, [layers.depth])

  useEffect(() => {
    if (hydroDataSourceRef.current) hydroDataSourceRef.current.show = layers.water
  }, [layers.water])

  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || !viewerReady) return

    const markerData: Array<{
      id: string
      selectId: string
      sensorId: string
      siteId?: string
      eventId?: string
      name: string
      source: string
      coordinates: FloodPoint['coordinates']
      depthCm: number
      riskLevel: FloodPoint['riskLevel']
      fallback: boolean
    }> = sensor
      ? [{
        id: sensor.sensorId,
        selectId: selectedPointId || 'FP-001',
        sensorId: sensor.sensorId,
        siteId: sensor.siteId,
        eventId: event?.id,
        name: event?.name ?? selectedPoint?.name ?? sensor.siteId,
        source: sensor.source ?? SENSOR_STATE_SOURCE,
        coordinates: sensor.coordinates,
        depthCm: sensor.depthCm,
        riskLevel: event?.riskLevel ?? selectedPoint?.riskLevel ?? 'NORMAL',
        fallback: false,
      }]
      : points.length > 0
        ? points.map((point) => ({
          id: `floodpoint-fallback-${point.id}`,
          selectId: point.id,
          sensorId: `floodpoint-fallback-${point.id}`,
          eventId: point.id === selectedPointId ? event?.id : undefined,
          name: point.name,
          source: FLOOD_POINT_FALLBACK_SOURCE,
          coordinates: point.coordinates,
          depthCm: point.depthCm,
          riskLevel: point.riskLevel,
          fallback: true,
        }))
        : event
          ? [{
            id: `event-fallback-${event.id}`,
            selectId: selectedPointId || 'FP-001',
            sensorId: `event-fallback-${event.id}`,
            eventId: event.id,
            name: event.name,
            source: EVENT_FALLBACK_SOURCE,
            coordinates: event.coordinates,
            depthCm: event.currentDepthCm,
            riskLevel: event.riskLevel,
            fallback: true,
          }]
          : []

    const entities = markerData.map((marker) => addGeographicSensorEntity(viewer, {
      entityId: marker.id,
      sensorId: marker.sensorId,
      floodPointId: marker.selectId,
      name: marker.name,
      coordinates: marker.coordinates,
      depthCm: marker.depthCm,
      riskLevel: marker.riskLevel,
      selected: marker.selectId === selectedPointId,
      source: marker.source,
      eventId: marker.eventId,
      siteId: marker.siteId,
      fallback: marker.fallback,
    }))
    setSensorEntityCount(entities.length)

    return () => {
      if (!viewer.isDestroyed()) entities.forEach((entity) => viewer.entities.remove(entity))
    }
  }, [event, points, selectedPointId, sensor, selectedPoint, viewerReady])

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
    return () => {
      if (!viewer.isDestroyed()) viewer.screenSpaceEventHandler.removeInputAction(Cesium.ScreenSpaceEventType.LEFT_CLICK)
    }
  }, [onPointSelect, viewerReady])

  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || !viewerReady) return

    const geometryUrl = forecastFrame?.geometryUrl
    const fill = FORECAST_FILL[activeForecast]
    const stroke = FORECAST_STROKE[activeForecast]
    let cancelled = false
    let loadedDataSource: Cesium.GeoJsonDataSource | null = null
    const previousDataSource = forecastDataSourceRef.current
    forecastDataSourceRef.current = null
    if (previousDataSource) viewer.dataSources.remove(previousDataSource, true)
    if (!geometryUrl) {
      setForecastStatus('empty')
      return () => {
        cancelled = true
      }
    }
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
      data-local-tileset={CORE_TILES_URL}
      data-coordinate-system="WGS84 lon/lat"
      data-hydro-source={HUANGPU_RIVER_GEOJSON_URL}
      data-hydro-attribution={HUANGPU_RIVER_SOURCE_LABEL}
      data-hydro-status={hydroStatus}
      data-sensor-entity-count={sensorEntityCount}
      data-sensor-mode={sensor ? 'sensor-state' : 'floodpoint-fallback'}
      data-sensor-id={sensor?.sensorId ?? 'none'}
      data-sensor-source={sensor?.source ?? (sensor ? SENSOR_STATE_SOURCE : FLOOD_POINT_FALLBACK_SOURCE)}
      data-sensor-depth-cm={sensor ? String(sensor.depthCm) : 'none'}
      data-selected-point-id={selectedPointId}
      data-selected-event-id={event?.id ?? 'none'}
      data-forecast-source={activeForecast}
      data-forecast-geometry={forecastFrame?.geometryUrl ?? 'none'}
      data-forecast-status={forecastStatus}
    >
      {status === 'loading' && <span className="cesium-scene-status">{CESIUM_ION_TOKEN ? 'OSM BUILDINGS LOADING' : 'LOCAL CITY LOADING'}</span>}
      {status === 'error' && <span className="cesium-scene-status cesium-scene-status--error">CITY DATA UNAVAILABLE</span>}
      {status === 'ready' && source && <span className="cesium-scene-source">{source === 'osm' ? 'OSM BUILDINGS · GLOBAL' : source === 'local' ? 'LOCAL HUANGPU · FALLBACK' : 'DEMO CITY BLOCKS · FALLBACK'}</span>}
    </div>
  )
}
