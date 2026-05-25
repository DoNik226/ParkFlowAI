<template>
  <div
    ref="containerRef"
    class="parking-map"
    @wheel.prevent="onWheel"
    @mousedown="startPan"
    @mousemove="onPan"
    @mouseup="stopPan"
    @mouseleave="stopPan"
  >
    <div v-if="!layout" class="empty">
      Карта не загружена
    </div>

    <template v-else>
      <div class="map-tools">
        <button type="button" @click.stop="zoomIn">+</button>
        <button type="button" @click.stop="zoomOut">−</button>
        <button type="button" @click.stop="resetView">⟳</button>
      </div>

      <svg
        class="map-svg"
        :viewBox="viewBox"
        preserveAspectRatio="xMidYMid meet"
      >
        <g :transform="transform">
          <foreignObject
            v-if="backgroundUrl"
            x="0"
            y="0"
            :width="frameWidth"
            :height="frameHeight"
            class="background-object"
          >
            <video
              v-if="backgroundType === 'video'"
              ref="backgroundVideoRef"
              class="background-media"
              :src="backgroundUrl"
              muted
              loop
              playsinline
              preload="auto"
            />

            <img
              v-else
              class="background-media"
              :src="backgroundUrl"
              alt="Фон парковки"
            >
          </foreignObject>

          <rect
            v-else
            x="0"
            y="0"
            :width="frameWidth"
            :height="frameHeight"
            class="fallback-background"
          />

          <polyline
            v-if="routePoints.length >= 2"
            :points="routePolyline"
            class="route-line"
          />

          <g class="spots-layer">
            <g v-for="spot in layout.spots || []" :key="spot.id">
              <polygon
                :points="polygonPoints(spot.polygon)"
                :class="[
                  'spot',
                  getStatus(spot.id),
                  { selected: selectedSpotId === spot.id }
                ]"
                @mousedown.stop
                @click.stop="$emit('select-spot', spot)"
              />

              <text
                :x="center(spot).x"
                :y="center(spot).y"
                text-anchor="middle"
                dominant-baseline="middle"
                class="spot-label"
              >
                {{ label(spot) }}
              </text>
            </g>
          </g>
        </g>
      </svg>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'

defineEmits(['select-spot'])

const props = defineProps({
  layout: {
    type: Object,
    default: null,
  },
  occupancy: {
    type: Object,
    default: null,
  },
  mapData: {
    type: Object,
    default: null,
  },
  routePath: {
    type: Array,
    default: () => [],
  },
  selectedSpotId: {
    type: String,
    default: null,
  },
  selectedEntranceId: {
    type: String,
    default: null,
  },
  backgroundUrl: {
    type: String,
    default: '',
  },
  backgroundType: {
    type: String,
    default: '',
  },
  backgroundPlaying: {
    type: Boolean,
    default: false,
  },
})

const containerRef = ref(null)
const backgroundVideoRef = ref(null)

const scale = ref(1)
const offsetX = ref(0)
const offsetY = ref(0)

const isPanning = ref(false)
const lastMouse = ref({ x: 0, y: 0 })

const MIN_SCALE = 0.6
const MAX_SCALE = 5
const SCALE_STEP = 0.18

const frameWidth = computed(() => {
  return Number(props.layout?.frame_meta?.width || props.layout?.image?.width || 1920)
})

const frameHeight = computed(() => {
  return Number(props.layout?.frame_meta?.height || props.layout?.image?.height || 1080)
})

const vertices = computed(() => {
  return Array.isArray(props.mapData?.vertices) ? props.mapData.vertices : []
})

const vertexById = computed(() => {
  const map = new Map()

  vertices.value.forEach((vertex) => {
    map.set(vertex.id, vertex)
    map.set(String(vertex.id), vertex)
  })

  return map
})

const occupancyBySpotId = computed(() => {
  const map = new Map()

  if (!props.occupancy?.spots) {
    return map
  }

  props.occupancy.spots.forEach((item) => {
    map.set(item.spot_id, item)
  })

  return map
})

const viewBox = computed(() => {
  return `0 0 ${frameWidth.value} ${frameHeight.value}`
})

const transform = computed(() => {
  return `translate(${offsetX.value} ${offsetY.value}) scale(${scale.value})`
})

const routePoints = computed(() => {
  return props.routePath
    .map((vertexId) => vertexById.value.get(String(vertexId)))
    .filter(Boolean)
})

const routePolyline = computed(() => {
  return routePoints.value.map((point) => `${point.x},${point.y}`).join(' ')
})

function polygonPoints(polygon) {
  return (polygon || []).map((p) => `${p.x},${p.y}`).join(' ')
}

function getStatus(spotId) {
  return occupancyBySpotId.value.get(spotId)?.status || 'unknown'
}

