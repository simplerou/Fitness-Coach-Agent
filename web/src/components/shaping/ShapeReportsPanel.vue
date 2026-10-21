<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useShapingIntelligenceStore } from '@/stores/shapingIntelligence'
import { useNotice } from '@/composables/useNotice'
import TrendChart from '@/components/charts/TrendChart.vue'

const intelligence = useShapingIntelligenceStore()
const notice = useNotice()
const period = ref<'week' | 'month'>('week')
const active = computed(() => intelligence.reports.find(row => row.period_type === period.value) ?? null)
const waistTrend = computed(() => (active.value?.report.measurements.trend ?? [])
  .filter(row => row.waist_cm != null).map(row => ({ date: row.recorded_on, value: Number(row.waist_cm) })))
function formatChange(value: number | null): string { return value == null ? '样本不足' : `${value > 0 ? '+' : ''}${value.toFixed(1)}` }
function wrap(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, width: number, lineHeight: number): number {
  let line = ''; let cursor = y
  for (const char of text) {
    if (ctx.measureText(line + char).width > width) { ctx.fillText(line, x, cursor); line = char; cursor += lineHeight } else line += char
  }
  if (line) ctx.fillText(line, x, cursor)
  return cursor + lineHeight
}
function exportImage(): void {
  if (!active.value) return
  const report = active.value.report; const canvas = document.createElement('canvas'); canvas.width = 1200; canvas.height = 1500
  const ctx = canvas.getContext('2d'); if (!ctx) return
  ctx.fillStyle = '#f4f7f2'; ctx.fillRect(0, 0, canvas.width, canvas.height); ctx.fillStyle = '#fff'; ctx.fillRect(60, 55, 1080, 1390)
  ctx.fillStyle = '#173b2e'; ctx.font = 'bold 46px sans-serif'; ctx.fillText(period.value === 'week' ? '每周塑型报告' : '每月塑型报告', 110, 135)
  ctx.fillStyle = '#728078'; ctx.font = '24px sans-serif'; ctx.fillText(`${report.period_start} 至 ${report.period_end}`, 110, 182)
  let y = 255; ctx.fillStyle = '#173b2e'; ctx.font = 'bold 30px sans-serif'; ctx.fillText('训练概况', 110, y); y += 50
  ctx.font = '25px sans-serif'; y = wrap(ctx, `${report.training.training_days} 个训练日 · ${report.training.total_sets} 组 · ${report.training.total_reps} 次 · 完成率 ${report.training.completion_rate ?? '样本不足'}%`, 110, y, 960, 40)
  y += 25; ctx.font = 'bold 30px sans-serif'; ctx.fillText('身体变化', 110, y); y += 48; ctx.font = '23px sans-serif'
  for (const row of report.measurements.changes.filter(item => item.current != null).slice(0, 7)) y = wrap(ctx, `${row.label}：${row.current}，环比 ${formatChange(row.change)}（本期 ${row.measurement_count} 次）`, 110, y, 960, 38)
  y += 25; ctx.font = 'bold 30px sans-serif'; ctx.fillText('恢复与下一步', 110, y); y += 48; ctx.font = '23px sans-serif'
  y = wrap(ctx, `平均酸痛 ${report.recovery.average_soreness ?? '未记录'}，平均睡眠 ${report.recovery.average_sleep_hours ?? '未记录'} 小时，恢复不足 ${report.recovery.insufficient_days} 天。`, 110, y, 960, 38)
  for (const item of report.next_actions) y = wrap(ctx, `• ${item}`, 110, y + 8, 960, 38)
  ctx.fillStyle = '#89968e'; ctx.font = '20px sans-serif'; wrap(ctx, '数据来自用户记录的围度、体重、训练动作与恢复打卡；样本不足时不推断趋势。', 110, 1380, 960, 32)
  const link = document.createElement('a'); link.download = `塑型${period.value === 'week' ? '周报' : '月报'}-${report.period_end}.png`; link.href = canvas.toDataURL('image/png'); link.click()
}
onMounted(async () => { try { await intelligence.loadReports() } catch (error) { notice.notify(error instanceof Error ? error.message : '塑型报告暂时无法生成。', 'error') } })
</script>

<template>
  <article class="panel shape-panel shape-report-panel">
    <div class="panel-head"><div><p class="eyebrow">SHAPING REPORT</p><h3>周 / 月塑型报告</h3></div><div class="report-period-switch"><button :aria-pressed="period === 'week'" @click="period = 'week'">周报</button><button :aria-pressed="period === 'month'" @click="period = 'month'">月报</button></div></div>
    <p class="shape-muted">{{ intelligence.reportTrigger || '进入塑型页后生成最近完整周期报告。' }}</p>
    <template v-if="active">
      <div class="report-heading"><div><b>{{ active.period_start }} 至 {{ active.period_end }}</b><span>{{ active.report.sample_status === 'sufficient' ? '样本可用于周期对比' : '数据样本不足' }}</span></div><button class="button button-quiet" @click="exportImage">导出图片</button></div>
      <div class="report-summary-grid"><div><span>训练天数</span><strong>{{ active.report.training.training_days }}</strong></div><div><span>训练总量</span><strong>{{ active.report.training.total_sets }} 组</strong></div><div><span>完成率</span><strong>{{ active.report.training.completion_rate == null ? '—' : `${active.report.training.completion_rate}%` }}</strong></div><div><span>平均睡眠</span><strong>{{ active.report.recovery.average_sleep_hours == null ? '—' : `${active.report.recovery.average_sleep_hours}h` }}</strong></div></div>
      <section class="report-section"><h4>围度与体成分环比</h4><div class="report-change-grid"><div v-for="row in active.report.measurements.changes" :key="row.metric"><span>{{ row.label }}</span><b>{{ row.current == null ? '未记录' : row.current }}</b><small>{{ formatChange(row.change) }} · 本期 {{ row.measurement_count }} 次</small></div></div><p class="fine-print">{{ active.report.measurements.source }}</p></section>
      <section class="report-section"><h4>腰围趋势</h4><TrendChart :labels="waistTrend.map(item => item.date)" :series="[{ name: '腰围 cm', data: waistTrend.map(item => item.value), colorToken: '--brand' }]" :height="200" /></section>
      <section class="report-section"><h4>表现与恢复</h4><p>渐进建议 {{ active.report.performance.highlights.length }} 条；恢复打卡 {{ active.report.recovery.checkin_count }} 次；恢复不足 {{ active.report.recovery.insufficient_days }} 天。</p><ul><li v-for="item in active.report.performance.highlights" :key="`${item.exercise}-${item.reason}`"><b>{{ item.exercise }}</b>：{{ item.reason }}</li></ul><p class="fine-print">{{ active.report.recovery.source }}</p></section>
      <section class="report-section"><h4>下一周期建议</h4><ul><li v-for="item in active.report.next_actions" :key="item">{{ item }}</li></ul><div v-if="active.report.data_notes.length" class="report-data-notes"><b>数据口径提醒</b><p v-for="item in active.report.data_notes" :key="item">{{ item }}</p></div></section>
    </template>
    <p v-else class="empty-state">正在生成最近完整周期报告…</p>
  </article>
</template>
