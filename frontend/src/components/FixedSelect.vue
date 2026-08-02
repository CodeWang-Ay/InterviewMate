<script setup>
import { onBeforeUnmount, ref } from 'vue'

const props = defineProps({ modelValue: { type: String, default: '' }, options: { type: Array, default: () => [] }, placeholder: { type: String, default: '' }, disabled: { type: Boolean, default: false } })
const emit = defineEmits(['update:modelValue', 'change'])
const open = ref(false)
const root = ref(null)
const label = () => {
  const item = props.options.find(option => (typeof option === 'string' ? option : option.value) === props.modelValue)
  return item ? (typeof item === 'string' ? item : item.label) : props.placeholder
}
function choose(item) { if (props.disabled) return; const value = typeof item === 'string' ? item : item.value; emit('update:modelValue', value); emit('change', value); open.value = false }
function outside(event) { if (!root.value?.contains(event.target)) open.value = false }
document.addEventListener('click', outside)
onBeforeUnmount(() => document.removeEventListener('click', outside))
</script>
<template>
  <div ref="root" class="fixed-select">
    <button type="button" class="fixed-select-trigger" :disabled="disabled" @click.stop="open = !open"><span class="truncate">{{ label() }}</span><i class="fa fa-angle-down text-gray-400"></i></button>
    <div v-if="open" class="fixed-select-menu">
      <button v-for="item in options" :key="typeof item === 'string' ? item : item.value" type="button" class="fixed-select-option" :class="((typeof item === 'string' ? item : item.value) === modelValue) ? 'selected' : ''" @click="choose(item)"><i v-if="((typeof item === 'string' ? item : item.value) === modelValue)" class="fa fa-check"></i><span v-else class="w-3"></span>{{ typeof item === 'string' ? item : item.label }}</button>
    </div>
  </div>
</template>
<style scoped>
.fixed-select{position:relative;width:100%}.fixed-select-trigger{display:flex;height:40px;width:100%;align-items:center;justify-content:space-between;gap:8px;border:1px solid #d9e1ee;border-radius:8px;background:#fff;padding:0 12px;font-size:14px;text-align:left}.fixed-select-trigger:hover{border-color:#9db8ed}.fixed-select-menu{position:absolute;left:0;top:44px;z-index:80;width:100%;max-height:240px;overflow:auto;border:1px solid #d9e1ee;border-radius:10px;background:#fff;padding:5px;box-shadow:0 12px 30px rgba(15,35,80,.16)}.fixed-select-option{display:flex;width:100%;align-items:center;gap:8px;border-radius:7px;padding:8px 9px;text-align:left;font-size:14px;color:#344054}.fixed-select-option:hover,.fixed-select-option.selected{background:#edf4ff;color:#2f6df6}.fixed-select-option.selected{font-weight:600}
.fixed-select-trigger:disabled{cursor:not-allowed;background:#f5f7fa;color:#98a2b3;opacity:.85}
</style>
