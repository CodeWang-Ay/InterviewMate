<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const toast = ref({ visible: false, type: 'info', message: '', duration: 4200, nonce: 0 })
const confirmation = ref({
  visible: false,
  title: '请确认操作',
  message: '',
  confirmText: '确认',
  cancelText: '取消',
  tone: 'danger',
})

let toastTimer = null
let confirmResolver = null
let nativeAlert = null

const toastTheme = computed(() => ({
  success: {
    shell: 'border-emerald-200/80 bg-[linear-gradient(135deg,#ecfdf5_0%,#f0fdfa_100%)] text-emerald-950',
    icon: 'bg-emerald-500 text-white',
    symbol: 'fa-check',
    title: '操作成功',
  },
  warning: {
    shell: 'border-amber-200/90 bg-[linear-gradient(135deg,#fff7ed_0%,#fff1f2_100%)] text-amber-950',
    icon: 'bg-[linear-gradient(135deg,#f59e0b,#f97316)] text-white',
    symbol: 'fa-exclamation',
    title: '请注意',
  },
  error: {
    shell: 'border-rose-200/90 bg-[linear-gradient(135deg,#fff1f2_0%,#fff7ed_100%)] text-rose-950',
    icon: 'bg-[linear-gradient(135deg,#f43f5e,#ef4444)] text-white',
    symbol: 'fa-times',
    title: '操作未完成',
  },
  info: {
    shell: 'border-blue-200/90 bg-[linear-gradient(135deg,#eff6ff_0%,#eef2ff_100%)] text-blue-950',
    icon: 'bg-[linear-gradient(135deg,#3b82f6,#6366f1)] text-white',
    symbol: 'fa-info',
    title: '提示',
  },
}[toast.value.type] || {}))

const confirmTheme = computed(() => confirmation.value.tone === 'danger'
  ? {
      icon: 'bg-[linear-gradient(135deg,#fff1f2,#ffedd5)] text-rose-600',
      button: 'bg-[linear-gradient(135deg,#f43f5e,#ef4444)] text-white shadow-rose-200 hover:shadow-rose-300',
      symbol: 'fa-trash-o',
    }
  : {
      icon: 'bg-[linear-gradient(135deg,#eff6ff,#eef2ff)] text-[#4776ff]',
      button: 'bg-[linear-gradient(135deg,#4776ff,#6366f1)] text-white shadow-blue-200 hover:shadow-blue-300',
      symbol: 'fa-question',
    })

function inferType(message) {
  const text = String(message || '')
  if (/失败|错误|不能|不存在|无权限/.test(text)) return 'error'
  if (/确认|警告|额度|上限|重复/.test(text)) return 'warning'
  if (/成功|完成|已保存|已复制|已恢复/.test(text)) return 'success'
  return 'info'
}

function notify(message, type = '', duration = 4200) {
  if (toastTimer) window.clearTimeout(toastTimer)
  toast.value = {
    visible: true,
    type: type || inferType(message),
    message: String(message || '操作完成'),
    duration,
    nonce: toast.value.nonce + 1,
  }
  toastTimer = window.setTimeout(() => {
    toast.value = { ...toast.value, visible: false }
  }, duration)
}

function requestConfirm(message, options = {}) {
  if (confirmResolver) confirmResolver(false)
  confirmation.value = {
    visible: true,
    title: options.title || (/删除/.test(String(message)) ? '确认删除' : '请确认操作'),
    message: String(message || '确定继续执行此操作吗？'),
    confirmText: options.confirmText || '确认',
    cancelText: options.cancelText || '取消',
    tone: options.tone || 'danger',
  }
  return new Promise(resolve => {
    confirmResolver = resolve
  })
}

function settleConfirm(result) {
  confirmation.value = { ...confirmation.value, visible: false }
  const resolve = confirmResolver
  confirmResolver = null
  resolve?.(result)
}

function onKeydown(event) {
  if (!confirmation.value.visible) return
  if (event.key === 'Escape') settleConfirm(false)
  if (event.key === 'Enter') settleConfirm(true)
}

