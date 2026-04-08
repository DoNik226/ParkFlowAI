<template>
  <!-- Контейнер страницы с голубым фоном -->
  <div class="login-container">
    <!-- Заголовок с названием системы -->
    <div class="login-header">
      <h1>ParkFlow AI</h1>
      <h2>Авторизация</h2>
    </div>
    
    <!-- Белая карточка с формой -->
    <div class="login-card">
      <form @submit.prevent="handleLogin">
        <!-- Поле ввода логина -->
        <div class="form-group">
          <label for="username" class="form-label">Логин</label>
          <input 
            type="text" 
            id="username" 
            v-model="form.username" 
            class="form-input"
            placeholder="Введите логин" 
            required
          />
        </div>

        <!-- Поле ввода пароля -->
        <div class="form-group">
          <label for="password" class="form-label">Пароль</label>
          <input 
            type="password" 
            id="password" 
            v-model="form.password" 
            class="form-input"
            placeholder="Введите пароль" 
            required
          />
        </div>

        <!-- Сообщение об ошибке (показывается только если есть ошибка) -->
        <div v-if="errorMessage" class="alert alert-danger">
          {{ errorMessage }}
        </div>

        <!-- Сообщение об успехе (показывается только если есть сообщение об успехе) -->
        <div v-if="successMessage" class="alert alert-success">
          {{ successMessage }}
        </div>

        <!-- Кнопка восстановления пароля -->
        <div class="button-group">
          <button type="button" class="btn-forgot" @click="handleForgotPassword">
            Забыл пароль
          </button>
        </div>
      </form>
    </div>
    
    <!-- Кнопка входа (отдельно под карточкой) -->
    <div class="login-button-container">
      <button type="button" class="btn-login" @click="handleLogin" :disabled="isLoading">
        {{ isLoading ? 'Вход...' : 'Войти' }}
      </button>
    </div>
  </div>
</template>

<script>
import { authService } from '@/services/auth'

export default {
  name: 'LoginView',
  data() {
    return {
      // Данные формы
      form: {
        username: '',
        password: ''
      },
      // Флаг загрузки (блокировка кнопки во время запроса)
      isLoading: false,
      // Текст ошибки для отображения
      errorMessage: '',
      // Текст успешного сообщения
      successMessage: ''
    }
  },
  methods: {
    // Обработка входа в систему
    async handleLogin() {
      this.isLoading = true
      this.errorMessage = ''
      this.successMessage = '' // Очищаем сообщение об успехе при входе

      try {
        // Запрос к API авторизации
        const data = await authService.login(this.form.username, this.form.password)
        
        // Сохранение токена и роли в localStorage
        localStorage.setItem('access_token', data.token)
        localStorage.setItem('user_role', data.role)

        // Перенаправление в зависимости от роли
        if (data.role === 'admin') {
          this.$router.push('/admin')
        } else {
          this.$router.push('/main')
        }
      } catch (error) {
        // Обработка ошибок от сервера
        if (error.response?.status === 403) {
          this.errorMessage = 'Аккаунт заблокирован из-за множественных попыток входа.'
        } else if (error.response?.status === 401) {
          this.errorMessage = 'Неверный логин или пароль.'
        } else {
          this.errorMessage = 'Ошибка сервера. Попробуйте позже.'
        }
      } finally {
        this.isLoading = false
      }
    },

    // Обработка запроса на восстановление пароля
    async handleForgotPassword() {
      // Очищаем предыдущие сообщения
      this.errorMessage = ''
      this.successMessage = ''
      
      if (!this.form.username) {
        this.errorMessage = 'Введите логин для восстановления пароля.'
        return
      }
      
      try {
        await authService.forgotPassword(this.form.username)
        // Показываем зеленое сообщение об успехе
        this.successMessage = 'Заявка отправлена администратору'
        
        // Опционально: очистить сообщение через 5 секунд
        setTimeout(() => {
          this.successMessage = ''
        }, 5000)
      } catch (error) {
        this.errorMessage = 'Ошибка при запросе сброса пароля.'
      }
    }
  }
}
</script>

<style scoped>
/* Голубой фон на всю страницу */
.login-container {
  min-height: 100vh;
  background-color: #4A90E2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  padding-top: 60px;
}

/* Заголовок системы */
.login-header {
  text-align: center;
  margin-bottom: 40px;
  color: white;
}

.login-header h1 {
  font-size: 32px;
  font-weight: 500;
  margin: 0 0 15px 0;
  letter-spacing: 0.5px;
}

.login-header h2 {
  font-size: 24px;
  font-weight: 400;
  margin: 0;
  opacity: 0.95;
}

/* Белая карточка формы */
.login-card {
  background: white;
  padding: 40px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  width: 90%;
  max-width: 400px;
}

/* Группа полей формы */
.form-group {
  margin-bottom: 25px;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  color: #333;
  font-size: 18px;
  font-weight: 400;
}

/* Поля ввода с подчеркиванием */
.form-input {
  width: 100%;
  padding: 12px 0;
  border: none;
  border-bottom: 1px solid #ddd;
  font-size: 16px;
  outline: none;
  transition: border-color 0.3s;
}

.form-input:focus {
  border-bottom-color: #4A90E2;
}

.form-input::placeholder {
  color: #999;
}

/* Кнопка восстановления пароля */
.button-group {
  display: flex;
  justify-content: center;
  margin-top: 10px;
}

.btn-forgot {
  background-color: white;
  color: #1E3A8A;
  border: none;
  padding: 10px 30px;
  border-radius: 4px;
  font-size: 15px;
  cursor: pointer;
}

/* Контейнер кнопки входа */
.login-button-container {
  margin-top: -20px;
}

/* Кнопка входа (темно-синяя) */
.btn-login {
  background-color: #1E3A8A;
  color: white;
  border: none;
  padding: 12px 50px;
  border-radius: 4px;
  font-size: 16px;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(30, 58, 138, 0.4);
}

/* Кнопка входа когда отключена */
.btn-login:disabled {
  background-color: #6B7280;
  cursor: not-allowed;
}

/* Сообщение об ошибке */
.alert {
  padding: 12px;
  border-radius: 4px;
  margin-bottom: 20px;
  font-size: 14px;
}

.alert-danger {
  background-color: #fee;
  color: #c33;
  border: 1px solid #fcc;
}

/* Зеленое сообщение об успехе */
.alert-success {
  background-color: #e8f5e9;
  color: #2e7d32;
  border: 1px solid #c8e6c9;
}
</style>