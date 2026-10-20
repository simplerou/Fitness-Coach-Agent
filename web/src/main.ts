import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './styles/tokens.css'
import './styles/main.css'
import './styles/shaping.css'
import './styles/training-intelligence.css'

createApp(App).use(createPinia()).use(router).mount('#app')