onMounted(() => {
  nativeAlert = window.alert
  window.appNotify = notify
  window.appConfirm = requestConfirm
  window.alert = message => notify(message)
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  if (toastTimer) window.clearTimeout(toastTimer)
  if (nativeAlert) window.alert = nativeAlert
  delete window.appNotify
  delete window.appConfirm
  window.removeEventListener('keydown', onKeydown)
  if (confirmResolver) confirmResolver(false)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="feedback-toast">
      <div
        v-if="toast.visible"
        :key="toast.nonce"
        class="fixed right-4 top-5 z-[120] w-[min(420px,calc(100vw-2rem))] overflow-hidden rounded-2xl border p-4 shadow-[0_20px_55px_rgba(15,23,42,0.18)] backdrop-blur-xl"
        :class="toastTheme.shell"
        role="status"
        aria-live="polite"
      >
        <div class="flex items-start gap-3.5">
          <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl shadow-sm" :class="toastTheme.icon">
            <i :class="['fa', toastTheme.symbol]"></i>
          </div>
          <div class="min-w-0 flex-1">
            <div class="text-sm font-black tracking-wide">{{ toastTheme.title }}</div>
            <div class="mt-1 whitespace-pre-line text-sm font-medium leading-6 opacity-80">{{ toast.message }}</div>
          </div>
          <button class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg opacity-40 transition hover:bg-white/70 hover:opacity-80" title="关闭" @click="toast.visible = false">
            <i class="fa fa-times text-xs"></i>
          </button>
        </div>
        <div class="absolute inset-x-0 bottom-0 h-1 bg-black/5">
          <div class="feedback-progress h-full bg-current opacity-35" :style="{ animationDuration: `${toast.duration}ms` }"></div>
        </div>
      </div>
    </Transition>

    <Transition name="feedback-modal">
      <div
        v-if="confirmation.visible"
        class="fixed inset-0 z-[130] flex items-center justify-center bg-[#08111f]/45 p-4 backdrop-blur-[3px]"
        role="dialog"
        aria-modal="true"
        :aria-label="confirmation.title"
        @click.self="settleConfirm(false)"
      >
        <div class="w-full max-w-[430px] overflow-hidden rounded-[24px] border border-white/80 bg-white shadow-[0_28px_90px_rgba(8,17,31,0.28)]">
          <div class="p-6 sm:p-7">
            <div class="flex items-start gap-4">
              <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl text-lg" :class="confirmTheme.icon">
                <i :class="['fa', confirmTheme.symbol]"></i>
              </div>
              <div class="min-w-0 flex-1">
                <h3 class="text-lg font-black text-[#172033]">{{ confirmation.title }}</h3>
                <p class="mt-2 whitespace-pre-line text-sm font-medium leading-6 text-[#667085]">{{ confirmation.message }}</p>
              </div>
            </div>
            <div class="mt-7 flex justify-end gap-3">
              <button class="rounded-xl border border-[#dfe5ee] bg-white px-5 py-2.5 text-sm font-bold text-[#475467] transition hover:bg-[#f8fafc]" @click="settleConfirm(false)">
                {{ confirmation.cancelText }}
              </button>
              <button class="rounded-xl px-5 py-2.5 text-sm font-bold shadow-lg transition hover:-translate-y-0.5" :class="confirmTheme.button" @click="settleConfirm(true)">
                {{ confirmation.confirmText }}
              </button>
            </div>
          </div>
          <div class="h-1.5 bg-[linear-gradient(90deg,#4776ff_0%,#11b89f_48%,#f59e0b_100%)]"></div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.feedback-toast-enter-active,
.feedback-toast-leave-active {
  transition: opacity 220ms ease, transform 260ms cubic-bezier(0.22, 1, 0.36, 1);
}
.feedback-toast-enter-from,
.feedback-toast-leave-to {
  opacity: 0;
  transform: translate3d(24px, -8px, 0) scale(0.97);
}
.feedback-modal-enter-active,
.feedback-modal-leave-active {
  transition: opacity 180ms ease;
}
.feedback-modal-enter-active > div,
.feedback-modal-leave-active > div {
  transition: transform 220ms cubic-bezier(0.22, 1, 0.36, 1);
}
.feedback-modal-enter-from,
.feedback-modal-leave-to {
  opacity: 0;
}
.feedback-modal-enter-from > div,
.feedback-modal-leave-to > div {
  transform: translateY(14px) scale(0.96);
}
.feedback-progress {
  transform-origin: left center;
  animation: feedback-countdown linear forwards;
}
@keyframes feedback-countdown {
  from { transform: scaleX(1); }
  to { transform: scaleX(0); }
}
@media (prefers-reduced-motion: reduce) {
  .feedback-toast-enter-active,
  .feedback-toast-leave-active,
  .feedback-modal-enter-active,
  .feedback-modal-leave-active,
  .feedback-modal-enter-active > div,
  .feedback-modal-leave-active > div {
    transition: opacity 120ms linear;
  }
  .feedback-progress { animation: none; }
}
</style>
