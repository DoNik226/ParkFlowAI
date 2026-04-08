<template>
  <div class="user-page">

    <!-- HEADER
    <header class="header">
      <div class="logo">ParkFlow AI</div>

      <button class="back" @click="$router.push('/admin')">
        <img src="../../assets/img/sign-out.png" width="30">
      </button>
    </header> -->

    <!-- TABLE -->
    <div class="table-container">

      <table class="user-table">
        <thead>
          <tr>
            <th>№</th>
            <th>ФИО</th>
            <th>Статус</th>
            <th>Блокировка</th>
            <th>Логин</th>
            <th>Пароль</th>
            <th>Почта</th>
            <th>Действия</th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="(user, index) in users" :key="user.id">
            <td>{{ index + 1 }}</td>

            <td>
              <input v-model="user.name" class="input" />
            </td>

            <td>
              <span v-if="user.isNew">-</span>
              <span v-else>{{ user.blocked ? 'Заблокирован' : 'OK' }}</span>
            </td>

            <td>
              {{ user.blockTime || '-' }}
            </td>

            <td>
              <input v-model="user.login" class="input" />
            </td>

            <td>
              <button class="refresh-pass-btn" @click="openPasswordModal(user)">
                <img src="../../assets/img/refresh.png" width="20">
              </button>
            </td>

            <td>
              <input v-model="user.email" class="input" />
            </td>

            <td class="actions">

              <!-- SAVE -->
              <button class="btn save" @click="saveUser(user)">
                <img src="../../assets/img/save.png" alt="save">
              </button>

              <!-- BLOCK -->
              <button 
                class="btn lock"
                :class="{ active: user.blocked }"
                @click="toggleBlock(user)"
              >
                <img 
                  :src="user.blocked ? unlockIcon : lockIcon"
                  alt="lock"
                >
              </button>

              <!-- DELETE -->
              <button class="btn delete" @click="confirmDelete(user)">
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
      </div>

    </div>

    <!-- PASSWORD MODAL -->
    <div v-if="showPasswordModal" class="modal">
      <div class="modal-content">
        <button class="close-btn" @click="closePasswordModal">
            ✖
        </button>
        <p style="color: #3B66F4">Введите новый пароль</p>
        <input v-model="newPassword" class="form-input" />

        <button class="save-half" @click="savePassword">
          Сохранить
        </button>
      </div>
    </div>

    <!-- DELETE MODAL -->
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
import { ref } from 'vue'
import lockIcon from '../../assets/img/lock.png'
import unlockIcon from '../../assets/img/unlock.png'

const users = ref([
  {
    id: 1,
    name: 'Иванов Иван Иванович',
    login: 'ivan',
    email: 'ivan@mail.com',
    blocked: false,
    blockTime: ''
  }
])

const addUser = () => {
  users.value.push({
    id: Date.now(),
    name: '',
    login: '',
    email: '',
    blocked: false,
    blockTime: '',
    isNew: true 
  })
}

const saveUser = (user) => {
  console.log('Сохранение:', user)

  if (user.isNew) {
    user.isNew = false 
  }
}

const closePasswordModal = () => {
  showPasswordModal.value = false
  newPassword.value = ''
}

const showPasswordModal = ref(false)
const showDeleteModal = ref(false)

const selectedUser = ref(null)
const newPassword = ref('')

const openPasswordModal = (user) => {
  selectedUser.value = user
  showPasswordModal.value = true
}

const savePassword = () => {
  console.log('Новый пароль:', newPassword.value)
  showPasswordModal.value = false
  newPassword.value = ''
}

const toggleBlock = (user) => {
  user.blocked = !user.blocked
  user.blockTime = user.blocked ? '12 часов' : ''
}


const confirmDelete = (user) => {
  selectedUser.value = user
  showDeleteModal.value = true
}

const deleteUser = () => {
  users.value = users.value.filter(u => u !== selectedUser.value)
  showDeleteModal.value = false
}
</script>

