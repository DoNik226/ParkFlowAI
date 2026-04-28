<template>
  <div class="parking-map">
    <div v-if="!layout" class="map-empty">
      Карта парковки не загружена
    </div>

    <svg
      v-else
      class="map-svg"
      :viewBox="viewBox"
      preserveAspectRatio="xMidYMid meet"
    >
      <g v-for="spot in layout.spots" :key="spot.id">
        <polygon
          :points="polygonPoints(spot.polygon)"
          :class="['spot', getSpotStatus(spot.id)]"
        />
        <text
          :x="spotCenter(spot).x"
          :y="spotCenter(spot).y"
          text-anchor="middle"
          dominant-baseline="middle"
          class="spot-label"
        >
          {{ spotLabel(spot) }}
        </text>
      </g>
    </svg>

    <div v-if="summary" class="map-summary">
      <span>Всего: {{ summary.total }}</span>
      <span class="free">Свободно: {{ summary.free }}</span>
      <span class="occupied">Занято: {{ summary.occupied }}</span>
      <span class="unknown">Неизвестно: {{ summary.unknown }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

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

const occupancyBySpotId = computed(() => {
  const map = new Map()

  if (!props.occupancy || !Array.isArray(props.occupancy.spots)) {
    return map
  }

  props.occupancy.spots.forEach((item) => {
    map.set(item.spot_id, item)
  })

  return map
})

const summary = computed(() => props.occupancy?.summary || null)

const viewBox = computed(() => {
  const meta = props.layout?.frame_meta

  const width = meta?.width || 1920
  const height = meta?.height || 1080

  return `0 0 ${width} ${height}`
})

function polygonPoints(polygon) {
  if (!Array.isArray(polygon)) return ''
  return polygon.map((p) => `${p.x},${p.y}`).join(' ')
}

function getSpotStatus(spotId) {
  return occupancyBySpotId.value.get(spotId)?.status || 'unknown'
}

function spotCenter(spot) {
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

function spotLabel(spot) {
  if (spot.label) return spot.label
  if (spot.number) return spot.number
  if (spot.id) return spot.id.split('_').at(-1)
  return ''
}
</script>

<style scoped>
.parking-map {
  width: 100%;
  height: 100%;
  min-height: 520px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.map-empty {
  color: #888;
  padding: 24px;
  border: 1px dashed #444;
  border-radius: 12px;
}

.map-svg {
  width: 100%;
  flex: 1;
  min-height: 480px;
  background: #10131a;
  border: 1px solid #2a2f3a;
  border-radius: 16px;
}

.spot {
  stroke-width: 3;
  transition: fill 0.2s ease, stroke 0.2s ease;
}

.spot.free {
  fill: rgba(70, 200, 100, 0.35);
  stroke: #46c864;
}

.spot.occupied {
  fill: rgba(230, 70, 70, 0.42);
  stroke: #e64646;
}

.spot.unknown {
  fill: rgba(160, 160, 160, 0.25);
  stroke: #999;
}

.spot-label {
  fill: #ffffff;
  font-size: 28px;
  font-weight: 700;
  pointer-events: none;
  paint-order: stroke;
  stroke: #111;
  stroke-width: 4px;
}

.map-summary {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  color: #ddd;
  font-size: 14px;
}

.map-summary .free {
  color: #46c864;
}

.map-summary .occupied {
  color: #e64646;
}

.map-summary .unknown {
  color: #aaa;
}
</style>