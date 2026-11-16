<script setup>
import { computed, reactive, ref } from 'vue'
import { validateFilters } from '../utils/filters.js'
import AppIcon from './AppIcon.vue'

const props = defineProps({ busy: Boolean, filters: { type: Object, default: () => ({}) } })
const emit = defineEmits(['apply'])
const draft = reactive({ type: '', category: '', start_date: '', end_date: '' })
const errors = ref({})
const active = computed(() => Object.keys(props.filters).length > 0)
function apply() {
  const result = validateFilters(draft)
  errors.value = result.errors
  if (result.value) emit('apply', result.value)
}
function clear() {
  Object.assign(draft, { type: '', category: '', start_date: '', end_date: '' })
  errors.value = {}
  emit('apply', {})
}
</script>

<template>
  <section class="panel filter-panel" aria-labelledby="filter-title">
    <div class="filter-heading"><div class="panel-heading"><AppIcon name="filter" /><h2 id="filter-title">筛选记录</h2></div><span class="filter-caption">{{ active ? '统计与图表均按当前条件展示' : '默认展示全部收支' }}</span></div>
    <form class="filter-form" novalidate @submit.prevent="apply">
      <div><label for="filter-type" class="field-label">收支类型</label><select id="filter-type" v-model="draft.type" :disabled="busy"><option value="">全部类型</option><option value="income">收入</option><option value="expense">支出</option></select><p v-if="errors.type" class="field-error">{{ errors.type }}</p></div>
      <div><label for="filter-category" class="field-label">分类</label><input id="filter-category" v-model="draft.category" placeholder="输入精确分类" :disabled="busy" /><p v-if="errors.category" class="field-error">{{ errors.category }}</p></div>
      <div><label for="filter-start" class="field-label">开始日期</label><input id="filter-start" v-model="draft.start_date" type="date" min="1000-01-01" max="9999-12-31" :disabled="busy" /><p v-if="errors.start_date" class="field-error">{{ errors.start_date }}</p></div>
      <div><label for="filter-end" class="field-label">结束日期</label><input id="filter-end" v-model="draft.end_date" type="date" min="1000-01-01" max="9999-12-31" :disabled="busy" /><p v-if="errors.end_date" class="field-error">{{ errors.end_date }}</p></div>
      <div class="filter-buttons"><button class="primary-button" type="submit" :disabled="busy">应用筛选</button><button class="secondary-button" type="button" :disabled="busy" @click="clear">清空筛选</button></div>
    </form>
  </section>
</template>
