<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { init, use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { SVGRenderer } from 'echarts/renderers'
import { balanceTrendOption, buildBalanceTrend } from '../utils/trend.js'
import { formatMoney } from '../utils/money.js'
import AppIcon from './AppIcon.vue'

use([LineChart, GridComponent, TooltipComponent, SVGRenderer])
const props = defineProps({ records: { type: Object, default: null }, summary: { type: Object, default: null }, stale: Boolean, filtered: Boolean })
const points = computed(() => buildBalanceTrend(props.records?.items || []))
const rangeLabel = computed(() => points.value.length ? `${points.value[0].date} — ${points.value.at(-1).date}` : '暂无日期范围')
const container = ref(null)
let chart
let observer
let disposed = false

async function draw() {
  await nextTick()
  if (disposed) return
  if (!container.value || !points.value.length) {
    observer?.disconnect()
    chart?.dispose()
    chart = null
    return
  }
  if (!chart) {
    chart = init(container.value, null, { renderer: 'svg' })
    observer = new ResizeObserver(() => chart?.resize())
    observer.observe(container.value)
  }
  chart.setOption(balanceTrendOption(points.value), { notMerge: true })
  chart.resize()
}
watch(() => props.records, draw, { flush: 'post' })
onMounted(draw)
onBeforeUnmount(() => { disposed = true; observer?.disconnect(); chart?.dispose() })
</script>

<template>
  <section class="panel trend-panel" aria-labelledby="trend-title">
    <div class="trend-heading"><div><h2 id="trend-title">结余走势</h2><p>{{ stale ? '当前为上次同步结果' : filtered ? '当前筛选范围 · 按记账日期累计' : '全部记录 · 按记账日期累计' }}</p></div><span class="chart-unit">CNY</span></div>
    <div class="trend-summary"><div><span class="trend-balance-label">累计结余</span><p class="trend-balance">{{ summary ? `¥${formatMoney(summary.balance)}` : '—' }}</p></div><span class="trend-series-label"><i />累计结余</span></div>
    <div v-if="!records" class="chart-empty"><AppIcon name="chart" /><span>{{ stale ? '账本暂未同步，请重新同步。' : '正在等待收支记录。' }}</span></div>
    <div v-else-if="!points.length" class="chart-empty"><AppIcon name="chart" /><strong>暂无收支走势</strong><span>{{ filtered ? '当前筛选范围内没有记录' : '记下第一笔，开始看见收支的变化' }}</span></div>
    <template v-else><div ref="container" class="balance-trend" role="img" :aria-label="`累计结余走势图，${rangeLabel}，详细日期与金额见下方走势数据`" /><details class="trend-data"><summary>查看走势数据 <span>{{ rangeLabel }}</span></summary><ul aria-label="按日期累计结余"><li v-for="point in points" :key="point.date"><span>{{ point.date }}</span><strong>¥{{ formatMoney(point.exactAmount) }}</strong></li></ul></details></template>
    <p class="trend-footnote">以 0 为起点，仅累计当前范围内的收支。</p>
  </section>
</template>
