<template>
  <!-- Основной контейнер страницы списка парковок -->
  <div class="parking-list-container">
  
    <!-- ===== УВЕДОМЛЕНИЯ ===== -->
    <transition name="toast">
      <div v-if="notification.show" :class="['toast-notification', notification.type]">
        <span class="toast-icon">{{ notification.type === 'success' ? '✓' : '⚠' }}</span>
        <span class="toast-message">{{ notification.message }}</span>
      </div>
    </transition>

    <!-- ===== ОСНОВНОЕ СОДЕРЖИМОЕ ===== -->
    <div class="content">

      <!-- ===== МОДАЛЬНОЕ ОКНО ДОБАВЛЕНИЯ ПАРКОВКИ ===== -->
      <div v-if="showAddParkingModal" class="modal-overlay" @click="closeParkingModal">
        <div class="modal-container" @click.stop>
          <div class="modal-header">
            <h3>Добавить парковку</h3>
            <button class="modal-close" @click="closeParkingModal">&times;</button>
          </div>
          
          <div class="modal-body">
            <div class="form-group">
              <label>Название</label>
              <input 
                type="text" 
                v-model="newParking.name" 
                class="form-input"
                :class="{ 'input-error': parkingErrors.name }"
                placeholder="Введите название"
                autofocus
              />
              <div v-if="parkingErrors.name" class="field-error">
                {{ parkingErrors.name }}
              </div>
            </div>
            
            <div class="form-group">
              <label>Адрес</label>
              <input 
                type="text" 
                v-model="newParking.address" 
                class="form-input"
                :class="{ 'input-error': parkingErrors.address }"
                placeholder="Введите адрес"
              />
              <div v-if="parkingErrors.address" class="field-error">
                {{ parkingErrors.address }}
              </div>
            </div>
          </div>
          
          <div class="modal-footer">
            <button class="btn-cancel" @click="closeParkingModal">Отмена</button>
            <button class="btn-save" @click="saveParking">Сохранить</button>
          </div>
        </div>
      </div>

      <!-- ===== МОДАЛЬНОЕ ОКНО ДОБАВЛЕНИЯ КАМЕРЫ ===== -->
      <div v-if="showAddCameraModal" class="modal-overlay" @click="closeCameraModal">
        <div class="modal-container" @click.stop>
          <div class="modal-header">
            <h3>Добавить камеру</h3>
            <button class="modal-close" @click="closeCameraModal">&times;</button>
          </div>
          
          <div class="modal-body">
            <div class="form-group">
              <label>Название</label>
              <input 
                type="text" 
                v-model="newCamera.name" 
                class="form-input"
                :class="{ 'input-error': cameraErrors.name }"
                placeholder="Введите название"
                autofocus
              />
              <div v-if="cameraErrors.name" class="field-error">
                {{ cameraErrors.name }}
              </div>
            </div>
            
            <div class="form-group">
              <label>URL</label>
              <input 
                type="text" 
                v-model="newCamera.url" 
                class="form-input"
                :class="{ 'input-error': cameraErrors.url }"
                placeholder="rtsp://..."
              />
              <div v-if="cameraErrors.url" class="field-error">
                {{ cameraErrors.url }}
              </div>
            </div>
          </div>
          
          <div class="modal-footer">
            <button class="btn-cancel" @click="closeCameraModal">Отмена</button>
            <button class="btn-save" @click="saveCamera(selectedParkingId)">Сохранить</button>
          </div>
        </div>
      </div>

      <!-- ===== МОДАЛЬНОЕ ОКНО ПОДТВЕРЖДЕНИЯ УДАЛЕНИЯ ===== -->
      <transition name="modal-fade">
        <div v-if="showDeleteModal" class="modal-overlay" @click="closeDeleteModal">
          <div class="modal-container delete-modal" @click.stop>
            <div class="modal-header delete-header">
              <h3>Удалить камеру</h3>
            </div>
            <div class="modal-body">
              <p class="delete-text">
                Вы действительно хотите удалить камеру 
                <span class="camera-name">{{ deletingCamera?.name }}</span>?
              </p>
            </div>
            
            <div class="modal-footer delete-footer">
              <button class="btn-cancel" @click="closeDeleteModal">Отмена</button>
              <button class="btn-delete" @click="confirmDelete">Удалить</button>
            </div>
          </div>
        </div>
      </transition>

      <!-- ===== ИНДИКАТОР ЗАГРУЗКИ ===== -->
      <div v-if="isLoading" class="loading-indicator">
        Загрузка данных...
      </div>

      <!-- ===== СООБЩЕНИЕ ОБ ОШИБКЕ ===== -->
      <div v-if="errorMessage" class="error-message">
        {{ errorMessage }}
      </div>

      <!-- ===== СПИСОК ПАРКОВОК ===== -->
      <div class="parking-list">
        <!-- Перебор всех парковок -->
        <div 
          v-for="parking in parkings" 
          :key="parking.id" 
          class="parking-item"
        >
          <!-- ===== ЗАГОЛОВОК ПАРКОВКИ ===== -->
          <div class="parking-header">
            <span class="parking-name">{{ parking.name }}</span>
            
            <!-- Группа кнопок справа  -->
            <div class="header-buttons">
              <!-- Кнопка перехода в редактор разметки -->
              <button class="editor-btn" @click="openEditor(parking.id)">
                Редактор
              </button>
              <!-- Кнопка сворачивания/разворачивания информации о парковке -->
              <button 
                class="collapse-btn" 
                @click="toggleParking(parking.id)"
              >
                <span :class="['arrow', { rotated: expandedParking === parking.id }]">▲</span>
              </button>
            </div>
          </div>

          <!-- ===== ДЕТАЛЬНАЯ ИНФОРМАЦИЯ О ПАРКОВКЕ  ===== -->
          <div v-if="expandedParking === parking.id" class="parking-details">
            <!-- Адрес парковки -->
            <div class="address-field">
              <label>Адрес:</label>
              <span>{{ parking.address }}</span>
            </div>

            <!-- ===== ТАБЛИЦА КАМЕР ===== -->
            <table class="cameras-table">
              <thead>
                <tr>
                  <th>Камера</th>
                  <th>Статус</th>
                  <th>URL</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <!-- Перебор камер парковки -->
                <tr v-for="camera in parking.cameras" :key="camera.id">
                  <td>{{ camera.name }}</td>
                  <td>
                    <!-- Индикатор статуса камеры (онлайн/офлайн) -->
                    <span :class="['status-badge', camera.status]">
                      {{ camera.status === 'online' ? 'активен' : 'офлайн' }}
                    </span>
                  </td>
                  <td>{{ camera.url }}</td>
                  <td>
                    <!-- Кнопка удаления камеры -->
                    <button class="delete-btn" @click="openDeleteModal(parking.id, camera)">
                      🗑️
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>

            <!-- Кнопка добавления камеры -->
            <div class="center-button">
              <button class="add-camera-btn" @click="openAddCameraForm(parking.id)">
                Добавить камеру
              </button>
            </div>
          </div>
        </div>

        <!-- ===== КНОПКА ДОБАВЛЕНИЯ НОВОЙ ПАРКОВКИ ===== -->
        <div class="center-button" v-if="!showAddParkingModal">
          <button class="add-parking-btn" @click="openAddParkingForm">
            Добавить парковку
          </button>
        </div>
      </div>

    </div>

  </div>
