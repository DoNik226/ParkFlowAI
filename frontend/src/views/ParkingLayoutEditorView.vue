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

      <div v-if="backgroundType === 'video'" class="video-controls">
        <div class="section-title">Фон разметки</div>

        <button class="btn" type="button" @click="toggleVideoPlayback">
          {{ backgroundPlaying ? 'Пауза видео' : 'Пуск видео' }}
        </button>

        <button class="btn" type="button" @click="seekVideoToStart">
          В начало видео
        </button>

        <div class="hint">
          Размечай места на паузе. Координаты будут сохранены по реальному размеру видео.
        </div>
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
        Фон для разметки не найден. Загрузите тестовое видео или получите/загрузите скриншот на странице настройки парковки.
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

const backgroundType = ref('snapshot')
const backgroundPlaying = ref(false)
const videoElement = ref(null)

let renderFrameHandle = null

const zones = ref([])
const selectedZoneId = ref(null)

const addMode = ref(false)
const addPoints = ref([])

// const newZoneCols = ref(5)
// const newZoneRows = ref(1)

const scale = ref(1)
const offsetX = ref(0)
const offsetY = ref(0)

const isPanning = ref(false)
const isDraggingPoint = ref(false)
const dragging = ref({
  zoneId: null,
  pointIndex: -1,
})

const lastMouse = ref({
  x: 0,
  y: 0,
})

const selectedZone = computed(() => {
  return zones.value.find((zone) => zone.id === selectedZoneId.value) || null
})

const spotsCount = computed(() => {
  return zones.value.reduce((sum, zone) => {
    return sum + Number(zone.cols || 0) * Number(zone.rows || 0)
  }, 0)
})

const modeText = computed(() => {
  if (!imageLoaded.value) return 'Фон разметки не загружен'
  if (addMode.value) return `Добавление зоны: точка ${addPoints.value.length + 1} из 4`
  if (selectedZone.value) return 'Выбрана зона. Можно двигать углы. Клик по пустому месту снимает выделение.'
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
    await loadBackgroundMedia()

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

    if (Array.isArray(layout.zones)) {
      zones.value = layout.zones.map((zone, index) => ({
        id: zone.id || `zone_${index + 1}`,
        corners: normalizeCorners(zone.corners || zone.polygon || []),
        cols: Number(zone.cols || 1),
        rows: Number(zone.rows || 1),
      }))
    }
  } catch {
    zones.value = []
  }
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

  if (backgroundType.value === 'video') {
    return Number(image.value.videoWidth || 0)
  }

  return Number(image.value.naturalWidth || 0)
}

function getFrameHeight() {
  if (!image.value) return 0

  if (backgroundType.value === 'video') {
    return Number(image.value.videoHeight || 0)
  }

  return Number(image.value.naturalHeight || 0)
}

async function loadBackgroundMedia() {
  const camera = getCurrentCamera()
  const sourceType = String(camera?.source_type || '').toLowerCase()
  const hasVideo = Boolean(camera?.test_video_path || parking.value?.test_video_path)

  if (sourceType === 'video' && hasVideo) {
    try {
      await loadVideoBackground()
      return
    } catch (err) {
      console.warn('Не удалось загрузить видео как фон разметки, пробую snapshot:', err)
    }
  }

  await loadSnapshotImage()
}

async function loadVideoBackground() {
  stopVideoRenderLoop()

  const video = document.createElement('video')
  video.src = parkingService.getSourceVideoUrl(parkingId)
  video.muted = true
  video.loop = true
  video.playsInline = true
  video.preload = 'auto'

  await new Promise((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      reject(new Error('Video loading timeout'))
    }, 12000)

    video.onloadedmetadata = () => {
      window.clearTimeout(timeout)

      if (!video.videoWidth || !video.videoHeight) {
        reject(new Error('Video metadata is empty'))
        return
      }

      resolve()
    }

    video.onerror = () => {
      window.clearTimeout(timeout)
      reject(new Error('Cannot load video'))
    }

    video.load()
  })

  try {
    video.currentTime = 0.001
    await new Promise((resolve) => {
      video.onseeked = resolve
      window.setTimeout(resolve, 400)
    })
  } catch {
    // Если браузер не дал сделать seek до первого кадра, всё равно используем video.
  }

  image.value = video
  videoElement.value = video
  backgroundType.value = 'video'
  backgroundPlaying.value = false
  imageLoaded.value = true

  render()
}

function startVideoRenderLoop() {
  stopVideoRenderLoop()

  const loop = () => {
    render()
    renderFrameHandle = window.requestAnimationFrame(loop)
  }

  renderFrameHandle = window.requestAnimationFrame(loop)
}

function stopVideoRenderLoop() {
  if (renderFrameHandle) {
    window.cancelAnimationFrame(renderFrameHandle)
    renderFrameHandle = null
  }
}

