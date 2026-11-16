<script setup>
import { formatMoney } from '../utils/money.js'
import AppIcon from './AppIcon.vue'
defineProps({ summary: { type: Object, default: null }, loading: Boolean, stale: Boolean })
const cards = [
  { key: 'total_income', label: '总收入', icon: 'arrowIn', theme: 'income', caption: '每一份努力，都算数' },
  { key: 'total_expense', label: '总支出', icon: 'arrowOut', theme: 'expense', caption: '生活里的每一笔花费' },
  { key: 'balance', label: '当前结余', icon: 'wallet', theme: 'balance', caption: '收入减去支出，心里有数' },
]
</script>

<template>
  <section class="summary-grid" aria-label="收支统计" :aria-busy="loading">
    <article v-for="card in cards" :key="card.key" class="summary-card" :class="card.theme">
      <div class="summary-heading"><span>{{ card.label }}</span><span class="summary-icon"><AppIcon :name="card.icon" /></span></div>
      <p class="summary-amount"><small>¥</small>{{ summary ? formatMoney(summary[card.key]) : '—' }}</p>
      <p class="summary-caption">{{ stale ? '暂未同步 · 当前为上次结果' : card.caption }}</p>
    </article>
  </section>
</template>
