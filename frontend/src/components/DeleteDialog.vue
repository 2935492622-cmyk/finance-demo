<script setup>
import { onMounted, ref, watch } from 'vue'
import { formatMoney } from '../utils/money.js'
import AppIcon from './AppIcon.vue'

const props = defineProps({ record: { type: Object, default: null }, busy: Boolean, locked: Boolean, error: { type: String, default: '' } })
const emit = defineEmits(['confirm', 'cancel', 'refresh'])
const dialog = ref(null)
function syncDialog() {
  if (!dialog.value) return
  if (props.record && !dialog.value.open) dialog.value.showModal()
  else if (!props.record && dialog.value.open) dialog.value.close()
}
watch(() => props.record, syncDialog, { flush: 'post' })
onMounted(syncDialog)
function cancel(event) {
  event?.preventDefault()
  if (!props.busy) emit('cancel')
}
</script>

<template>
  <dialog ref="dialog" class="delete-dialog" aria-labelledby="delete-title" aria-describedby="delete-description" @cancel="cancel">
    <template v-if="record"><span class="delete-dialog-icon"><AppIcon name="trash" /></span><h2 id="delete-title">删除这笔记录？</h2><p id="delete-description">{{ record.category }} · {{ record.type === 'income' ? '收入' : '支出' }} ¥{{ formatMoney(record.amount) }}<br />删除后无法恢复，统计也会同步更新。</p><p v-if="error" class="dialog-error" role="alert">{{ error }}</p><div class="dialog-buttons"><button class="secondary-button" type="button" :disabled="busy" @click="cancel">{{ locked ? '关闭' : '取消' }}</button><button v-if="locked" class="primary-button" type="button" :disabled="busy" @click="emit('refresh')">刷新核对</button><button v-else class="danger-button" type="button" :disabled="busy" @click="emit('confirm')">{{ busy ? '正在删除…' : '确认删除' }}</button></div></template>
  </dialog>
</template>
