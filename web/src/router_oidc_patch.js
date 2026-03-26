/**
 * 路由配置 OIDC 集成补丁
 *
 * 使用方法：
 * 在 web/src/router/index.js 中添加以下路由：
 *
 * ```javascript
 * {
 *   path: '/auth/oidc/callback',
 *   name: 'OIDCCallback',
 *   component: () => import('@/views/OIDCCallbackView.vue'),
 *   meta: { public: true }
 * }
 * ```
 *
 * 确保该路由标记为 public，这样未登录用户也可以访问。
 *
 * 完整示例：
 *
 * ```javascript
 * import { createRouter, createWebHistory } from 'vue-router'
 * import HomeView from '@/views/HomeView.vue'
 * import LoginView from '@/views/LoginView.vue'
 * import OIDCCallbackView from '@/views/OIDCCallbackView.vue'  // 新增
 *
 * const routes = [
 *   {
 *     path: '/',
 *     name: 'home',
 *     component: HomeView
 *   },
 *   {
 *     path: '/login',
 *     name: 'login',
 *     component: LoginView,
 *     meta: { public: true }
 *   },
 *   {
 *     path: '/auth/oidc/callback',  // 新增
 *     name: 'OIDCCallback',
 *     component: OIDCCallbackView,
 *     meta: { public: true }
 *   },
 *   // ... 其他路由
 * ]
 *
 * const router = createRouter({
 *   history: createWebHistory(),
 *   routes
 * })
 *
 * // 路由守卫
 * router.beforeEach((to, from, next) => {
 *   const userStore = useUserStore()
 *
 *   // 允许访问公开页面
 *   if (to.meta.public) {
 *     next()
 *     return
 *   }
 *
 *   // 检查登录状态
 *   if (!userStore.isLoggedIn) {
 *     next('/login')
 *     return
 *   }
 *
 *   next()
 * })
 *
 * export default router
 * ```
 */
