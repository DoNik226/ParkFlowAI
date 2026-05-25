<template>
  <section class="editor-page">
    <aside class="sidebar">
      <h2>ParkFlow AI</h2>

      <div class="block">
        <label>Парковка</label>
        <input :value="parkingId" disabled>
      </div>

      <div class="block">
        <label>Название</label>
        <input v-model="parkingName">
      </div>

      <hr>

      <button
        class="btn"
        :class="{ active: addMode }"
        :disabled="!imageLoaded"
        @click="toggleAddMode"
      >
        {{ addMode ? 'Отмена добавления' : '+ Добавить зону' }}
      </button>

      <div v-if="addMode" class="hint">
        Кликни 4 угла зоны по порядку:
        передний левый → передний правый → задний правый → задний левый.
      </div>

      <hr>

      <div class="section-title">
        Зоны: {{ zones.length }}
      </div>

      <div class="zones-list">
        <button
          v-for="(zone, index) in zones"
          :key="zone.id"
          class="zone-item"
          :class="{ selected: selectedZoneId === zone.id }"
          @click="selectZone(zone.id)"
        >
          <span>Зона {{ index + 1 }}</span>
          <b>{{ zone.cols }}×{{ zone.rows }}</b>
        </button>
      </div>

      <div v-if="selectedZone" class="edit-zone">
        <div class="section-title">Выбранная зона</div>

        <label>Мест в ряду</label>
        <input v-model.number="selectedZone.cols" type="number" min="1">

        <label>Рядов</label>
        <input v-model.number="selectedZone.rows" type="number" min="1">

        <button class="btn danger" @click="deleteSelectedZone">
          Удалить зону
        </button>
      </div>

      <div v-if="selectedSpotInfo" class="edit-zone">
        <div class="section-title">Выбранное место</div>

        <div class="selected-spot-title">
          {{ selectedSpotInfo.label }}
        </div>

        <div class="hint">
          Потяни синие точки выбранного места, чтобы вручную подогнать его границы под реальную разметку.
        </div>

        <button class="btn" @click="resetSelectedSpotPolygon">
          Сбросить место к сетке
        </button>
      </div>

      <hr>

      <div class="stats">
        <div>
          <span>Зон</span>
          <b>{{ zones.length }}</b>
        </div>

        <div>
          <span>Мест</span>
          <b>{{ spotsCount }}</b>
        </div>

        <div>
          <span>Масштаб</span>
          <b>{{ Math.round(scale * 100) }}%</b>
        </div>
      </div>

      <hr>

      <button class="btn success" :disabled="saving || !imageLoaded" @click="saveLayout">
        {{ saving ? 'Сохранение...' : 'Сохранить layout' }}
      </button>

      <button class="btn" @click="resetView">
        Сбросить вид
      </button>

      <button class="btn" @click="goSetup">
        Назад к настройке
      </button>

      <button class="btn" @click="goMapEditor">
        Конструктор цифровой карты
      </button>

      <div v-if="message" class="message success-message">
        {{ message }}
      </div>

      <div v-if="error" class="message error-message">
        {{ error }}
      </div>
    </aside>

    <main
      ref="canvasWrapRef"
      class="canvas-wrap"
      @wheel.prevent="onWheel"
    >
      <canvas
        ref="canvasRef"
        @mousedown="onMouseDown"
        @mousemove="onMouseMove"
        @mouseup="onMouseUp"
        @mouseleave="onMouseUp"
        @contextmenu.prevent
      />

      <div v-if="!imageLoaded && !loading" class="empty">
        Скриншот не найден. Сначала загрузите или получите скриншот на странице настройки парковки.
      </div>

      <div v-if="loading" class="empty">
        Загрузка редактора...
      </div>

      <div class="top-bar">
        {{ modeText }}
      </div>
    </main>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { parkingService } from '@/services/parking'

const route = useRoute()
const router = useRouter()

const parkingId = String(route.params.parkingId)

const canvasRef = ref(null)
const canvasWrapRef = ref(null)

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const message = ref('')

const parking = ref(null)
const parkingName = ref('')

const image = ref(null)
const imageLoaded = ref(false)
const imageObjectUrl = ref('')

const zones = ref([])
const selectedZoneId = ref(null)

const addMode = ref(false)
const addPoints = ref([])

const selectedSpotKey = ref(null)
const spotOverrides = ref({})

// const newZoneCols = ref(5)
// const newZoneRows = ref(1)

const scale = ref(1)
const offsetX = ref(0)
const offsetY = ref(0)

const isPanning = ref(false)
const isDraggingPoint = ref(false)
const isDraggingSpotPoint = ref(false)

