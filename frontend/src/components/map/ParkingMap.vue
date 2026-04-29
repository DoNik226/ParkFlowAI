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
    <div v-if="!layout" class="empty">Карта не загружена</div>

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
          <g v-for="spot in layout.spots" :key="spot.id">
            <polygon
              :points="polygonPoints(spot.polygon)"
              :class="['spot', getStatus(spot.id)]"
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
      </svg>
    </template>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

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
})

const containerRef = ref(null)

const scale = ref(1)
const offsetX = ref(0)
const offsetY = ref(0)

const isPanning = ref(false)
const lastMouse = ref({ x: 0, y: 0 })

const MIN_SCALE = 0.6
const MAX_SCALE = 5
const SCALE_STEP = 0.18

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
  const width = props.layout?.frame_meta?.width || props.layout?.image?.width || 1920
  const height = props.layout?.frame_meta?.height || props.layout?.image?.height || 1080
  return `0 0 ${width} ${height}`
})

const transform = computed(() => {
  return `translate(${offsetX.value} ${offsetY.value}) scale(${scale.value})`
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
  const width = props.layout?.frame_meta?.width || props.layout?.image?.width || 1920
  const height = props.layout?.frame_meta?.height || props.layout?.image?.height || 1080

  const mouseX = ((event.clientX - rect.left) / rect.width) * width
  const mouseY = ((event.clientY - rect.top) / rect.height) * height

  const scaleRatio = newScale / oldScale

  offsetX.value = mouseX - (mouseX - offsetX.value) * scaleRatio
  offsetY.value = mouseY - (mouseY - offsetY.value) * scaleRatio
  scale.value = newScale
}

function startPan(event) {
  if (event.button !== 0) {
    return
  }

  isPanning.value = true
  lastMouse.value = {
    x: event.clientX,
    y: event.clientY,
  }
}

function onPan(event) {
  if (!isPanning.value) {
    return
  }

  const svg = containerRef.value?.querySelector('svg')
  if (!svg) {
    return
  }

  const rect = svg.getBoundingClientRect()
  const width = props.layout?.frame_meta?.width || props.layout?.image?.width || 1920
  const height = props.layout?.frame_meta?.height || props.layout?.image?.height || 1080

  const dxPx = event.clientX - lastMouse.value.x
  const dyPx = event.clientY - lastMouse.value.y

  const dxViewBox = (dxPx / rect.width) * width
  const dyViewBox = (dyPx / rect.height) * height

  offsetX.value += dxViewBox
  offsetY.value += dyViewBox

  lastMouse.value = {
    x: event.clientX,
    y: event.clientY,
  }
}

function stopPan() {
  isPanning.value = false
}
</script>

<style scoped>
.parking-map {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 520px;
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
  min-height: 520px;
  display: grid;
  place-items: center;
  color: #888;
}

.map-svg {
  width: 100%;
  height: 100%;
  min-height: 520px;
  display: block;
  background: #10131a;
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

.map-tools button:hover {
  background: #ffffff;
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