</template>

<script>
// =====  ПЕРЕКЛЮЧАТЕЛЬ РЕЖИМА ДАННЫХ =====
// false, когда backend будет готов
const USE_MOCK_DATA = true

// Импорты сервисов 
// import { parkingService } from '@/services/parking'
// import { cameraService } from '@/services/camera'

export default {
  name: 'ParkingListView',
  
  // ===== ДАННЫЕ КОМПОНЕНТА =====
  data() {
    return {
      USE_MOCK_DATA,
      expandedParking: null,
      showAddParkingModal: false,
      showAddCameraModal: false,
      showDeleteModal: false,
      selectedParkingId: null,
      deletingCamera: null,
      deletingParkingId: null,
      
      notification: {
        show: false,
        message: '',
        type: 'success'
      },
      
      parkingErrors: { name: '', address: '' },
      cameraErrors: { name: '', url: '' },
      
      parkings: [
        {
          id: 1,
          name: 'Парковка 1',
          address: 'ул. Ленина, 10',
          cameras: [
            { id: 1, name: 'Камера 1', status: 'online', url: 'rtsp://172.16.31.61/1' }
          ]
        },
        {
          id: 2,
          name: 'Парковка 2',
          address: 'пр. Мира, 25',
          cameras: [
            { id: 2, name: 'Камера 2', status: 'offline', url: 'rtsp://172.16.31.62/1' },
            { id: 3, name: 'Камера 3', status: 'online', url: 'rtsp://172.16.31.63/1' }
          ]
        }
      ],
      
      newParking: { name: '', address: '' },
      newCamera: { name: '', url: '' },
      
      isLoading: false,
      errorMessage: ''
    }
  },
  
  async mounted() {
    if (!USE_MOCK_DATA) {
      await this.loadParkings()
    }
  },
  
  methods: {
    showNotification(message, type = 'success') {
      this.notification = { show: true, message, type }
      setTimeout(() => { this.notification.show = false }, 3000)
    },
    
    validateParking() {
      this.parkingErrors = { name: '', address: '' }
      let isValid = true
      if (!this.newParking.name?.trim()) {
        this.parkingErrors.name = 'Заполните поле "Название"'
        isValid = false
      }
      if (!this.newParking.address?.trim()) {
        this.parkingErrors.address = 'Заполните поле "Адрес"'
        isValid = false
      }
      return isValid
    },
    
    validateCamera() {
      this.cameraErrors = { name: '', url: '' }
      let isValid = true
      if (!this.newCamera.name?.trim()) {
        this.cameraErrors.name = 'Заполните поле "Название"'
        isValid = false
      }
      if (!this.newCamera.url?.trim()) {
        this.cameraErrors.url = 'Заполните поле "URL"'
        isValid = false
      }
      return isValid
    },
    
    async loadParkings() {
      this.isLoading = true
      this.errorMessage = ''
      try {
        const data = await parkingService.getAllParkings()
        this.parkings = data
      } catch (error) {
        console.error('Ошибка загрузки парковок:', error)
        this.errorMessage = 'Не удалось загрузить список парковок'
        this.parkings = []
      } finally {
        this.isLoading = false
      }
    },

    toggleParking(id) {
      this.expandedParking = this.expandedParking === id ? null : id
    },
    
    openEditor(id) {
      this.$router.push(`/editor/${id}`)
    },
    
    openAddParkingForm() {
      this.newParking = { name: '', address: '' }
      this.parkingErrors = { name: '', address: '' }
      this.showAddParkingModal = true
    },
    
    closeParkingModal() {
      this.showAddParkingModal = false
      this.newParking = { name: '', address: '' }
      this.parkingErrors = { name: '', address: '' }
    },
    
    async saveParking() {
      if (!this.validateParking()) return
      
      if (USE_MOCK_DATA) {
        const newId = this.parkings.length > 0 
          ? Math.max(...this.parkings.map(p => p.id)) + 1 : 1
        this.parkings.push({
          id: newId,
          name: this.newParking.name,
          address: this.newParking.address,
          cameras: []
        })
        this.closeParkingModal()
        this.expandedParking = newId
        this.showNotification('Парковка успешно добавлена', 'success')
      } else {
        this.isLoading = true
        try {
          await parkingService.createParking(this.newParking)
          await this.loadParkings()
          this.closeParkingModal()
          this.showNotification('Парковка успешно добавлена', 'success')
        } catch (error) {
          console.error('Ошибка создания парковки:', error)
          this.showNotification('Не удалось создать парковку', 'error')
        } finally {
          this.isLoading = false
        }
      }
    },
    
    openAddCameraForm(parkingId) {
      this.selectedParkingId = parkingId
      this.newCamera = { name: '', url: '' }
      this.cameraErrors = { name: '', url: '' }
      this.showAddCameraModal = true
    },
    
    closeCameraModal() {
      this.showAddCameraModal = false
      this.selectedParkingId = null
      this.newCamera = { name: '', url: '' }
      this.cameraErrors = { name: '', url: '' }
    },
    
    async saveCamera(parkingId) {
      if (!this.validateCamera()) return
      
      if (USE_MOCK_DATA) {
        const parking = this.parkings.find(p => p.id === parkingId)
        if (parking) {
          const newId = parking.cameras.length > 0
            ? Math.max(...parking.cameras.map(c => c.id)) + 1 : 1
          parking.cameras.push({
            id: newId,
            name: this.newCamera.name,
            status: 'offline',
            url: this.newCamera.url
          })
        }
        this.closeCameraModal()
        this.showNotification('Камера успешно добавлена', 'success')
      } else {
        this.isLoading = true
        try {
          await cameraService.createCamera({
            name: this.newCamera.name,
            rtsp_url: this.newCamera.url,
            parking_id: parkingId
          })
          await this.loadParkings()
          this.closeCameraModal()
          this.showNotification('Камера успешно добавлена', 'success')
        } catch (error) {
          console.error('Ошибка создания камеры:', error)
          this.showNotification('Не удалось добавить камеру', 'error')
        } finally {
          this.isLoading = false
        }
      }
    },
    
    openDeleteModal(parkingId, camera) {
      this.deletingParkingId = parkingId
      this.deletingCamera = camera
      this.showDeleteModal = true
    },
    
    closeDeleteModal() {
      this.showDeleteModal = false
      this.deletingCamera = null
      this.deletingParkingId = null
    },
    
    async confirmDelete() {
      if (USE_MOCK_DATA) {
        const parking = this.parkings.find(p => p.id === this.deletingParkingId)
        if (parking) {
          parking.cameras = parking.cameras.filter(c => c.id !== this.deletingCamera.id)
        }
        this.showNotification('Камера удалена', 'success')
      } else {
        this.isLoading = true
        try {
          await cameraService.deleteCamera(this.deletingCamera.id)
          await this.loadParkings()
          this.showNotification('Камера удалена', 'success')
        } catch (error) {
          console.error('Ошибка удаления камеры:', error)
          this.showNotification('Не удалось удалить камеру', 'error')
        } finally {
          this.isLoading = false
        }
      }
      this.closeDeleteModal()
    },
    
    goBack() {
      this.$router.push('/admin')
    }
  }
}
</script>