const dragging = ref({
  zoneId: null,
  pointIndex: -1,
})

const draggingSpot = ref({
  key: null,
  pointIndex: -1,
})

const lastMouse = ref({
  x: 0,
  y: 0,
})

const selectedZone = computed(() => {
  return zones.value.find((zone) => zone.id === selectedZoneId.value) || null
})

const selectedSpotInfo = computed(() => {
  if (!selectedSpotKey.value) return null

  for (const zone of zones.value) {
    const rows = Math.max(1, Number(zone.rows) || 1)
    const cols = Math.max(1, Number(zone.cols) || 1)

    for (let row = 0; row < rows; row += 1) {
      for (let col = 0; col < cols; col += 1) {
        const key = makeSpotKey(zone.id, row, col)

        if (key === selectedSpotKey.value) {
          return {
            key,
            zone,
            row,
            col,
            label: `Зона ${zones.value.indexOf(zone) + 1}, ряд ${row + 1}, место ${col + 1}`,
          }
        }
      }
    }
  }

  return null
})

const spotsCount = computed(() => {
  return zones.value.reduce((sum, zone) => {
    return sum + Number(zone.cols || 0) * Number(zone.rows || 0)
  }, 0)
})

const modeText = computed(() => {
  if (!imageLoaded.value) return 'Скриншот не загружен'
  if (addMode.value) return `Добавление зоны: точка ${addPoints.value.length + 1} из 4`
  if (selectedSpotInfo.value) return 'Выбрано место. Можно двигать его вершины вручную.'
  if (selectedZone.value) return 'Выбрана зона. Можно двигать углы. Клик по месту выбирает его для ручной корректировки.'
  return 'Режим просмотра. Колесо — масштаб, ЛКМ по пустому месту — перемещение.'
})

function showMessage(text) {
  message.value = text
  error.value = ''

  setTimeout(() => {
    message.value = ''
  }, 3000)
}

function showError(text) {
  error.value = text
  message.value = ''
}

async function loadEditor() {
  loading.value = true
  error.value = ''

  try {
    parking.value = await parkingService.getParking(parkingId)
    parkingName.value = parking.value.name

    await loadExistingLayout()
    await loadSnapshotImage()

    await nextTick()
    resizeCanvas()
    fitImageToCanvas()
    render()
  } catch (err) {
    console.error('Ошибка загрузки редактора:', err)
    showError('Не удалось загрузить редактор')
  } finally {
    loading.value = false
  }
}

async function loadExistingLayout() {
  try {
    const layout = await parkingService.getLayout(parkingId)

    const loadedZones = Array.isArray(layout.zones)
      ? layout.zones.map((zone, index) => ({
          id: zone.id || `zone_${index + 1}`,
          corners: normalizeCorners(zone.corners || zone.polygon || []),
          cols: Number(zone.cols || 1),
          rows: Number(zone.rows || 1),
        }))
      : []

    zones.value = loadedZones

    const overrides = {}

    if (Array.isArray(layout.spots)) {
      layout.spots.forEach((spot) => {
        const zoneId = spot.zone_id || spot.zoneId
        const row = Number(spot.row || 1) - 1
        const col = Number(spot.col || 1) - 1
        const polygon = normalizeCorners(spot.polygon || spot.corners || [])

        if (!zoneId || row < 0 || col < 0 || polygon.length !== 4) {
          return
        }

        overrides[makeSpotKey(zoneId, row, col)] = polygon
      })
    }

    spotOverrides.value = overrides
  } catch {
    zones.value = []
    spotOverrides.value = {}
  }
}

async function loadSnapshotImage() {
  try {
    const blob = await parkingService.getSnapshotBlob(parkingId)

    if (imageObjectUrl.value) {
      URL.revokeObjectURL(imageObjectUrl.value)
    }

    imageObjectUrl.value = URL.createObjectURL(blob)

    await new Promise((resolve, reject) => {
      const img = new Image()

      img.onload = () => {
        image.value = img
        imageLoaded.value = true
        resolve()
      }

      img.onerror = reject
      img.src = imageObjectUrl.value
    })
  } catch {
    image.value = null
    imageLoaded.value = false
  }
}

function normalizeCorners(points) {
  return points.map((point) => ({
    x: Number(point.x),
    y: Number(point.y),
  }))
}


function getCurrentCamera() {
  if (parking.value?.camera) {
    return parking.value.camera
  }

  if (Array.isArray(parking.value?.cameras) && parking.value.cameras.length) {
    return parking.value.cameras[0]
  }

  return {
    source_type: parking.value?.source_type,
    source_url: parking.value?.source_url,
    test_video_path: parking.value?.test_video_path,
  }
}

