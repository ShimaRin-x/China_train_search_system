import { createRouter, createWebHistory } from 'vue-router'

import MapWorkspace from '@/views/MapWorkspace.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'map',
      component: MapWorkspace
    }
  ]
})

export default router
