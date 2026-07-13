import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

const nativeFetch = window.fetch.bind(window)
let handlingUnauthorized = false

function clearAuthAndRedirect() {
  if (handlingUnauthorized) return
  handlingUnauthorized = true
  try {
    window.localStorage?.removeItem('token')
    window.localStorage?.removeItem('username')
    window.localStorage?.removeItem('nickname')
    window.localStorage?.removeItem('avatar')
    window.localStorage?.removeItem('role')
    window.localStorage?.removeItem('email')
    window.localStorage?.removeItem('phone')
    window.localStorage?.removeItem('company')
    window.localStorage?.removeItem('bio')
  } catch (_) {
    // ignore storage failure
  }

  const path = window.location.pathname.startsWith('/user') ? '/user/login' : '/login'
  const redirect = encodeURIComponent(`${window.location.pathname}${window.location.search}`)
  window.location.replace(`${path}?redirect=${redirect}`)
}

window.fetch = async (input, init = {}) => {
  const request = new Request(input, init)
  const url = new URL(request.url, window.location.origin)
  const isApiRequest = url.origin === window.location.origin && url.pathname.startsWith('/api/')
  const isPublicAuth = ['/api/auth/login', '/api/auth/register', '/api/auth/candidate-login'].includes(url.pathname)

  if (!isApiRequest || isPublicAuth) {
    return nativeFetch(input, init)
  }

  const headers = new Headers(init.headers || request.headers || {})
  const isFormDataBody = typeof FormData !== 'undefined' && init.body instanceof FormData
  if (isFormDataBody) {
    headers.delete('Content-Type')
  }
  try {
    const token = window.localStorage?.getItem('token') || ''
    if (token && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${token}`)
    }
  } catch (_) {
    // ignore localStorage access failure
  }

  const response = await nativeFetch(input, { ...init, headers })
  if (response.status === 401 && url.pathname !== '/api/auth/session') {
    clearAuthAndRedirect()
  }
  return response
}

createApp(App).use(router).mount('#app')