<style scoped>
/* ========== FIX: УБИРАЕМ ГОРИЗОНТАЛЬНУЮ ПРОКРУТКУ ========== */
.parking-list-container {
  min-height: 100vh;
  background-color: #f5f5f5;
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 100vw;
  overflow-x: hidden; /* ← Важно! */
  box-sizing: border-box;
}

/* ========== УВЕДОМЛЕНИЯ ========== */
.toast-notification {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  padding: 15px 30px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  gap: 10px;
  z-index: 2000;
  font-size: 15px;
  font-weight: 500;
  min-width: 300px;
  justify-content: center;
}

.toast-notification.success {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.toast-notification.error {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.toast-icon {
  font-size: 18px;
  font-weight: bold;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-20px);
}

/* ========== ИНДИКАТОРЫ ========== */
.loading-indicator {
  background-color: #d1ecf1;
  color: #0c5460;
  padding: 10px 20px;
  text-align: center;
  font-size: 14px;
  margin-bottom: 20px;
  border-radius: 4px;
}

.error-message {
  background-color: #f8d7da;
  color: #721c24;
  padding: 10px 20px;
  text-align: center;
  font-size: 14px;
  margin-bottom: 20px;
  border-radius: 4px;
  border: 1px solid #f5c6cb;
}

/* ========== ОСНОВНОЙ КОНТЕНТ ========== */
.content {
  flex: 1;
  padding: 30px 40px;
  width: 100%;
  max-width: 100%;
  margin: 0;
  box-sizing: border-box;
  overflow-x: hidden;
}

/* ========== СПИСОК ПАРКОВОК — НА ВСЮ ШИРИНУ ========== */
.parking-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
  width: 100%;
  max-width: 100%;
}