function getFrameWidth() {
  if (!image.value) return 0
  return Number(image.value.naturalWidth || image.value.videoWidth || 0)
}

function getFrameHeight() {
  if (!image.value) return 0
  return Number(image.value.naturalHeight || image.value.videoHeight || 0)
}

function resizeCanvas() {
  const canvas = canvasRef.value
  const wrap = canvasWrapRef.value

  if (!canvas || !wrap) return

  canvas.width = wrap.clientWidth
  canvas.height = wrap.clientHeight

  render()
}

function fitImageToCanvas() {
  const canvas = canvasRef.value
  const img = image.value

  if (!canvas || !img) return

  const padding = 40

  const availableWidth = Math.max(100, canvas.width - padding * 2)
  const availableHeight = Math.max(100, canvas.height - padding * 2)

  const imageWidth = img.naturalWidth
  const imageHeight = img.naturalHeight

  const fitScale = Math.min(
    availableWidth / imageWidth,
    availableHeight / imageHeight
  )

  scale.value = clamp(fitScale, 0.05, 6)

  offsetX.value = (canvas.width - imageWidth * scale.value) / 2
  offsetY.value = (canvas.height - imageHeight * scale.value) / 2

  render()
}

function clearCanvas() {
  const canvas = canvasRef.value
  const ctx = canvas?.getContext('2d')

  if (!canvas || !ctx) return

  ctx.clearRect(0, 0, canvas.width, canvas.height)
}

function render() {
  const canvas = canvasRef.value
  const ctx = canvas?.getContext('2d')

  if (!canvas || !ctx) return

  clearCanvas()

  if (!image.value) return

  ctx.save()
  ctx.translate(offsetX.value, offsetY.value)
  ctx.scale(scale.value, scale.value)

  ctx.drawImage(image.value, 0, 0, getFrameWidth(), getFrameHeight())

  zones.value.forEach((zone, index) => {
    drawZone(ctx, zone, index)
  })

  if (addMode.value && addPoints.value.length) {
    drawAddingPreview(ctx)
  }

  ctx.restore()
}

function drawZone(ctx, zone, index) {
  const grid = buildZoneGrid(zone)
  const selected = selectedZoneId.value === zone.id
  const rows = Math.max(1, Number(zone.rows) || 1)
  const cols = Math.max(1, Number(zone.cols) || 1)

  ctx.save()

  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      const key = makeSpotKey(zone.id, row, col)
      const polygon = getSpotPolygon(zone, row, col, grid)
      const spotSelected = selectedSpotKey.value === key

      ctx.beginPath()
      ctx.moveTo(polygon[0].x, polygon[0].y)

      for (let i = 1; i < polygon.length; i += 1) {
        ctx.lineTo(polygon[i].x, polygon[i].y)
      }

      ctx.closePath()

      ctx.fillStyle = spotSelected
        ? 'rgba(255, 193, 7, 0.25)'
        : selected
          ? 'rgba(255, 193, 7, 0.13)'
          : 'rgba(33, 150, 243, 0.12)'

      ctx.fill()

      ctx.strokeStyle = spotSelected ? '#ffc107' : selected ? '#2d8fe3' : 'rgba(45, 143, 227, 0.9)'
      ctx.lineWidth = spotSelected ? 4 / scale.value : 1.5 / scale.value
      ctx.stroke()

      if (spotSelected) {
        polygon.forEach((point, pointIndex) => {
          ctx.beginPath()
          ctx.arc(point.x, point.y, 7 / scale.value, 0, Math.PI * 2)
          ctx.fillStyle = '#38bdf8'
          ctx.fill()
          ctx.strokeStyle = '#111827'
          ctx.lineWidth = 1.5 / scale.value
          ctx.stroke()

          ctx.fillStyle = '#111827'
          ctx.font = `bold ${11 / scale.value}px Arial`
          ctx.fillText(String(pointIndex + 1), point.x + 9 / scale.value, point.y - 9 / scale.value)
        })
      }
    }
  }

  zone.corners.forEach((point, pointIndex) => {
    ctx.beginPath()
    ctx.arc(point.x, point.y, 7 / scale.value, 0, Math.PI * 2)
    ctx.fillStyle = selected ? '#ffc107' : '#2d8fe3'
    ctx.fill()
    ctx.strokeStyle = '#111'
    ctx.lineWidth = 1 / scale.value
    ctx.stroke()

    ctx.fillStyle = '#111'
    ctx.font = `${12 / scale.value}px Arial`
    ctx.fillText(String(pointIndex + 1), point.x + 9 / scale.value, point.y - 9 / scale.value)
  })

  const center = polygonCenter(zone.corners)
  ctx.fillStyle = '#fff'
  ctx.font = `bold ${18 / scale.value}px Arial`
  ctx.strokeStyle = '#111'
  ctx.lineWidth = 3 / scale.value
  ctx.strokeText(`Зона ${index + 1}`, center.x - 35 / scale.value, center.y)
  ctx.fillText(`Зона ${index + 1}`, center.x - 35 / scale.value, center.y)

  ctx.restore()
}

