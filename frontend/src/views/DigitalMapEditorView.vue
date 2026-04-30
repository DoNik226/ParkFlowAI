<template>
  <section class="editor-page">
    <aside class="sidebar">
      <h2>Конструктор цифровой карты</h2>

      <div class="block">
        <label>Парковка</label>
        <input :value="parkingId" disabled>
      </div>

      <div class="block">
        <label>Название</label>
        <input v-model="parkingName">
      </div>

      <hr>

      <div class="section-title">Режим</div>

      <button
        class="btn"
        :class="{ active: mode === 'select' }"
        @click="setMode('select')"
      >
        Выбор / перемещение
      </button>

      <button
        class="btn"
        :class="{ active: mode === 'road' }"
        @click="setMode('road')"
      >
        + Точка дороги
      </button>

      <button
        class="btn"
        :class="{ active: mode === 'entrance' }"
        @click="setMode('entrance')"
      >
        + Въезд
      </button>

      <button
        class="btn"
        :class="{ active: mode === 'edge' }"
        @click="setMode('edge')"
      >
        Соединить точки
      </button>

      <button class="btn" @click="createSpotAccessVertices">
        Создать точки мест
      </button>

      <hr>

      <div class="stats">
        <div>
          <span>Мест из layout</span>
          <b>{{ spots.length }}</b>
        </div>

        <div>
          <span>Точек графа</span>
          <b>{{ vertices.length }}</b>
        </div>

        <div>
          <span>Рёбер</span>
          <b>{{ edges.length }}</b>
        </div>

        <div>
          <span>Въездов</span>
          <b>{{ entrances.length }}</b>
        </div>
      </div>

      <hr>

      <div v-if="selectedVertex" class="selected-box">
        <div class="section-title">Выбранная точка</div>

        <label>ID</label>
        <input :value="selectedVertex.id" disabled>

        <label>Тип</label>
        <input :value="selectedVertex.type" disabled>

        <label v-if="selectedVertex.type === 'entrance'">Название въезда</label>
        <input
          v-if="selectedVertex.type === 'entrance'"
          v-model="selectedVertex.name"
        >

        <button class="btn danger" @click="deleteSelectedVertex">
          Удалить точку
        </button>
      </div>

      <div v-if="selectedEdge" class="selected-box">
        <div class="section-title">Выбранное ребро</div>

        <label>Длина, м</label>
        <input v-model.number="selectedEdge.length_meters" type="number" min="0.1" step="0.1">

        <label class="checkbox-row">
          <input v-model="selectedEdge.is_bidirectional" type="checkbox">
          <span>Двустороннее движение</span>
        </label>

        <button class="btn danger" @click="deleteSelectedEdge">
          Удалить ребро
        </button>
      </div>

      <hr>

      <button class="btn success" :disabled="saving || !imageLoaded" @click="saveMap">
        {{ saving ? 'Сохранение...' : 'Сохранить map.json' }}
      </button>

      <button class="btn" @click="resetView">
        Сбросить вид
      </button>

      <button class="btn" @click="goSetup">
        Назад к настройке
      </button>

      <button class="btn" @click="goUserMap">
        Открыть карту пользователя
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

      <div v-if="loading" class="empty">
        Загрузка конструктора...
      </div>

      <div v-else-if="!imageLoaded" class="empty">
        Скриншот не найден. Сначала загрузите или получите скриншот на странице настройки парковки.
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

const layout = ref(null)
const spots = ref([])

const vertices = ref([])
const edges = ref([])
const entrances = ref([])

const mode = ref('select')

const selectedVertexId = ref(null)
const selectedEdgeId = ref(null)

const edgeStartVertexId = ref(null)

const scale = ref(1)
const offsetX = ref(0)
const offsetY = ref(0)

const isPanning = ref(false)
const isDraggingVertex = ref(false)

const draggingVertexId = ref(null)

const lastMouse = ref({
  x: 0,
  y: 0,
})

const selectedVertex = computed(() => {
  return vertices.value.find((vertex) => vertex.id === selectedVertexId.value) || null
})

