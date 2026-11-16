<script setup>
import { formatMoney } from '../utils/money.js'
import { formatCreatedAt } from '../utils/date.js'
import AppIcon from './AppIcon.vue'
defineProps({ records: { type: Object, default: null }, loading: Boolean, failed: Boolean, filtered: Boolean, locked: Boolean, editingId: { type: Number, default: null } })
const emit = defineEmits(['edit', 'delete'])
</script>

<template>
  <section id="records" class="panel records-panel" aria-labelledby="records-title" :aria-busy="loading">
    <div class="records-heading"><div class="panel-heading"><span class="section-icon"><AppIcon name="list" /></span><div><h2 id="records-title">收支明细</h2><p>日常的点滴，都在这里</p></div></div><span class="count-badge">{{ records ? `${records.total} 笔记录` : '全部记录' }}</span></div>
    <div v-if="!records" class="list-state"><span v-if="loading" class="large-spinner spinner" /><span v-else class="empty-icon"><AppIcon :name="failed ? 'warning' : 'book'" /></span><h3>{{ loading ? '正在打开你的账本' : '账本暂时无法读取' }}</h3><p>{{ loading ? '收支记录即将呈现' : '请检查服务连接，再点击「重新同步」。' }}</p></div>
    <div v-else-if="records.items.length === 0" class="list-state"><span class="empty-icon"><AppIcon name="book" /></span><h3>{{ filtered ? '没有符合条件的记录' : '从第一笔开始' }}</h3><p v-if="filtered">试试调整筛选条件<br />或清空筛选查看全部收支。</p><p v-else>一杯咖啡，或一份收入<br />记下来，就是理清生活的开始。</p></div>
    <div v-else class="table-scroll"><table><thead><tr><th>分类 / 备注</th><th>记账日期</th><th>类型</th><th class="amount-cell">金额</th><th class="actions-heading">操作</th></tr></thead><tbody><tr v-for="item in records.items" :key="item.id" :class="{ 'editing-row': item.id === editingId }"><td><div class="record-description"><span class="record-icon" :class="item.type"><AppIcon :name="item.type === 'income' ? 'arrowIn' : 'arrowOut'" /></span><div><strong>{{ item.category }}</strong><span class="record-note">{{ item.note || '无备注' }}</span></div></div></td><td class="date-cell"><span>{{ item.transaction_date }}</span><small>录入于 {{ formatCreatedAt(item.created_at) }}</small></td><td><span class="type-badge" :class="item.type">{{ item.type === 'income' ? '收入' : '支出' }}</span></td><td class="record-amount amount-cell" :class="item.type">{{ item.type === 'income' ? '+' : '−' }}¥{{ formatMoney(item.amount) }}</td><td class="record-actions"><button type="button" :disabled="locked || loading" :aria-label="`编辑第 ${item.id} 笔记录`" @click="emit('edit', item)"><AppIcon name="edit" /><span>编辑</span></button><button type="button" class="delete-action" :disabled="locked || loading" :aria-label="`删除第 ${item.id} 笔记录`" @click="emit('delete', item)"><AppIcon name="trash" /><span>删除</span></button></td></tr></tbody></table></div>
    <div v-if="records" class="records-footer"><span class="tiny-dot" />{{ failed ? '当前为上次同步结果，请重新同步' : filtered ? '已显示当前筛选下的全部记录' : '已显示全部收支记录' }}<span class="currency-label">人民币 CNY</span></div>
    <p v-if="records?.items.length" class="table-scroll-hint">左右滑动可查看完整明细与操作</p>
  </section>
</template>
