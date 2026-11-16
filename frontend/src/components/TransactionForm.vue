<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { shanghaiDate } from '../utils/date.js'
import { validateTransaction } from '../utils/validation.js'
import { transactionPayload } from '../utils/filters.js'
import AppIcon from './AppIcon.vue'

const props = defineProps({ record: { type: Object, default: null }, saving: Boolean, locked: Boolean, serverErrors: { type: Object, default: () => ({}) } })
const emit = defineEmits(['submit', 'cancel'])
const form = reactive({ amount: '', type: 'expense', category: '', note: '', transaction_date: shanghaiDate() })
const localErrors = ref({})
const errors = computed(() => ({ ...props.serverErrors, ...localErrors.value }))
const categories = computed(() => form.type === 'income'
  ? ['工资', '奖金', '兼职', '理财', '其他']
  : ['餐饮', '交通', '购物', '居住', '医疗', '娱乐', '其他'])
// Reset category only for an explicit user type change, never during edit hydration.
function selectType(type) {
  if (type === form.type) return
  form.type = type
  form.category = ''
  localErrors.value = {}
}
watch(() => props.record, (record) => {
  if (record) Object.assign(form, transactionPayload(record))
  else reset()
  localErrors.value = {}
}, { immediate: true })
function submit() {
  if (props.saving || props.locked) return
  const result = validateTransaction(form)
  localErrors.value = result.errors
  if (result.value) emit('submit', result.value)
}
function reset() {
  Object.assign(form, { amount: '', category: '', note: '', transaction_date: shanghaiDate() })
  localErrors.value = {}
}
defineExpose({ reset })
</script>

<template>
  <section class="panel entry-panel" aria-labelledby="entry-title">
    <div class="panel-heading"><span class="section-icon"><AppIcon :name="record ? 'edit' : 'plus'" /></span><div><h2 id="entry-title">{{ record ? '编辑记录' : '记一笔' }}</h2><p>{{ record ? `正在编辑第 ${record.id} 笔记录` : '把今天的收支，认真记下来' }}</p></div></div>
    <form novalidate @submit.prevent="submit">
      <fieldset :disabled="saving || locked" class="form-fields">
        <legend class="sr-only">{{ record ? '编辑收支记录' : '新增收支记录' }}</legend>
        <div class="type-picker" role="group" aria-label="收支类型">
          <button type="button" :class="{ active: form.type === 'expense' }" :aria-pressed="form.type === 'expense'" @click="selectType('expense')"><AppIcon name="arrowOut" />支出</button>
          <button type="button" :class="{ active: form.type === 'income' }" :aria-pressed="form.type === 'income'" @click="selectType('income')"><AppIcon name="arrowIn" />收入</button>
        </div>
        <label class="field-label" for="amount">金额 <span>必填</span></label>
        <div class="amount-input" :class="{ invalid: errors.amount }"><span>¥</span><input id="amount" v-model="form.amount" type="text" inputmode="decimal" autocomplete="off" placeholder="0.00" :aria-invalid="Boolean(errors.amount)" :aria-describedby="errors.amount ? 'amount-error' : undefined" /></div>
        <p v-if="errors.amount" id="amount-error" class="field-error">{{ errors.amount }}</p>
        <div class="form-row">
          <div class="form-field"><label class="field-label" for="category">分类 <span>必填</span></label><input id="category" v-model="form.category" list="category-options" placeholder="选择或输入分类" autocomplete="off" :aria-invalid="Boolean(errors.category)" :aria-describedby="errors.category ? 'category-error' : undefined" /><datalist id="category-options"><option v-for="category in categories" :key="category" :value="category" /></datalist><p v-if="errors.category" id="category-error" class="field-error">{{ errors.category }}</p></div>
          <div class="form-field"><label class="field-label" for="transaction-date">记账日期</label><input id="transaction-date" v-model="form.transaction_date" type="date" min="1000-01-01" max="9999-12-31" :aria-invalid="Boolean(errors.transaction_date)" :aria-describedby="errors.transaction_date ? 'date-error' : undefined" /><p v-if="errors.transaction_date" id="date-error" class="field-error">{{ errors.transaction_date }}</p></div>
        </div>
        <label class="field-label" for="note">备注 <span>选填</span></label><textarea id="note" v-model="form.note" rows="3" placeholder="这一笔，用在了哪里？" :aria-invalid="Boolean(errors.note)" :aria-describedby="errors.note ? 'note-error' : undefined" /><p v-if="errors.note" id="note-error" class="field-error">{{ errors.note }}</p>
      </fieldset>
      <button class="primary-button save-button" type="submit" :disabled="saving || locked"><span v-if="saving" class="spinner" /><AppIcon v-else :name="record ? 'check' : 'plus'" />{{ saving ? '正在保存…' : locked ? '请先刷新核对记录' : record ? '保存修改' : '保存这一笔' }}</button>
      <button v-if="record" class="cancel-edit-button" type="button" :disabled="saving" @click="emit('cancel')">取消编辑</button>
      <p class="form-footnote">小小的记录，让每一笔都清楚。</p>
    </form>
  </section>
</template>
