<script setup>
import { computed, defineAsyncComponent, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import AppIcon from './components/AppIcon.vue'
import SummaryCards from './components/SummaryCards.vue'
import TransactionForm from './components/TransactionForm.vue'
import TransactionList from './components/TransactionList.vue'
import FilterBar from './components/FilterBar.vue'
import DeleteDialog from './components/DeleteDialog.vue'
import { transactionsApi } from './api/transactions.js'
import { createLedger } from './composables/ledger.js'

const ledger = createLedger(transactionsApi)
const { state } = ledger
const form = ref(null)
const ExpenseChart = defineAsyncComponent(() => import('./components/ExpenseChart.vue'))
const BalanceTrend = defineAsyncComponent(() => import('./components/BalanceTrend.vue'))
const activeSection = ref('overview')
const navigation = [
  { id: 'overview', label: '收支概览', icon: 'grid' },
  { id: 'records', label: '收支明细', icon: 'list' },
  { id: 'analysis', label: '支出分析', icon: 'chart' },
  { id: 'entry', label: '记一笔', icon: 'plus' },
]
const filtered = computed(() => Object.keys(state.snapshot?.filters || {}).length > 0)
const today = new Intl.DateTimeFormat('zh-CN', { timeZone: 'Asia/Shanghai', year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' }).format(new Date())
const syncLabel = computed(() => state.loading ? '同步中' : state.error ? '暂未同步' : state.lastSynced ? '已同步' : '等待同步')
function navigate(id) {
  activeSection.value = id
  document.getElementById(id)?.scrollIntoView({ block: 'start', behavior: 'smooth' })
  if (id === 'entry') document.querySelector('#amount')?.focus({ preventScroll: true })
}
async function save(payload) {
  if (await ledger.save(payload)) form.value?.reset()
}
async function edit(record) {
  if (ledger.startEdit(record)) {
    await nextTick()
    navigate('entry')
  }
}
onMounted(() => ledger.refresh())
onBeforeUnmount(ledger.dispose)
</script>

<template>
  <div class="app-layout">
    <aside class="sidebar">
      <a class="brand" href="#overview" aria-label="一笔，返回总览" @click.prevent="navigate('overview')"><span class="brand-mark"><AppIcon name="book" /></span><span>一笔<small>PERSONAL LEDGER</small></span></a>
      <p class="nav-label">我的账本</p>
      <nav class="sidebar-nav" aria-label="账本导航">
        <a v-for="item in navigation" :key="item.id" class="nav-item" :class="{ active: activeSection === item.id }" :href="`#${item.id}`" :aria-current="activeSection === item.id ? 'location' : undefined" @click.prevent="navigate(item.id)"><AppIcon :name="item.icon" /><span>{{ item.label }}</span><span v-if="activeSection === item.id" class="nav-dot" /></a>
      </nav>
      <div class="sidebar-note"><span class="sidebar-note-icon"><AppIcon name="leaf" /></span><p>每一笔，都有迹可循。</p><small>让日常收支，慢慢变清楚。</small></div>
      <div class="sidebar-bottom"><span class="user-avatar">我</span><div><strong>我的个人账本</strong><small>人民币 · CNY</small></div><AppIcon name="book" /></div>
    </aside>
    <main id="overview" class="main-content">
      <header class="topbar"><div class="breadcrumb">我的账本 <span>/</span><strong>收支概览</strong></div><div class="topbar-actions"><span class="sync-status" :class="{ offline: Boolean(state.error) }" role="status"><i />{{ syncLabel }}</span><button class="primary-button new-entry-button" @click="navigate('entry')"><AppIcon name="plus" />记一笔</button><span class="user-avatar topbar-avatar" aria-hidden="true">我</span></div></header>
      <section class="page-intro"><div><h1>收支概览<span class="heading-dot">.</span></h1><p class="intro-description">看清收支去向，让每一笔都有数。</p></div><span class="today"><AppIcon name="calendar" />{{ today }}</span></section>
      <div class="overview-toolbar"><nav class="view-links" aria-label="页面分区"><a href="#overview" :class="{ selected: activeSection === 'overview' }" @click.prevent="navigate('overview')">概览</a><a href="#records" :class="{ selected: activeSection === 'records' }" @click.prevent="navigate('records')">全部记录</a><a href="#analysis" :class="{ selected: activeSection === 'analysis' }" @click.prevent="navigate('analysis')">分类分析</a></nav><button class="secondary-button sync-button" :disabled="state.loading || state.submitting" @click="ledger.refresh()"><AppIcon name="refresh" :class="{ rotating: state.loading }" />{{ state.loading ? '正在同步' : '重新同步' }}</button></div>
      <div v-if="state.notice" class="notice" :class="state.notice.tone" role="status"><AppIcon :name="state.notice.tone === 'success' ? 'check' : 'warning'" /><span>{{ state.notice.message }}</span><button v-if="state.uncertainWrite" type="button" :disabled="state.loading" @click="ledger.refresh()">刷新核对</button></div>
      <div v-if="state.error" class="notice error" role="alert"><AppIcon name="warning" /><span>{{ state.error }}{{ state.snapshot ? ' 当前展示上次成功同步的结果。' : ' 暂未取得收支数据。' }}</span></div>
      <p v-if="state.loading && state.snapshot" class="snapshot-hint">正在同步，当前暂展示上次成功读取的完整结果。</p>
      <SummaryCards :summary="state.snapshot?.summary" :loading="state.loading" :stale="Boolean(state.error && state.snapshot)" />
      <FilterBar :busy="state.submitting" :filters="state.filters" @apply="ledger.refresh" />
      <div class="dashboard-grid">
        <BalanceTrend :records="state.snapshot?.records" :summary="state.snapshot?.summary" :stale="Boolean(state.error)" :filtered="filtered" />
        <ExpenseChart :summary="state.snapshot?.summary" :stale="Boolean(state.error)" :filtered="filtered" />
        <TransactionList :records="state.snapshot?.records" :loading="state.loading" :failed="Boolean(state.error)" :filtered="filtered" :locked="state.submitting || state.uncertainWrite" :editing-id="state.editing?.id" @edit="edit" @delete="ledger.requestDelete" />
        <TransactionForm ref="form" :record="state.editing" :saving="state.submitting" :locked="state.uncertainWrite" :server-errors="state.fieldErrors" @submit="save" @cancel="ledger.cancelEdit" />
      </div>
      <DeleteDialog :record="state.deleteTarget" :busy="state.submitting || state.loading" :locked="state.uncertainWrite" :error="state.deleteError" @confirm="ledger.confirmDelete" @cancel="ledger.cancelDelete" @refresh="ledger.refresh()" />
      <footer class="page-footer"><span>一笔 YIBI <span class="footer-separator">/</span> 认真记下日常</span><span>数据以最近一次成功同步为准</span></footer>
    </main>
  </div>
</template>
