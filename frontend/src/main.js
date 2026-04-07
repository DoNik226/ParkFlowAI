import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './assets/css/main.css'
import './assets/css/admin_view.css'
import './assets/css/user_manage.css'
import { registerSW } from 'virtual:pwa-register'
registerSW({ immediate: true })

createApp(App)
  .use(router)
  .mount('#app')