const selectedEdge = computed(() => {
  return edges.value.find((edge) => edge.id === selectedEdgeId.value) || null
})

const modeText = computed(() => {
  if (!imageLoaded.value) return 'Скриншот не загружен'

  if (mode.value === 'road') {
    return 'Клик по изображению добавит точку дороги'
  }

  if (mode.value === 'entrance') {
    return 'Клик по изображению добавит въезд'
  }

  if (mode.value === 'edge') {
    if (edgeStartVertexId.value) {
      return 'Выберите вторую точку для соединения'
    }

    return 'Выберите первую точку для соединения'
  }

  return 'Выбор / перемещение. Колесо — масштаб, ЛКМ по пустому месту — перемещение.'
})

async function loadEditor() {
  loading.value = true
  error.value = ''

  try {
    parking.value = await parkingService.getParking(parkingId)
    parkingName.value = parking.value.name

    await loadLayout()
    await loadMap()
    await loadSnapshotImage()

    await nextTick()
    resizeCanvas()
    fitImageToCanvas()
    render()
  } catch (err) {
    console.error('Ошибка загрузки конструктора карты:', err)
    showError('Не удалось загрузить конструктор цифровой карты')
  } finally {
    loading.value = false
  }
}

async function loadLayout() {
  layout.value = await parkingService.getLayout(parkingId)
  spots.value = Array.isArray(layout.value?.spots) ? layout.value.spots : []
}