.parking-item {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  overflow: hidden;
  width: 100%;
  box-sizing: border-box;
}

/* ========== ШАПКА ПАРКОВКИ ========== */
.parking-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  background-color: #f9f9f9;
  border-bottom: 1px solid #eee;
  gap: 15px;
  width: 100%;
  box-sizing: border-box;
}

.parking-name {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-right: auto;
}

.header-buttons {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.editor-btn {
  background-color: #2689E6;
  color: white;
  border: none;
  padding: 10px 25px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
}

.editor-btn:hover {
  background-color: #2689E6;
}

.collapse-btn {
  background: none;
  border: none;
  color: #2689E6;
  font-size: 18px;
  cursor: pointer;
  padding: 5px 10px;
}

.arrow {
  display: inline-block;
  transition: transform 0.3s;
}

.arrow.rotated {
  transform: rotate(180deg);
}

/* ========== ДЕТАЛИ ПАРКОВКИ ========== */
.parking-details {
  padding: 20px;
  width: 100%;
  box-sizing: border-box;
}

.address-field {
  margin-bottom: 20px;
  color: #666;
}

.address-field label {
  font-weight: 600;
  margin-right: 10px;
}

/* ========== ТАБЛИЦА КАМЕР ========== */
.cameras-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 20px;
}

