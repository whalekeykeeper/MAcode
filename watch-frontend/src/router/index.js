import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'


const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    {
      path: '/about',
      name: 'about',
      // route level code-splitting
      // this generates a separate chunk (About.[hash].js) for this route
      // which is lazy-loaded when the route is visited.
      component: () => import('../views/AboutView.vue')
    },
      // View to display collected words, the contexts(sentences), the appear frequency, and a checkbox which could
    // be used to mark the word as learned.
    {
      path: '/wordlist',
      name: 'word list',
      component: () => import('../views/WordListView.vue')
    },
    {
      path: '/gapfilling',
      name: 'gap filling',
      component: () => import('../views/GapFillingView.vue')
    }
  ]
})


export default router