async function loadMap() {
  try {
    const mapData = await parkingService.getMap(parkingId)

    vertices.value = Array.isArray(mapData.vertices)
      ? mapData.vertices.map(normalizeVertex)
      : []

    edges.value = Array.isArray(mapData.edges)
      ? mapData.edges.map(normalizeEdge)
      : []

    entrances.value = Array.isArray(mapData.entrances)
      ? mapData.entrances
      : []
  } catch {
    vertices.value = []
    edges.value = []
    entrances.value = []
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

function normalizeVertex(vertex) {
  return {
    id: vertex.id,
    type: vertex.type || 'road',
    x: Number(vertex.x),
    y: Number(vertex.y),
    name: vertex.name || '',
    spot_id: vertex.spot_id || null,
  }
}

function normalizeEdge(edge) {
  return {
    id: edge.id,
    source: edge.source,
    destination: edge.destination,
    length_meters: Number(edge.length_meters || 1),
    is_bidirectional: edge.is_bidirectional !== false,
  }
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

  const fitScale = Math.min(
    availableWidth / img.naturalWidth,
    availableHeight / img.naturalHeight
  )

  scale.value = clamp(fitScale, 0.05, 6)
  offsetX.value = (canvas.width - img.naturalWidth * scale.value) / 2
  offsetY.value = (canvas.height - img.naturalHeight * scale.value) / 2

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

  ctx.drawImage(image.value, 0, 0, image.value.naturalWidth, image.value.naturalHeight)

  drawSpots(ctx)
  drawEdges(ctx)
  drawVertices(ctx)

  ctx.restore()
}

function drawSpots(ctx) {
  spots.value.forEach((spot) => {
    const polygon = spot.polygon || []

    if (polygon.length < 3) return

    ctx.beginPath()
    ctx.moveTo(polygon[0].x, polygon[0].y)

    for (let i = 1; i < polygon.length; i += 1) {
      ctx.lineTo(polygon[i].x, polygon[i].y)
    }

    ctx.closePath()

    ctx.fillStyle = 'rgba(45, 143, 227, 0.08)'
    ctx.strokeStyle = '#2d8fe3'
    ctx.lineWidth = 1.5 / scale.value
    ctx.fill()
    ctx.stroke()

    const center = polygonCenter(polygon)

    ctx.fillStyle = '#ffffff'
    ctx.strokeStyle = '#111827'
    ctx.lineWidth = 3 / scale.value
    ctx.font = `bold ${16 / scale.value}px Arial`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'

    const text = spot.label || spot.number || spot.id
    ctx.strokeText(text, center.x, center.y)
    ctx.fillText(text, center.x, center.y)
  })
}

function drawEdges(ctx) {
  edges.value.forEach((edge) => {
    const source = vertices.value.find((vertex) => vertex.id === edge.source)
    const destination = vertices.value.find((vertex) => vertex.id === edge.destination)

    if (!source || !destination) return

    const selected = selectedEdgeId.value === edge.id

    ctx.beginPath()
    ctx.moveTo(source.x, source.y)
    ctx.lineTo(destination.x, destination.y)

    ctx.strokeStyle = selected ? '#f59e0b' : '#0f172a'
    ctx.lineWidth = selected ? 4 / scale.value : 2.5 / scale.value
    ctx.stroke()

    const mid = {
      x: (source.x + destination.x) / 2,
      y: (source.y + destination.y) / 2,
    }

    ctx.fillStyle = selected ? '#f59e0b' : '#0f172a'
    ctx.font = `${13 / scale.value}px Arial`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'bottom'
    ctx.fillText(`${round(edge.length_meters)} м`, mid.x, mid.y - 4 / scale.value)
  })
}

function drawVertices(ctx) {
  vertices.value.forEach((vertex) => {
    const selected = selectedVertexId.value === vertex.id
    const radius = getVertexRadius(vertex)

    ctx.beginPath()
    ctx.arc(vertex.x, vertex.y, radius / scale.value, 0, Math.PI * 2)

    ctx.fillStyle = getVertexColor(vertex, selected)
    ctx.fill()

    ctx.strokeStyle = selected ? '#f59e0b' : '#ffffff'
    ctx.lineWidth = selected ? 4 / scale.value : 2 / scale.value
    ctx.stroke()

    ctx.fillStyle = '#111827'
    ctx.font = `bold ${12 / scale.value}px Arial`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'top'

    const label = getVertexLabel(vertex)
    ctx.fillText(label, vertex.x, vertex.y + (radius + 4) / scale.value)
  })
}

function getVertexRadius(vertex) {
  if (vertex.type === 'entrance') return 12
  if (vertex.type === 'spot_access') return 7
  return 9
}

function getVertexColor(vertex, selected) {
  if (selected) return '#fbbf24'
  if (vertex.type === 'entrance') return '#22c55e'
  if (vertex.type === 'spot_access') return '#8b5cf6'
  return '#ef4444'
}

function getVertexLabel(vertex) {
  if (vertex.type === 'entrance') return vertex.name || 'Въезд'
  if (vertex.type === 'spot_access') return vertex.spot_id || 'Место'
  return vertex.id
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

  if (mode.value === 'road') {
    addVertex(point, 'road')
    return
  }

  if (mode.value === 'entrance') {
    addVertex(point, 'entrance')
    return
  }

  if (mode.value === 'edge') {
    handleEdgeClick(point)
    return
  }

  const vertex = findVertexHit(point)
  if (vertex) {
    selectedVertexId.value = vertex.id
    selectedEdgeId.value = null

    isDraggingVertex.value = true
    draggingVertexId.value = vertex.id

    render()
    return
  }

  const edge = findEdgeHit(point)
  if (edge) {
    selectedEdgeId.value = edge.id
    selectedVertexId.value = null
    render()
    return
  }

  selectedVertexId.value = null
  selectedEdgeId.value = null

  isPanning.value = true
  lastMouse.value = {
    x: event.clientX,
    y: event.clientY,
  }

  render()
}

function onMouseMove(event) {
  if (!imageLoaded.value) return

  if (isDraggingVertex.value && draggingVertexId.value) {
    const point = screenToImage(event)
    const vertex = vertices.value.find((item) => item.id === draggingVertexId.value)

    if (vertex) {
      vertex.x = point.x
      vertex.y = point.y
      recalculateConnectedEdges(vertex.id)
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
  isDraggingVertex.value = false
  draggingVertexId.value = null
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

function addVertex(point, type) {
  const index = vertices.value.length + 1

  const vertex = {
    id: `${type}_${Date.now()}_${index}`,
    type,
    x: round(point.x),
    y: round(point.y),
    name: type === 'entrance' ? `Въезд ${entrances.value.length + 1}` : '',
    spot_id: null,
  }

  vertices.value.push(vertex)

  if (type === 'entrance') {
    entrances.value.push({
      id: vertex.id,
      name: vertex.name,
      vertex_id: vertex.id,
      x: vertex.x,
      y: vertex.y,
      parking_id: parkingId,
    })
  }

  selectedVertexId.value = vertex.id
  selectedEdgeId.value = null

  render()
}

function handleEdgeClick(point) {
  const vertex = findVertexHit(point)

  if (!vertex) {
    edgeStartVertexId.value = null
    selectedVertexId.value = null
    render()
    return
  }

  if (!edgeStartVertexId.value) {
    edgeStartVertexId.value = vertex.id
    selectedVertexId.value = vertex.id
    selectedEdgeId.value = null
    render()
    return
  }

  if (edgeStartVertexId.value === vertex.id) {
    edgeStartVertexId.value = null
    render()
    return
  }

  const exists = edges.value.some((edge) => {
    return (
      (edge.source === edgeStartVertexId.value && edge.destination === vertex.id) ||
      (edge.source === vertex.id && edge.destination === edgeStartVertexId.value)
    )
  })

  if (!exists) {
    const source = vertices.value.find((item) => item.id === edgeStartVertexId.value)
    const destination = vertex

    const length = distance(source, destination)

    edges.value.push({
      id: `edge_${Date.now()}_${edges.value.length + 1}`,
      source: source.id,
      destination: destination.id,
      length_meters: round(length),
      is_bidirectional: true,
    })
  }

  selectedVertexId.value = vertex.id
  selectedEdgeId.value = null
  edgeStartVertexId.value = null

  render()
}

function createSpotAccessVertices() {
  const existingSpotIds = new Set(
    vertices.value
      .filter((vertex) => vertex.type === 'spot_access')
      .map((vertex) => vertex.spot_id)
  )

  let created = 0

  spots.value.forEach((spot) => {
    if (!spot.id || existingSpotIds.has(spot.id)) return

    const polygon = spot.polygon || []
    if (!polygon.length) return

    const center = polygonCenter(polygon)

    vertices.value.push({
      id: `spot_access_${spot.id}`,
      type: 'spot_access',
      x: round(center.x),
      y: round(center.y),
      name: spot.label || spot.number || spot.id,
      spot_id: spot.id,
    })

    created += 1
  })

  showMessage(`Создано точек мест: ${created}`)
  render()
}

function findVertexHit(point) {
  const radius = 14 / scale.value

  for (const vertex of [...vertices.value].reverse()) {
    const dx = point.x - vertex.x
    const dy = point.y - vertex.y

    if (Math.sqrt(dx * dx + dy * dy) <= radius) {
      return vertex
    }
  }

  return null
}

function findEdgeHit(point) {
  const threshold = 7 / scale.value

  for (const edge of [...edges.value].reverse()) {
    const source = vertices.value.find((vertex) => vertex.id === edge.source)
    const destination = vertices.value.find((vertex) => vertex.id === edge.destination)

    if (!source || !destination) continue

    const d = distancePointToSegment(point, source, destination)

    if (d <= threshold) {
      return edge
    }
  }

  return null
}

function distancePointToSegment(point, a, b) {
  const dx = b.x - a.x
  const dy = b.y - a.y

  if (dx === 0 && dy === 0) {
    return distance(point, a)
  }

  const t = clamp(
    ((point.x - a.x) * dx + (point.y - a.y) * dy) / (dx * dx + dy * dy),
    0,
    1
  )

  const projection = {
    x: a.x + t * dx,
    y: a.y + t * dy,
  }

  return distance(point, projection)
}

function recalculateConnectedEdges(vertexId) {
  edges.value.forEach((edge) => {
    if (edge.source !== vertexId && edge.destination !== vertexId) return

    const source = vertices.value.find((vertex) => vertex.id === edge.source)
    const destination = vertices.value.find((vertex) => vertex.id === edge.destination)

    if (!source || !destination) return

    edge.length_meters = round(distance(source, destination))
  })
}

function deleteSelectedVertex() {
  if (!selectedVertex.value) return

  const vertexId = selectedVertex.value.id

  vertices.value = vertices.value.filter((vertex) => vertex.id !== vertexId)
  edges.value = edges.value.filter((edge) => {
    return edge.source !== vertexId && edge.destination !== vertexId
  })
  entrances.value = entrances.value.filter((entrance) => entrance.vertex_id !== vertexId)

  selectedVertexId.value = null
  selectedEdgeId.value = null

  render()
}

function deleteSelectedEdge() {
  if (!selectedEdge.value) return

  edges.value = edges.value.filter((edge) => edge.id !== selectedEdge.value.id)
  selectedEdgeId.value = null

  render()
}

function buildMapPayload() {
  const normalizedEntrances = vertices.value
    .filter((vertex) => vertex.type === 'entrance')
    .map((vertex, index) => ({
      id: vertex.id,
      name: vertex.name || `Въезд ${index + 1}`,
      vertex_id: vertex.id,
      x: round(vertex.x),
      y: round(vertex.y),
      parking_id: parkingId,
    }))

  return {
    version: 1,
    parking: {
      id: parkingId,
      name: parkingName.value || parking.value?.name || parkingId,
      db_id: parking.value?.db_id,
      company_id: parking.value?.company_id,
    },
    frame_meta: {
      width: image.value?.naturalWidth || layout.value?.frame_meta?.width || 0,
      height: image.value?.naturalHeight || layout.value?.frame_meta?.height || 0,
    },
    entrances: normalizedEntrances,
    vertices: vertices.value.map((vertex) => ({
      id: vertex.id,
      type: vertex.type,
      x: round(vertex.x),
      y: round(vertex.y),
      name: vertex.name || '',
      spot_id: vertex.spot_id || null,
    })),
    edges: edges.value.map((edge) => ({
      id: edge.id,
      source: edge.source,
      destination: edge.destination,
      length_meters: round(edge.length_meters || 1),
      is_bidirectional: edge.is_bidirectional !== false,
      one_way: edge.is_bidirectional === false,
    })),
  }
}

async function saveMap() {
  saving.value = true
  error.value = ''
  message.value = ''

  try {
    const map = buildMapPayload()
    await parkingService.saveMap(parkingId, map)
    showMessage(`Map сохранён. Точек: ${map.vertices.length}, рёбер: ${map.edges.length}`)
  } catch (err) {
    console.error('Ошибка сохранения map:', err)
    showError('Не удалось сохранить цифровую карту')
  } finally {
    saving.value = false
  }
}

function setMode(nextMode) {
  mode.value = nextMode
  edgeStartVertexId.value = null
}

function resetView() {
  fitImageToCanvas()
}

function goSetup() {
  router.push(`/admin/parkings/${parkingId}/setup`)
}

function goUserMap() {
  router.push({
    path: '/main',
    query: {
      parking_id: parkingId,
    },
  })
}

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

function polygonCenter(points) {
  const sum = points.reduce(
    (acc, point) => {
      acc.x += Number(point.x)
      acc.y += Number(point.y)
      return acc
    },
    { x: 0, y: 0 }
  )

  return {
    x: sum.x / points.length,
    y: sum.y / points.length,
  }
}

function distance(a, b) {
  const dx = Number(a.x) - Number(b.x)
  const dy = Number(a.y) - Number(b.y)
  return Math.sqrt(dx * dx + dy * dy)
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function round(value) {
  return Math.round(Number(value) * 100) / 100
}

watch(
  [vertices, edges],
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
  width: 330px;
  min-width: 330px;
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
.selected-box label {
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

.checkbox-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 10px 0;
}

.checkbox-row input {
  width: auto;
  height: auto;
}

.checkbox-row span {
  color: #1f2937;
  text-transform: none;
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

.section-title {
  margin-bottom: 8px;
  color: #2d8fe3;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
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

.selected-box {
  margin-top: 14px;
  padding: 12px;
  border: 1px solid #f59e0b;
  border-radius: 10px;
  background: #fffbeb;
}

.selected-box input {
  margin-bottom: 10px;
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