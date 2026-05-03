<template>
  <div class="user-page">
    <div v-if="errorMessage" class="alert error">
      {{ errorMessage }}
    </div>

    <div v-if="successMessage" class="alert success">
      {{ successMessage }}
    </div>

    <div class="table-container">
      <table class="user-table">
        <thead>
          <tr>
            <th>№</th>
            <th>ФИО</th>
            <th>Статус</th>
            <th>Блокировка</th>
            <th>Логин</th>
            <th>Роль</th>
            <th>Пароль</th>
            <th>Почта</th>
            <th>Действия</th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="(user, index) in users" :key="user.local_id || user.id">
            <td>{{ index + 1 }}</td>

            <td>
              <input
                v-model="user.full_name"
                class="input"
                placeholder="ФИО"
              />
            </td>

            <td>
              <span v-if="user.isNew">Новый</span>
              <span v-else>{{ user.is_active ? 'OK' : 'Отключён' }}</span>
            </td>

            <td>
              <span v-if="user.locked_until">
                до {{ formatDate(user.locked_until) }}
              </span>
              <span v-else>-</span>
            </td>

            <td>
              <input
                v-model="user.username"
                class="input"
                placeholder="Логин"
              />
            </td>

            <td>
              <select v-model="user.role" class="input">
                <option value="user">user</option>
                <option value="admin">admin</option>
              </select>
            </td>

            <td>
              <input
                v-if="user.isNew"
                v-model="user.password"
                class="input"
                type="password"
                placeholder="мин. 10 символов"
              />

              <button
                v-else
                class="refresh-pass-btn"
                @click="openPasswordModal(user)"
                title="Сменить пароль"
              >
                <img src="../../assets/img/refresh.png" width="20" alt="password">
              </button>
            </td>

            <td>
              <input
                v-model="user.email"
                class="input"
                placeholder="email@example.com"
              />
            </td>

            <td class="actions">
              <button class="btn save" @click="saveUser(user)" title="Сохранить">
                <img src="../../assets/img/save.png" alt="save">
              </button>

              <button
                v-if="!user.isNew"
                class="btn lock"
                :class="{ active: isBlocked(user) }"
                @click="toggleBlock(user)"
                title="Заблокировать/разблокировать"
              >
                <img
                  :src="isBlocked(user) ? unlockIcon : lockIcon"
                  alt="lock"
                >
              </button>

              <button
                class="btn delete"
                @click="confirmDelete(user)"
                title="Удалить"
              >
                <img src="../../assets/img/trash.png" alt="trash">
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="add-user-container">
        <button class="add-user-btn" @click="addUser">
          + Добавить пользователя
        </button>

        <button class="reload-btn" @click="loadUsers">
          Обновить
        </button>
      </div>
    </div>

    <div v-if="showPasswordModal" class="modal">
      <div class="modal-content">
        <button class="close-btn" @click="closePasswordModal">
          ✖
        </button>

        <p style="color: #3B66F4">Введите новый пароль</p>

        <input
          v-model="newPassword"
          class="form-input"
          type="password"
          placeholder="минимум 10 символов"
        />

        <button class="save-half" @click="savePassword">
          Сохранить
        </button>
      </div>
    </div>

    <div v-if="showDeleteModal" class="modal">
      <div class="modal-content">
        <p>Удалить пользователя?</p>

        <div class="modal-actions">
          <button class="cancel-btn" @click="showDeleteModal = false">
            Нет
          </button>

          <button class="confirm-btn" @click="deleteUser">
            Да
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { adminService } from '@/services/admin'
import lockIcon from '../../assets/img/lock.png'
import unlockIcon from '../../assets/img/unlock.png'

const users = ref([])

const showPasswordModal = ref(false)
const showDeleteModal = ref(false)

const selectedUser = ref(null)
const newPassword = ref('')

const errorMessage = ref('')
const successMessage = ref('')

function showSuccess(message) {
  successMessage.value = message
  errorMessage.value = ''

  setTimeout(() => {
    successMessage.value = ''
  }, 3000)
}

function showError(message) {
  errorMessage.value = message
  successMessage.value = ''
}

function normalizeUser(user) {
  return {
    id: user.id,
    username: user.username || '',
    email: user.email || '',
    full_name: user.full_name || '',
    role: user.role || 'user',
    is_active: user.is_active !== false,
    failed_attempts: user.failed_attempts || 0,
    locked_until: user.locked_until || null,
    isNew: false,
  }
}

