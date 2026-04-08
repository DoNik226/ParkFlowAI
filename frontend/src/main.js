import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './assets/css/main.css'
import './assets/css/admin_view.css'
import './assets/css/user_manage.css'

createApp(App)
  .use(router)
  .mount('#app')