function center(spot) {
  const polygon = spot.polygon || []

  if (!polygon.length) {
    return { x: 0, y: 0 }
  }

  const sum = polygon.reduce(
    (acc, p) => {
      acc.x += Number(p.x) || 0
      acc.y += Number(p.y) || 0
      return acc
    },
    { x: 0, y: 0 }
  )

  return {
    x: sum.x / polygon.length,
    y: sum.y / polygon.length,
  }
}

function label(spot) {
  if (spot.label) return spot.label
  if (spot.number) return spot.number
  if (spot.id) return spot.id.split('_').at(-1)
  return ''
}

function clampScale(value) {
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, value))
}

function zoomIn() {
  scale.value = clampScale(scale.value + SCALE_STEP)
}

function zoomOut() {
  scale.value = clampScale(scale.value - SCALE_STEP)
}

function resetView() {
  scale.value = 1
  offsetX.value = 0
  offsetY.value = 0
}

function onWheel(event) {
  const direction = event.deltaY < 0 ? 1 : -1
  const oldScale = scale.value
  const newScale = clampScale(oldScale + direction * SCALE_STEP)

  if (newScale === oldScale) {
    return
  }

  const svg = event.currentTarget.querySelector('svg')

  if (!svg) {
    scale.value = newScale
    return
  }

  const rect = svg.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top

  const svgX = (x / rect.width) * frameWidth.value
  const svgY = (y / rect.height) * frameHeight.value

  offsetX.value = svgX - ((svgX - offsetX.value) / oldScale) * newScale
  offsetY.value = svgY - ((svgY - offsetY.value) / oldScale) * newScale
  scale.value = newScale
}

function startPan(event) {
  if (event.button !== 0) return

  isPanning.value = true
  lastMouse.value = {
    x: event.clientX,
    y: event.clientY,
  }
}

function onPan(event) {
  if (!isPanning.value) return

  const dx = event.clientX - lastMouse.value.x
  const dy = event.clientY - lastMouse.value.y

  const svg = containerRef.value?.querySelector('svg')
  const rect = svg?.getBoundingClientRect()

  if (rect) {
    offsetX.value += (dx / rect.width) * frameWidth.value
    offsetY.value += (dy / rect.height) * frameHeight.value
  } else {
    offsetX.value += dx
    offsetY.value += dy
  }

  lastMouse.value = {
    x: event.clientX,
    y: event.clientY,
  }
}

function stopPan() {
  isPanning.value = false
}

async function syncBackgroundVideoPlayback() {
  await nextTick()

  const video = backgroundVideoRef.value

  if (!video) {
    return
  }

  if (props.backgroundPlaying) {
    try {
      await video.play()
    } catch (error) {
      console.warn('Не удалось запустить видео-фон:', error)
    }
  } else {
    video.pause()
  }
}

watch(
  () => [props.backgroundUrl, props.backgroundType, props.backgroundPlaying],
  () => {
    syncBackgroundVideoPlayback()
  },
  { immediate: true }
)
</script>

<style scoped>
.parking-map {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 620px;
  overflow: hidden;
  border-radius: 16px;
  background: #10131a;
  border: 2px solid #2d8fe3;
  cursor: grab;
  user-select: none;
}

.parking-map:active {
  cursor: grabbing;
}

.empty {
  min-height: 620px;
  display: grid;
  place-items: center;
  color: #888;
}

.map-svg {
  width: 100%;
  height: 100%;
  min-height: 620px;
  display: block;
  background: #10131a;
}

.background-object {
  pointer-events: none;
}

.background-media {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: fill;
}

.fallback-background {
  fill: #10131a;
}

.map-tools {
  position: absolute;
  right: 16px;
  top: 50%;
  z-index: 3;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transform: translateY(-50%);
}

.map-tools button {
  width: 44px;
  height: 44px;
  border: none;
  border-radius: 10px;
  background: #e9edf2;
  color: #111827;
  font-size: 22px;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
}

.route-line {
  fill: none;
  stroke: #fbbf24;
  stroke-width: 10;
  stroke-linecap: round;
  stroke-linejoin: round;
  filter: drop-shadow(0 0 6px rgba(251, 191, 36, 0.8));
}

.spot {
  stroke-width: 3;
  cursor: pointer;
  transition: opacity 0.2s ease, stroke-width 0.2s ease;
}

.spot:hover {
  opacity: 0.8;
  stroke-width: 5;
}

.spot.free {
  fill: rgba(70, 200, 100, 0.35);
  stroke: #31c85f;
}

.spot.occupied {
  fill: rgba(230, 70, 70, 0.45);
  stroke: #e64646;
}

.spot.unknown {
  fill: rgba(160, 160, 160, 0.25);
  stroke: #999;
}

.spot.selected {
  stroke: #fbbf24;
  stroke-width: 6;
}

.spot-label {
  fill: #fff;
  font-size: 26px;
  font-weight: 800;
  paint-order: stroke;
  stroke: #111;
  stroke-width: 4px;
  pointer-events: none;
}
</style>