async function loadUsers() {
  try {
    const data = await adminService.getUsers()
    users.value = Array.isArray(data) ? data.map(normalizeUser) : []
  } catch (error) {
    console.error('Ошибка загрузки пользователей:', error)
    showError('Не удалось загрузить пользователей')
  }
}

function addUser() {
  users.value.push({
    local_id: `new-${Date.now()}`,
    username: '',
    email: '',
    full_name: '',
    role: 'user',
    password: '',
    is_active: true,
    failed_attempts: 0,
    locked_until: null,
    isNew: true,
  })
}

function validateUser(user) {
  if (!user.username || user.username.trim().length < 3) {
    return 'Логин должен быть не короче 3 символов'
  }

  if (!user.email || !user.email.includes('@')) {
    return 'Введите корректную почту'
  }

  if (!user.role) {
    return 'Выберите роль пользователя'
  }

  if (user.isNew && (!user.password || user.password.length < 10)) {
    return 'Пароль должен быть не короче 10 символов'
  }

  return null
}

async function saveUser(user) {
  const validationError = validateUser(user)

  if (validationError) {
    showError(validationError)
    return
  }

  try {
    if (user.isNew) {
      const created = await adminService.createUser({
        username: user.username.trim(),
        email: user.email.trim(),
        full_name: user.full_name?.trim() || null,
        role: user.role,
        password: user.password,
        is_active: true,
      })

      const index = users.value.findIndex((item) => item === user)
      users.value[index] = normalizeUser(created)

      showSuccess('Пользователь создан')
      return
    }

    const updated = await adminService.updateUser(user.id, {
      username: user.username.trim(),
      email: user.email.trim(),
      full_name: user.full_name?.trim() || null,
      role: user.role,
      is_active: user.is_active !== false,
    })

    const index = users.value.findIndex((item) => item.id === user.id)
    users.value[index] = normalizeUser(updated)

    showSuccess('Пользователь обновлён')
  } catch (error) {
    console.error('Ошибка сохранения пользователя:', error)

    if (error.response?.status === 409) {
      showError('Пользователь с таким логином или почтой уже существует')
    } else if (error.response?.status === 422) {
      showError('Проверь поля: логин от 3 символов, пароль от 10 символов, корректная почта')
    } else if (error.response?.status === 403) {
      showError('Нет прав администратора')
    } else {
      showError('Не удалось сохранить пользователя')
    }
  }
}

function closePasswordModal() {
  showPasswordModal.value = false
  selectedUser.value = null
  newPassword.value = ''
}

function openPasswordModal(user) {
  selectedUser.value = user
  showPasswordModal.value = true
}

async function savePassword() {
  if (!selectedUser.value) {
    return
  }

  if (!newPassword.value || newPassword.value.length < 10) {
    showError('Новый пароль должен быть не короче 10 символов')
    return
  }

  try {
    const updated = await adminService.changeUserPassword(selectedUser.value.id, newPassword.value)

    const index = users.value.findIndex((item) => item.id === selectedUser.value.id)
    users.value[index] = normalizeUser(updated)

    closePasswordModal()
    showSuccess('Пароль обновлён')
  } catch (error) {
    console.error('Ошибка смены пароля:', error)
    showError('Не удалось сменить пароль')
  }
}

function isBlocked(user) {
  return Boolean(user.locked_until)
}

async function toggleBlock(user) {
  try {
    const block = !isBlocked(user)

    const updated = await adminService.blockUser(user.id, block, 30)

    const index = users.value.findIndex((item) => item.id === user.id)
    users.value[index] = normalizeUser(updated)

    showSuccess(block ? 'Пользователь заблокирован' : 'Пользователь разблокирован')
  } catch (error) {
    console.error('Ошибка блокировки пользователя:', error)
    showError('Не удалось изменить блокировку')
  }
}

function confirmDelete(user) {
  selectedUser.value = user
  showDeleteModal.value = true
}

async function deleteUser() {
  if (!selectedUser.value) {
    return
  }

  try {
    if (!selectedUser.value.isNew) {
      await adminService.deleteUser(selectedUser.value.id)
    }

    users.value = users.value.filter((item) => item !== selectedUser.value)

    showDeleteModal.value = false
    selectedUser.value = null

    showSuccess('Пользователь удалён')
  } catch (error) {
    console.error('Ошибка удаления пользователя:', error)
    showError('Не удалось удалить пользователя')
  }
}