function drawAddingPreview(ctx) {
  ctx.save()

  addPoints.value.forEach((point, index) => {
    ctx.beginPath()
    ctx.arc(point.x, point.y, 8 / scale.value, 0, Math.PI * 2)
    ctx.fillStyle = '#ffc107'
    ctx.fill()

    ctx.fillStyle = '#111'
    ctx.font = `bold ${12 / scale.value}px Arial`
    ctx.fillText(String(index + 1), point.x + 10 / scale.value, point.y)
  })

  if (addPoints.value.length > 1) {
    ctx.beginPath()
    ctx.moveTo(addPoints.value[0].x, addPoints.value[0].y)

    for (let i = 1; i < addPoints.value.length; i += 1) {
      ctx.lineTo(addPoints.value[i].x, addPoints.value[i].y)
    }

    ctx.strokeStyle = '#ffc107'
    ctx.lineWidth = 2 / scale.value
    ctx.setLineDash([8 / scale.value, 6 / scale.value])
    ctx.stroke()
  }

  ctx.restore()
}


function makeSpotKey(zoneId, row, col) {
  return `${zoneId}__${row + 1}__${col + 1}`
}

function clonePolygon(points) {
  return points.map((point) => ({
    x: Number(point.x),
    y: Number(point.y),
  }))
}

function getDefaultSpotPolygonFromGrid(row, col, grid) {
  return [
    grid[row][col],
    grid[row][col + 1],
    grid[row + 1][col + 1],
    grid[row + 1][col],
  ].map((point) => ({
    x: Number(point.x),
    y: Number(point.y),
  }))
}

function getSpotPolygon(zone, row, col, grid = null) {
  const key = makeSpotKey(zone.id, row, col)
  const overridden = spotOverrides.value[key]

  if (Array.isArray(overridden) && overridden.length === 4) {
    return clonePolygon(overridden)
  }

  const sourceGrid = grid || buildZoneGrid(zone)
  return getDefaultSpotPolygonFromGrid(row, col, sourceGrid)
}

function setSpotOverride(key, polygon) {
  spotOverrides.value = {
    ...spotOverrides.value,
    [key]: polygon.map((point) => ({
      x: round(point.x),
      y: round(point.y),
    })),
  }
}

function deleteSpotOverride(key) {
  const next = { ...spotOverrides.value }
  delete next[key]
  spotOverrides.value = next
}

function buildZoneGrid(zone) {
  const rows = Math.max(1, Number(zone.rows) || 1)
  const cols = Math.max(1, Number(zone.cols) || 1)
  const grid = []

  for (let row = 0; row <= rows; row += 1) {
    const line = []

    for (let col = 0; col <= cols; col += 1) {
      line.push(bilerp(zone.corners, col / cols, row / rows))
    }

    grid.push(line)
  }

  return grid
}

function bilerp(corners, u, v) {
  const tl = corners[0]
  const tr = corners[1]
  const br = corners[2]
  const bl = corners[3]

  const top = lerp(tl, tr, u)
  const bottom = lerp(bl, br, u)

  return lerp(top, bottom, v)
}

function lerp(a, b, t) {
  return {
    x: a.x + (b.x - a.x) * t,
    y: a.y + (b.y - a.y) * t,
  }
}

function polygonCenter(points) {
  const sum = points.reduce(
    (acc, point) => {
      acc.x += point.x
      acc.y += point.y
      return acc
    },
    { x: 0, y: 0 }
  )

  return {
    x: sum.x / points.length,
    y: sum.y / points.length,
  }
}

function screenToImage(event) {
  const canvas = canvasRef.value
  const rect = canvas.getBoundingClientRect()

  const x = event.clientX - rect.left
  const y = event.clientY - rect.top

  return {
    x: (x - offsetX.value) / scale.value,
    y: (y - offsetY.value) / scale.value,
  }
}

