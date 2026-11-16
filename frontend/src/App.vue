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
const filtered = computed(() => Object.keys(state.snapshot?.filters || {}).length > 0)
const today = new Intl.DateTimeFormat('zh-CN', { timeZone: 'Asia/Shanghai', year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' }).format(new Date())
const syncLabel = computed(() => state.loading ? '同步中' : state.error ? '暂未同步' : state.lastSynced ? '已同步' : '等待同步')
async function save(payload) {
  if (await ledger.save(payload)) form.value?.reset()
}
async function edit(record) {
  if (ledger.startEdit(record)) {
    await nextTick()
    document.querySelector('#entry-title')?.scrollIntoView({ block: 'center', behavior: 'smooth' })
    document.querySelector('#amount')?.focus({ preventScroll: true })
  }
}
onMounted(() => ledger.refresh())
onBeforeUnmount(ledger.dispose)
</script>

<template>
  <div class="app-layout">
    <aside class="sidebar"><a class="brand" href="#overview" aria-label="一笔，返回总览"><span class="brand-mark"><AppIcon name="book" /></span><span>一笔<small>YIBI · PERSONAL LEDGER</small></span></a><div class="sidebar-rule" /><p class="nav-label">我的空间</p><a class="nav-item active" href="#overview" aria-current="page"><AppIcon name="grid" />收支总览<span class="nav-dot" /></a><div class="sidebar-note"><AppIcon name="leaf" /><p>记下每一笔<br />慢慢，过好每一天。</p><span>YOUR MONEY, YOUR PACE.</span></div><div class="sidebar-bottom"><span class="user-avatar">我</span><div><strong>我的个人账本</strong><small>一点记录，一份从容</small></div></div></aside>
    <main id="overview" class="main-content">
      <header class="topbar"><div class="breadcrumb">我的空间 <span>/</span><strong>收支总览</strong></div><span class="today"><AppIcon name="calendar" />{{ today }}</span></header>
      <section class="page-intro"><div><p class="eyebrow">A LITTLE CLARITY, EVERY DAY</p><h1>把日子，记得清楚一点。</h1><p class="intro-description">从一笔收支开始，让生活更有数。</p></div><button class="secondary-button" :disabled="state.loading || state.submitting" @click="ledger.refresh()"><AppIcon name="refresh" :class="{ rotating: state.loading }" />{{ state.loading ? '正在同步' : '重新同步' }}</button></section>
      <div v-if="state.notice" class="notice" :class="state.notice.tone" role="status"><AppIcon :name="state.notice.tone === 'success' ? 'check' : 'warning'" /><span>{{ state.notice.message }}</span><button v-if="state.uncertainWrite" type="button" :disabled="state.loading" @click="ledger.refresh()">刷新核对</button></div>
      <div v-if="state.error" class="notice error" role="alert"><AppIcon name="warning" /><span>{{ state.error }}{{ state.snapshot ? ' 当前展示上次成功同步的结果。' : ' 暂未取得收支数据。' }}</span></div>
      <FilterBar :busy="state.submitting" :filters="state.filters" @apply="ledger.refresh" />
      <p v-if="state.loading && state.snapshot" class="snapshot-hint">正在同步，当前暂展示上次成功读取的完整结果。</p>
      <SummaryCards :summary="state.snapshot?.summary" :loading="state.loading" :stale="Boolean(state.error && state.snapshot)" />
      <div class="section-divider"><span>你的日常账本</span><div /><span class="sync-status" :class="{ offline: Boolean(state.error) }"><i />{{ syncLabel }}</span></div>
      <div class="workspace-grid"><TransactionForm ref="form" :record="state.editing" :saving="state.submitting" :locked="state.uncertainWrite" :server-errors="state.fieldErrors" @submit="save" @cancel="ledger.cancelEdit" /><div class="ledger-right-column"><TransactionList :records="state.snapshot?.records" :loading="state.loading" :failed="Boolean(state.error)" :filtered="filtered" :locked="state.submitting || state.uncertainWrite" :editing-id="state.editing?.id" @edit="edit" @delete="ledger.requestDelete" /><ExpenseChart :summary="state.snapshot?.summary" :stale="Boolean(state.error)" :filtered="filtered" /></div></div>
      <DeleteDialog :record="state.deleteTarget" :busy="state.submitting || state.loading" :locked="state.uncertainWrite" :error="state.deleteError" @confirm="ledger.confirmDelete" @cancel="ledger.cancelDelete" @refresh="ledger.refresh()" />
      <footer class="page-footer"><span>一笔 · 认真记下日常</span><span>数据以最近一次成功同步为准</span></footer>
    </main>
  </div>
</template>