.cameras-table th,
.cameras-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.cameras-table th {
  background-color: #f5f5f5;
  font-weight: 600;
  color: #333;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge.online {
  background-color: #d4edda;
  color: #155724;
}

.status-badge.offline {
  background-color: #f8d7da;
  color: #721c24;
}

.delete-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 18px;
  padding: 5px;
}

/* ========== КНОПКИ ДОБАВЛЕНИЯ ========== */
.center-button {
  display: flex;
  justify-content: center;
  width: 100%;
  margin-top: 15px;
}

.add-camera-btn {
  background-color: #2689E6;
  color: white;
  border: none;
  padding: 12px 30px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
}

.add-parking-btn {
  background-color: #2689E6;
  color: white;
  border: none;
  padding: 15px 40px;
  border-radius: 4px;
  font-size: 16px;
  cursor: pointer;
}

/* ========== МОДАЛЬНЫЕ ОКНА ========== */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  animation: fadeIn 0.3s ease;
  width: 100vw;
  height: 100vh;
}

.modal-container {
  background-color: white;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow: hidden;
  animation: slideIn 0.3s ease;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 25px;
  border-bottom: 1px solid #eee;
}

.modal-header h3 {
  margin: 0;
  color: #2689E6;
  font-size: 20px;
}

.modal-close {
  background: none;
  border: none;
  font-size: 28px;
  color: #999;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}

.modal-close:hover {
  color: #333;
  background-color: #f5f5f5;
}

.modal-body {
  padding: 25px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 20px 25px;
  border-top: 1px solid #eee;
  background-color: #f9f9f9;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideIn {
  from { transform: translateY(-30px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

/* ========== МОДАЛКА УДАЛЕНИЯ ========== */
.delete-modal {
  max-width: 450px;
  text-align: center;
}

.delete-header {
  flex-direction: column;
  gap: 10px;
  padding: 30px 25px 20px;
  border-bottom: none;
}

.delete-header h3 {
  color: #DC143C;
  font-size: 22px;
}

.delete-text {
  font-size: 16px;
  color: #333;
  margin: 10px 0;
  line-height: 1.6;
}

.camera-name {
  font-weight: 600;
  color: #2689E6;
}

.delete-footer {
  background-color: #fff;
  border-top: 1px solid #eee;
  padding: 20px 25px 25px;
}

.btn-delete {
  background-color: #DC143C;
  color: white;
  border: none;
  padding: 10px 25px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
}

.btn-delete:hover {
  background-color: #c41236;
}

.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: all 0.3s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-from .modal-container,
.modal-fade-leave-to .modal-container {
  transform: scale(0.9);
}

/* ========== ФОРМЫ ========== */
.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: #666;
  font-size: 14px;
}

.form-input {
  width: 100%;
  padding: 10px 0;
  border: none;
  border-bottom: 2px solid #ddd;
  font-size: 16px;
  outline: none;
  box-sizing: border-box;
}

.form-input:focus {
  border-bottom-color: #2689E6;
}

.form-input.input-error {
  border-bottom-color: #DC143C;
}

.field-error {
  color: #DC143C;
  font-size: 13px;
  margin-top: 5px;
  font-weight: 500;
}

.btn-save,
.btn-cancel {
  padding: 10px 25px;
  border: none;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
}

.btn-save {
  background-color: #2689E6;
  color: white;
}

.btn-save:hover {
  background-color: #2689E6;
}

.btn-cancel {
  background-color: #f0f0f0;
  color: #666;
}

.btn-cancel:hover {
  background-color: #e0e0e0;
}

/* ========== АДАПТИВНОСТЬ ========== */
@media (max-width: 600px) {
  .content {
    padding: 20px;
  }
  
  .modal-container {
    width: 95%;
    margin: 20px;
  }
  
  .modal-body {
    padding: 20px;
  }
  
  .modal-footer {
    flex-direction: column;
  }
  
  .modal-footer button {
    width: 100%;
  }
  
  .toast-notification {
    width: 90%;
    min-width: auto;
    left: 5%;
    transform: none;
  }
  
  .parking-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 15px;
  }
  
  .header-buttons {
    width: 100%;
    justify-content: flex-end;
  }
  
  .parking-name {
    margin-right: 0;
    width: 100%;
  }
}
</style>