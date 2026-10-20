<script setup lang="ts">
import type { RecoverySummary } from '@/api/types'
defineProps<{ summary: RecoverySummary }>()
const labels: Record<string, string> = { good: '恢复良好', attention: '需要留意', insufficient: '恢复不足', rest: '建议休息', stop: '停止相关动作' }
</script>

<template>
  <article class="panel recovery-panel"><div class="panel-head"><div><p class="eyebrow">RECOVERY</p><h3>恢复状态</h3></div></div>
    <div class="recovery-status-grid"><section><span>今日</span><b>{{ summary.today ? labels[summary.today.status] || summary.today.status : '未打卡' }}</b><p>{{ summary.today?.message || '完成训练后记录酸痛、睡眠和精神状态。' }}</p></section><section><span>本周</span><b>{{ summary.week ? labels[summary.week.status] || summary.week.status : '暂无数据' }}</b><p>{{ summary.week?.message || '本周恢复信息会在这里汇总。' }}</p></section></div>
  </article>
</template>