async function toggleVideoPlayback() {
  if (backgroundType.value !== 'video' || !videoElement.value) return

  if (backgroundPlaying.value) {
    videoElement.value.pause()
    backgroundPlaying.value = false
    stopVideoRenderLoop()
    render()
    return
  }

  try {
    await videoElement.value.play()
    backgroundPlaying.value = true
    startVideoRenderLoop()
  } catch (err) {
    console.warn('Не удалось запустить видео в редакторе:', err)
    showError('Не удалось запустить видео в редакторе')
  }
}

function seekVideoToStart() {
  if (backgroundType.value !== 'video' || !videoElement.value) return

  videoElement.value.pause()
  backgroundPlaying.value = false
  stopVideoRenderLoop()
  videoElement.value.currentTime = 0
  render()
}

async function loadSnapshotImage() {
  try {
    stopVideoRenderLoop()
    backgroundPlaying.value = false
    backgroundType.value = 'snapshot'
    videoElement.value = null

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
  if (!canvas || !image.value) return

  const padding = 40

  const availableWidth = Math.max(100, canvas.width - padding * 2)
  const availableHeight = Math.max(100, canvas.height - padding * 2)

  const imageWidth = getFrameWidth()
  const imageHeight = getFrameHeight()

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

  ctx.save()

  for (let row = 0; row < zone.rows; row++) {
    for (let col = 0; col < zone.cols; col++) {
      const tl = grid[row][col]
      const tr = grid[row][col + 1]
      const br = grid[row + 1][col + 1]
      const bl = grid[row + 1][col]

      ctx.beginPath()
      ctx.moveTo(tl.x, tl.y)
      ctx.lineTo(tr.x, tr.y)
      ctx.lineTo(br.x, br.y)
      ctx.lineTo(bl.x, bl.y)
      ctx.closePath()

      ctx.fillStyle = selected
        ? 'rgba(255, 193, 7, 0.15)'
        : 'rgba(33, 150, 243, 0.12)'

      ctx.fill()
    }
  }

  ctx.strokeStyle = selected ? '#ffc107' : '#2d8fe3'
  ctx.lineWidth = selected ? 3 / scale.value : 2 / scale.value

  for (let col = 0; col <= zone.cols; col++) {
    ctx.beginPath()
    ctx.moveTo(grid[0][col].x, grid[0][col].y)

    for (let row = 1; row <= zone.rows; row++) {
      ctx.lineTo(grid[row][col].x, grid[row][col].y)
    }

    ctx.stroke()
  }

  for (let row = 0; row <= zone.rows; row++) {
    ctx.beginPath()
    ctx.moveTo(grid[row][0].x, grid[row][0].y)

    for (let col = 1; col <= zone.cols; col++) {
      ctx.lineTo(grid[row][col].x, grid[row][col].y)
    }

    ctx.stroke()
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

  const hit = findCornerHit(point)

  if (hit) {
    selectedZoneId.value = hit.zone.id
    isDraggingPoint.value = true
    dragging.value = {
      zoneId: hit.zone.id,
      pointIndex: hit.pointIndex,
    }

    render()
    return
  }

  const zone = findZoneHit(point)

  if (zone) {
    selectedZoneId.value = zone.id
    render()
    return
  }

  // Клик по пустому месту снимает выделение зоны
  if (selectedZoneId.value) {
    selectedZoneId.value = null
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
  dragging.value = {
    zoneId: null,
    pointIndex: -1,
  }
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

  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i].x
    const yi = polygon[i].y
    const xj = polygon[j].x
    const yj = polygon[j].y

    const intersect =
      yi > point.y !== yj > point.y &&
      point.x < ((xj - xi) * (point.y - yi)) / (yj - yi) + xi

    if (intersect) inside = !inside
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
  addMode.value = false
  addPoints.value = []

  render()
}

function selectZone(zoneId) {
  selectedZoneId.value = zoneId
  addMode.value = false
  addPoints.value = []
  render()
}

function deleteSelectedZone() {
  if (!selectedZone.value) return

  zones.value = zones.value.filter((zone) => zone.id !== selectedZone.value.id)
  selectedZoneId.value = null
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
        const polygon = [
          grid[row][col],
          grid[row][col + 1],
          grid[row + 1][col + 1],
          grid[row + 1][col],
        ].map((point) => ({
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
  stopVideoRenderLoop()

  if (videoElement.value) {
    videoElement.value.pause()
  }

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

.video-controls {
  display: grid;
  gap: 8px;
}

.video-controls .hint {
  margin-bottom: 8px;
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

.video-controls {
  display: grid;
  gap: 8px;
}

.video-controls .hint {
  margin-bottom: 8px;
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