function onMouseDown(event) {
  if (!imageLoaded.value || event.button !== 0) return

  const point = screenToImage(event)

  if (addMode.value) {
    addPoints.value.push(point)

    if (addPoints.value.length === 4) {
      finishAddingZone()
    }

    render()
    return
  }

  const spotCornerHit = findSpotCornerHit(point)

  if (spotCornerHit) {
    selectedZoneId.value = spotCornerHit.zone.id
    selectedSpotKey.value = spotCornerHit.key
    isDraggingSpotPoint.value = true
    draggingSpot.value = {
      key: spotCornerHit.key,
      pointIndex: spotCornerHit.pointIndex,
    }

    render()
    return
  }

  const hit = findCornerHit(point)

  if (hit) {
    selectedZoneId.value = hit.zone.id
    selectedSpotKey.value = null
    isDraggingPoint.value = true
    dragging.value = {
      zoneId: hit.zone.id,
      pointIndex: hit.pointIndex,
    }

    render()
    return
  }

  const spotHit = findSpotHit(point)

  if (spotHit) {
    selectedZoneId.value = spotHit.zone.id
    selectedSpotKey.value = spotHit.key
    render()
    return
  }

  const zone = findZoneHit(point)

  if (zone) {
    selectedZoneId.value = zone.id
    selectedSpotKey.value = null
    render()
    return
  }

  if (selectedZoneId.value || selectedSpotKey.value) {
    selectedZoneId.value = null
    selectedSpotKey.value = null
    render()
  }

  isPanning.value = true
  lastMouse.value = {
    x: event.clientX,
    y: event.clientY,
  }
}

function onMouseMove(event) {
  if (!imageLoaded.value) return

  if (isDraggingSpotPoint.value) {
    const point = screenToImage(event)
    const hit = findSpotByKey(draggingSpot.value.key)

    if (hit && draggingSpot.value.pointIndex >= 0) {
      const grid = buildZoneGrid(hit.zone)
      const polygon = getSpotPolygon(hit.zone, hit.row, hit.col, grid)
      polygon[draggingSpot.value.pointIndex] = point
      setSpotOverride(hit.key, polygon)
      render()
    }

    return
  }

  if (isDraggingPoint.value) {
    const point = screenToImage(event)
    const zone = zones.value.find((item) => item.id === dragging.value.zoneId)

    if (zone && dragging.value.pointIndex >= 0) {
      zone.corners[dragging.value.pointIndex] = point
      render()
    }

    return
  }

  if (isPanning.value) {
    const dx = event.clientX - lastMouse.value.x
    const dy = event.clientY - lastMouse.value.y

    offsetX.value += dx
    offsetY.value += dy

    lastMouse.value = {
      x: event.clientX,
      y: event.clientY,
    }

    render()
  }
}

function onMouseUp() {
  isPanning.value = false
  isDraggingPoint.value = false
  isDraggingSpotPoint.value = false
  dragging.value = {
    zoneId: null,
    pointIndex: -1,
  }
  draggingSpot.value = {
    key: null,
    pointIndex: -1,
  }
}

function findSpotByKey(key) {
  if (!key) return null

  for (const zone of zones.value) {
    const rows = Math.max(1, Number(zone.rows) || 1)
    const cols = Math.max(1, Number(zone.cols) || 1)

    for (let row = 0; row < rows; row += 1) {
      for (let col = 0; col < cols; col += 1) {
        const spotKey = makeSpotKey(zone.id, row, col)

        if (spotKey === key) {
          return {
            key: spotKey,
            zone,
            row,
            col,
          }
        }
      }
    }
  }

  return null
}

function findSpotCornerHit(point) {
  const radius = 12 / scale.value

  for (const zone of [...zones.value].reverse()) {
    const grid = buildZoneGrid(zone)
    const rows = Math.max(1, Number(zone.rows) || 1)
    const cols = Math.max(1, Number(zone.cols) || 1)

    for (let row = rows - 1; row >= 0; row -= 1) {
      for (let col = cols - 1; col >= 0; col -= 1) {
        const key = makeSpotKey(zone.id, row, col)
        const polygon = getSpotPolygon(zone, row, col, grid)

        for (let pointIndex = 0; pointIndex < polygon.length; pointIndex += 1) {
          const corner = polygon[pointIndex]
          const dx = point.x - corner.x
          const dy = point.y - corner.y

          if (Math.sqrt(dx * dx + dy * dy) <= radius) {
            return {
              key,
              zone,
              row,
              col,
              pointIndex,
            }
          }
        }
      }
    }
  }

  return null
}