function formatDate(value) {
  if (!value) {
    return '-'
  }

  return new Date(value).toLocaleString('ru-RU')
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.user-page {
  width: 100%;
  padding: 0;
}

.alert {
  max-width: 100%;
  margin: 0 0 16px;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 15px;
}

.alert.error {
  background: #fee2e2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

.alert.success {
  background: #dcfce7;
  color: #166534;
  border: 1px solid #bbf7d0;
}

.table-container {
  width: 100%;
  max-width: 100%;
  margin: 0 auto;
  padding: 24px;
  box-sizing: border-box;
  background: #f7f3f3;
  border-radius: 0;
  overflow-x: hidden;
}

.user-table {
  width: 100%;
  table-layout: fixed;
  border-collapse: separate;
  border-spacing: 0;
  background: #f7f3f3;
  border: 1px solid #777;
  border-radius: 10px;
  overflow: hidden;
}

.user-table th,
.user-table td {
  border-right: 1px solid #777;
  border-bottom: 1px solid #aaa;
  padding: 9px 6px;
  text-align: center;
  vertical-align: middle;
  box-sizing: border-box;
}

.user-table th:last-child,
.user-table td:last-child {
  border-right: none;
}

.user-table tr:last-child td {
  border-bottom: none;
}

.user-table th {
  background: #d9d9d9;
  font-weight: 700;
  font-size: 14px;
  white-space: nowrap;
}

.user-table td {
  font-size: 14px;
}

.user-table th:nth-child(1),
.user-table td:nth-child(1) {
  width: 4%;
}

.user-table th:nth-child(2),
.user-table td:nth-child(2) {
  width: 16%;
}

.user-table th:nth-child(3),
.user-table td:nth-child(3) {
  width: 7%;
}

.user-table th:nth-child(4),
.user-table td:nth-child(4) {
  width: 10%;
}

.user-table th:nth-child(5),
.user-table td:nth-child(5) {
  width: 14%;
}

.user-table th:nth-child(6),
.user-table td:nth-child(6) {
  width: 9%;
}

.user-table th:nth-child(7),
.user-table td:nth-child(7) {
  width: 12%;
}

.user-table th:nth-child(8),
.user-table td:nth-child(8) {
  width: 15%;
}

.user-table th:nth-child(9),
.user-table td:nth-child(9) {
  width: 13%;
}

.input {
  width: 100%;
  height: 36px;
  box-sizing: border-box;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 0 8px;
  background: #fff;
  font-size: 13px;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
}

select.input {
  cursor: pointer;
}

.actions {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
  flex-wrap: nowrap;
  min-width: 116px;
}

.btn {
  width: 32px;
  height: 32px;
  min-width: 32px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn img {
  width: 19px;
  height: 19px;
}

.btn.save {
  background: #ffea00;
}

.btn.lock {
  background: #ff4d4d;
}

.btn.lock.active {
  background: #22c55e;
}

.btn.delete {
  background: #2d8fe3;
}

.refresh-pass-btn {
  width: 34px;
  height: 34px;
  min-width: 34px;
  border: none;
  border-radius: 8px;
  background: #2d8fe3;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.refresh-pass-btn img {
  width: 18px;
  height: 18px;
}

.add-user-container {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 24px;
}

.add-user-btn,
.reload-btn,
.save-half,
.cancel-btn,
.confirm-btn {
  border: none;
  border-radius: 10px;
  padding: 12px 24px;
  cursor: pointer;
  font-weight: 700;
}

.add-user-btn {
  background: #2d8fe3;
  color: white;
}

.reload-btn {
  background: #eef2f7;
  color: #1f2937;
}

.modal {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}

.modal-content {
  min-width: 320px;
  background: white;
  border-radius: 16px;
  padding: 24px;
  position: relative;
  text-align: center;
}

.close-btn {
  position: absolute;
  top: 10px;
  right: 12px;
  border: none;
  background: transparent;
  cursor: pointer;
}

.form-input {
  width: 100%;
  height: 40px;
  box-sizing: border-box;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 0 10px;
  margin: 12px 0;
}

.save-half {
  background: #2d8fe3;
  color: white;
}

.modal-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.cancel-btn {
  background: #e5e7eb;
}

.confirm-btn {
  background: #ef4444;
  color: white;
}

@media (max-width: 1100px) {
  .table-container {
    padding: 12px;
    overflow-x: auto;
  }

  .user-table {
    min-width: 980px;
  }
}
</style>