<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useShapingIntelligenceStore } from '@/stores/shapingIntelligence'
import { useNotice } from '@/composables/useNotice'
import type { MuscleGroup } from '@/api/types'
import FilterSelect from '@/components/ui/FilterSelect.vue'

const intelligence = useShapingIntelligenceStore()
const notice = useNotice()
const groups: MuscleGroup[] = ['胸', '背', '腿', '肩', '臂', '核心']
const goalLabels = { whole_body: '全身塑型', glutes_legs: '侧重臀腿', shoulders_back: '侧重肩背' }
const goalValue = computed({ get: () => intelligence.preferences.goal, set: (value: string) => { intelligence.preferences.goal = value as keyof typeof goalLabels } })
const goalOptions = Object.entries(goalLabels).map(([value, label]) => ({ value, label }))
function toggle(list: MuscleGroup[], group: MuscleGroup): void {
  const index = list.indexOf(group)
  if (index >= 0) list.splice(index, 1); else list.push(group)
}
async function save(): Promise<void> {
  try { const message = await intelligence.savePreferences(); await intelligence.analyze(); notice.notify(message, 'success') }
  catch (error) { notice.notify(error instanceof Error ? error.message : '设置保存失败。', 'error') }
}
async function decide(id: number, decision: 'adopted' | 'ignored'): Promise<void> {
  try { notice.notify(await intelligence.decideWeak(id, decision), 'success') }
  catch (error) { notice.notify(error instanceof Error ? error.message : '建议处理失败。', 'error') }
}
onMounted(async () => {
  try { await intelligence.loadPreferences(); await intelligence.analyze() }
  catch { /* 面板内显示错误 */ }
})
</script>

<template>
  <article class="panel shape-panel shape-intelligence-panel">
    <div class="panel-head"><div><p class="eyebrow">TARGETED TRAINING</p><h3>部位专项与薄弱覆盖</h3></div><button class="text-button" :disabled="intelligence.loading" @click="intelligence.analyze">重新分析</button></div>
    <p class="shape-muted">按最近 4 周动作组数和训练频率统计。至少积累 2 个不同训练周后才做判断；侧重和禁忌部位不会被误判为薄弱。</p>
    <div class="shape-preference-grid">
      <label class="field"><span>塑型方向</span><FilterSelect v-model="goalValue" :options="goalOptions" aria-label="塑型方向" /></label>
      <fieldset class="shape-chip-field"><legend>额外侧重部位</legend><button v-for="group in groups" :key="group" type="button" :aria-pressed="intelligence.preferences.focus_groups.includes(group)" @click="toggle(intelligence.preferences.focus_groups, group)">{{ group }}</button></fieldset>
      <fieldset class="shape-chip-field"><legend>不练 / 禁忌部位</legend><button v-for="group in groups" :key="group" type="button" :aria-pressed="intelligence.preferences.excluded_groups.includes(group)" @click="toggle(intelligence.preferences.excluded_groups, group)">{{ group }}</button></fieldset>
      <button class="button button-primary" type="button" @click="save">保存并分析</button>
    </div>
    <p v-if="intelligence.error" class="shape-error" role="alert">{{ intelligence.error }}</p>
    <div v-if="intelligence.weakAnalysis" class="muscle-analysis">
      <div class="muscle-stat-grid">
        <div v-for="row in intelligence.weakAnalysis.stats" :key="row.muscle_group" class="muscle-stat"><span>{{ row.muscle_group }}</span><strong>{{ row.total_sets }} 组</strong><small>{{ row.frequency }} 次 · {{ row.coverage_percent }}%</small></div>
      </div>
      <p class="shape-muted">{{ intelligence.weakAnalysis.message }} 已观察 {{ intelligence.weakAnalysis.observed_weeks }} 个训练周。</p>
      <div v-if="intelligence.weakAnalysis.advice.length" class="weak-advice-list">
        <article v-for="item in intelligence.weakAnalysis.advice" :key="item.id" class="weak-advice-card">
          <div><span class="tag">{{ item.muscle_group }}部</span><span class="advice-status">{{ item.status === 'pending' ? '待确认' : item.status === 'adopted' ? '已采纳' : '已忽略' }}</span></div>
          <p>{{ item.evidence }}</p><b>{{ item.exercises.map(row => row.name).join(' / ') || '当前器械条件下暂无匹配动作' }}</b>
          <p>{{ item.prescription }}</p><p>{{ item.integration }}</p>
          <div v-if="item.status === 'pending'" class="shape-actions"><button class="button button-quiet" @click="decide(item.id, 'ignored')">忽略</button><button class="button button-primary" :disabled="!item.exercises.length" @click="decide(item.id, 'adopted')">采纳并写入周计划</button></div>
        </article>
      </div>
      <p v-else class="empty-state">{{ intelligence.weakAnalysis.status === 'insufficient_data' ? '数据样本不足，继续记录训练后再分析。' : '当前没有识别到需要额外补充的部位。' }}</p>
    </div>
  </article>
</template>