function findSpotHit(point) {
  for (const zone of [...zones.value].reverse()) {
    const grid = buildZoneGrid(zone)
    const rows = Math.max(1, Number(zone.rows) || 1)
    const cols = Math.max(1, Number(zone.cols) || 1)

    for (let row = rows - 1; row >= 0; row -= 1) {
      for (let col = cols - 1; col >= 0; col -= 1) {
        const key = makeSpotKey(zone.id, row, col)
        const polygon = getSpotPolygon(zone, row, col, grid)

        if (pointInPolygon(point, polygon)) {
          return {
            key,
            zone,
            row,
            col,
          }
        }
      }
    }
  }

  return null
}

function findCornerHit(point) {
  const radius = 12 / scale.value

  for (const zone of [...zones.value].reverse()) {
    for (let i = 0; i < zone.corners.length; i += 1) {
      const corner = zone.corners[i]
      const dx = point.x - corner.x
      const dy = point.y - corner.y

      if (Math.sqrt(dx * dx + dy * dy) <= radius) {
        return {
          zone,
          pointIndex: i,
        }
      }
    }
  }

  return null
}

function findZoneHit(point) {
  for (const zone of [...zones.value].reverse()) {
    if (pointInPolygon(point, zone.corners)) {
      return zone
    }
  }

  return null
}

function pointInPolygon(point, polygon) {
  let inside = false

  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i, i += 1) {
    const xi = polygon[i].x
    const yi = polygon[i].y
    const xj = polygon[j].x
    const yj = polygon[j].y

    const intersect = ((yi > point.y) !== (yj > point.y)) &&
      (point.x < ((xj - xi) * (point.y - yi)) / ((yj - yi) || 1e-9) + xi)

    if (intersect) {
      inside = !inside
    }
  }

  return inside
}

function onWheel(event) {
  if (!imageLoaded.value) return

  const oldScale = scale.value
  const direction = event.deltaY < 0 ? 1 : -1
  const newScale = clamp(scale.value + direction * 0.12, 0.2, 6)

  if (newScale === oldScale) return

  const canvas = canvasRef.value
  const rect = canvas.getBoundingClientRect()

  const mouseX = event.clientX - rect.left
  const mouseY = event.clientY - rect.top

  const imageX = (mouseX - offsetX.value) / oldScale
  const imageY = (mouseY - offsetY.value) / oldScale

  scale.value = newScale
  offsetX.value = mouseX - imageX * newScale
  offsetY.value = mouseY - imageY * newScale

  render()
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function toggleAddMode() {
  addMode.value = !addMode.value
  addPoints.value = []
  selectedZoneId.value = null
  render()
}

function finishAddingZone() {
  const zone = {
    id: `zone_${Date.now()}`,
    corners: addPoints.value.slice(),
    cols: 1,
    rows: 1,
  }

  zones.value.push(zone)
  selectedZoneId.value = zone.id
  selectedSpotKey.value = null
  addMode.value = false
  addPoints.value = []

  render()
}

function selectZone(zoneId) {
  selectedZoneId.value = zoneId
  selectedSpotKey.value = null
  addMode.value = false
  addPoints.value = []
  render()
}

function deleteSelectedZone() {
  if (!selectedZone.value) return

  const zoneId = selectedZone.value.id
  zones.value = zones.value.filter((zone) => zone.id !== zoneId)

  const nextOverrides = { ...spotOverrides.value }
  Object.keys(nextOverrides).forEach((key) => {
    if (key.startsWith(`${zoneId}__`)) {
      delete nextOverrides[key]
    }
  })
  spotOverrides.value = nextOverrides

  selectedZoneId.value = null
  selectedSpotKey.value = null
  render()
}

function resetSelectedSpotPolygon() {
  if (!selectedSpotKey.value) return

  deleteSpotOverride(selectedSpotKey.value)
  render()
}

function resetView() {
  fitImageToCanvas()
}

function buildLayoutPayload() {
  const spots = []
  let spotNumber = 1

  const layoutZones = zones.value.map((zone, zoneIndex) => {
    const normalizedZone = {
      id: zone.id,
      name: `Зона ${zoneIndex + 1}`,
      zone: zoneIndex + 1,
      cols: Math.max(1, Number(zone.cols) || 1),
      rows: Math.max(1, Number(zone.rows) || 1),
      corners: zone.corners.map((point) => ({
        x: round(point.x),
        y: round(point.y),
      })),
    }

    const grid = buildZoneGrid(normalizedZone)

    for (let row = 0; row < normalizedZone.rows; row += 1) {
      for (let col = 0; col < normalizedZone.cols; col += 1) {
        const polygon = getSpotPolygon(normalizedZone, row, col, grid).map((point) => ({
          x: round(point.x),
          y: round(point.y),
        }))

        const label = String(spotNumber).padStart(3, '0')

        spots.push({
          id: `spot_${label}`,
          label,
          number: label,
          zone: zoneIndex + 1,
          zone_id: normalizedZone.id,
          row: row + 1,
          col: col + 1,
          enabled: true,
          polygon,
        })

        spotNumber += 1
      }
    }

    return normalizedZone
  })

  return {
    version: 1,
    parking: {
      id: parkingId,
      name: parkingName.value || parking.value?.name || parkingId,
      db_id: parking.value?.db_id,
      company_id: parking.value?.company_id,
    },
    camera: {
      source_type: getCurrentCamera()?.source_type || null,
      source_url: getCurrentCamera()?.source_url || null,
      test_video_path: getCurrentCamera()?.test_video_path || null,
    },
    frame_meta: {
      width: getFrameWidth(),
      height: getFrameHeight(),
    },
    zones: layoutZones,
    spots,
  }
}

function round(value) {
  return Math.round(Number(value) * 100) / 100
}

async function saveLayout() {
  saving.value = true
  error.value = ''
  message.value = ''

  try {
    const layout = buildLayoutPayload()
    await parkingService.saveLayout(parkingId, layout)

    showMessage(`Layout сохранён. Мест: ${layout.spots.length}`)
  } catch (err) {
    console.error('Ошибка сохранения layout:', err)
    showError('Не удалось сохранить layout')
  } finally {
    saving.value = false
  }
}

function goSetup() {
  router.push(`/admin/parkings/${parkingId}/setup`)
}

function goMapEditor() {
  router.push(`/admin/parkings/${parkingId}/map-editor`)
}

watch(
  zones,
  () => {
    render()
  },
  { deep: true }
)

onMounted(async () => {
  window.addEventListener('resize', resizeCanvas)
  await loadEditor()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCanvas)

  if (imageObjectUrl.value) {
    URL.revokeObjectURL(imageObjectUrl.value)
  }
})
</script>

