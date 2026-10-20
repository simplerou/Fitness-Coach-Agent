<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDietStore } from '@/stores/diet'
import { useNotice } from '@/composables/useNotice'
import DietPlanner from '@/components/diet/DietPlanner.vue'
import DietPlanResult from '@/components/diet/DietPlanResult.vue'
import DietIntake from '@/components/diet/DietIntake.vue'

const diet = useDietStore()
const notice = useNotice()
const router = useRouter()
const consent = ref(false)
onMounted(async () => {
  try { await diet.loadAll() }
  catch (error) { notice.notify(error instanceof Error ? error.message : '饮食记录暂时无法读取。', 'error') }
})
async function generate(): Promise<void> {
  try { notice.notify(await diet.generatePlan(consent.value), 'success') }
  catch (error) { notice.notify(error instanceof Error ? error.message : '暂时无法生成饮食规划。', 'error') }
}
</script>

<template>
  <section class="page active">
    <div class="section-heading"><div><p class="eyebrow">FOOD & WATER</p><h2>吃得有记录</h2></div><span class="tag">按天回顾</span></div>
    <DietPlanner v-model:consent="consent" @generate="generate" />
    <DietPlanResult @generate="generate" @open-profile="router.push({ name: 'profile' })" />
    <DietIntake />
  </section>
</template>