<!-- <style scoped>
.editor-page {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  background: #111827;
  overflow: hidden;
}

.sidebar {
  width: 310px;
  min-width: 310px;
  height: 100%;
  overflow-y: auto;
  padding: 16px;
  background: #0f172a;
  color: #e5e7eb;
  border-right: 1px solid #1e293b;
}

.sidebar h2 {
  margin: 0 0 18px;
  color: #38bdf8;
  font-size: 18px;
}

.block {
  margin-bottom: 12px;
}

.block label,
.edit-zone label {
  display: block;
  margin-bottom: 6px;
  color: #94a3b8;
  font-size: 12px;
  text-transform: uppercase;
}

input {
  width: 100%;
  height: 36px;
  box-sizing: border-box;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 0 10px;
  background: #020617;
  color: #e5e7eb;
}

input:disabled {
  opacity: 0.7;
}

hr {
  border: none;
  border-top: 1px solid #1e293b;
  margin: 16px 0;
}

.btn {
  width: 100%;
  min-height: 38px;
  border: 1px solid #38bdf8;
  border-radius: 8px;
  background: transparent;
  color: #38bdf8;
  cursor: pointer;
  font-weight: 700;
  margin-bottom: 8px;
}

.btn:hover,
.btn.active {
  background: #38bdf8;
  color: #020617;
}

.btn.success {
  border-color: #22c55e;
  color: #22c55e;
}

.btn.success:hover {
  background: #22c55e;
  color: #020617;
}

.btn.danger {
  border-color: #ef4444;
  color: #ef4444;
}

.btn.danger:hover {
  background: #ef4444;
  color: white;
}

.btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.hint {
  padding: 10px;
  border-radius: 8px;
  background: rgba(56, 189, 248, 0.08);
  color: #bae6fd;
  font-size: 12px;
  line-height: 1.5;
}

.section-title {
  margin-bottom: 8px;
  color: #38bdf8;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.zones-list {
  display: grid;
  gap: 6px;
  max-height: 190px;
  overflow-y: auto;
}

.zone-item {
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 9px;
  background: #020617;
  color: #e5e7eb;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
}

.zone-item.selected {
  border-color: #ffc107;
  color: #ffc107;
}

.edit-zone {
  margin-top: 14px;
  padding: 12px;
  border: 1px solid #ffc107;
  border-radius: 10px;
  background: rgba(255, 193, 7, 0.08);
}

.edit-zone input {
  margin-bottom: 10px;
}

.selected-spot-title {
  margin-bottom: 10px;
  color: #0f172a;
  font-weight: 800;
  font-size: 14px;
}

.stats {
  display: grid;
  gap: 8px;
}

.stats div {
  display: flex;
  justify-content: space-between;
  color: #94a3b8;
}

.stats b {
  color: #e5e7eb;
}

.message {
  margin-top: 10px;
  padding: 10px;
  border-radius: 8px;
  font-size: 13px;
}

.success-message {
  background: rgba(34, 197, 94, 0.15);
  color: #bbf7d0;
}

.error-message {
  background: rgba(239, 68, 68, 0.15);
  color: #fecaca;
}

.canvas-wrap {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: #020617;
}

canvas {
  width: 100%;
  height: 100%;
  display: block;
  cursor: crosshair;
}

.empty {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 40px;
  color: #64748b;
  text-align: center;
  pointer-events: none;
}

.top-bar {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(15, 23, 42, 0.9);
  color: #38bdf8;
  border: 1px solid #1e293b;
  border-radius: 10px;
  padding: 8px 16px;
  pointer-events: none;
  font-size: 13px;
}
</style> -->

<style scoped>
.editor-page {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  background: #eef6ff;
  overflow: hidden;
}

.sidebar {
  width: 310px;
  min-width: 310px;
  height: 100%;
  overflow-y: auto;
  padding: 16px;
  background: #f8fbff;
  color: #1f2937;
  border-right: 1px solid #dbeafe;
  box-shadow: 8px 0 24px rgba(15, 23, 42, 0.08);
}

.sidebar h2 {
  margin: 0 0 18px;
  color: #2d8fe3;
  font-size: 18px;
}

.block {
  margin-bottom: 12px;
}

.block label,
.edit-zone label {
  display: block;
  margin-bottom: 6px;
  color: #64748b;
  font-size: 12px;
  text-transform: uppercase;
}

input {
  width: 100%;
  height: 36px;
  box-sizing: border-box;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 0 10px;
  background: #ffffff;
  color: #0f172a;
}

input:disabled {
  background: #eef2f7;
  color: #64748b;
}

hr {
  border: none;
  border-top: 1px solid #dbeafe;
  margin: 16px 0;
}

.btn {
  width: 100%;
  min-height: 38px;
  border: 1px solid #2d8fe3;
  border-radius: 8px;
  background: #ffffff;
  color: #2d8fe3;
  cursor: pointer;
  font-weight: 700;
  margin-bottom: 8px;
}

.btn:hover,
.btn.active {
  background: #2d8fe3;
  color: #ffffff;
}

.btn.success {
  border-color: #16a34a;
  color: #16a34a;
}

.btn.success:hover {
  background: #16a34a;
  color: #ffffff;
}

.btn.danger {
  border-color: #ef4444;
  color: #ef4444;
}

.btn.danger:hover {
  background: #ef4444;
  color: #ffffff;
}

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.hint {
  padding: 10px;
  border-radius: 8px;
  background: #e0f2fe;
  color: #075985;
  font-size: 12px;
  line-height: 1.5;
}

.section-title {
  margin-bottom: 8px;
  color: #2d8fe3;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.zones-list {
  display: grid;
  gap: 6px;
  max-height: 190px;
  overflow-y: auto;
}

.zone-item {
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 9px;
  background: #ffffff;
  color: #1f2937;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
}

.zone-item.selected {
  border-color: #f59e0b;
  background: #fffbeb;
  color: #92400e;
}

.edit-zone {
  margin-top: 14px;
  padding: 12px;
  border: 1px solid #f59e0b;
  border-radius: 10px;
  background: #fffbeb;
}

.edit-zone input {
  margin-bottom: 10px;
}

.selected-spot-title {
  margin-bottom: 10px;
  color: #0f172a;
  font-weight: 800;
  font-size: 14px;
}

.stats {
  display: grid;
  gap: 8px;
}

.stats div {
  display: flex;
  justify-content: space-between;
  color: #64748b;
}

.stats b {
  color: #0f172a;
}

.message {
  margin-top: 10px;
  padding: 10px;
  border-radius: 8px;
  font-size: 13px;
}

.success-message {
  background: #dcfce7;
  color: #166534;
}

.error-message {
  background: #fee2e2;
  color: #991b1b;
}

.canvas-wrap {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: #eaf3ff;
}

canvas {
  width: 100%;
  height: 100%;
  display: block;
  cursor: crosshair;
}

.empty {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 40px;
  color: #64748b;
  text-align: center;
  pointer-events: none;
}

.top-bar {
  position: absolute;
  top: 16px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(255, 255, 255, 0.94);
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  padding: 8px 16px;
  pointer-events: none;
  font-size: 13px;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
}
</style>