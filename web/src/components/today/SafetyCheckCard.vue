<script setup lang="ts">
import { useSafetyStore } from '@/stores/safety'
import { useNotice } from '@/composables/useNotice'

const safety = useSafetyStore()
const notice = useNotice()

async function choose(noSymptoms: boolean): Promise<void> {
  try {
    await safety.submitCheck(noSymptoms)
  } catch (error) {
    notice.notify(error instanceof Error ? error.message : '请求失败，请稍后重试。', 'error')
  }
}

async function recheck(): Promise<void> {
  await safety.recheck()
  if (safety.errorMessage) notice.notify(safety.errorMessage, 'error')
}
</script>

<template>
  <article
    v-if="!safety.isRestDay"
    class="safety-check-module"
    :class="{ 'is-clear': safety.safetyStatus === 'clear', 'is-stop': safety.safetyStatus === 'stop' }"
    aria-labelledby="safety-module-title"
  >
    <div class="safety-module-copy">
      <p class="eyebrow">TODAY CHECK</p>
      <h3 id="safety-module-title">
        {{ safety.safetyStatus === 'stop' ? '今天先暂停训练' : safety.safetyStatus === 'clear' ? '今天已确认身体没有明显不适' : '训练前确认一下身体感受' }}
      </h3>
      <p>{{ safety.safetyStatus === 'stop' ? '今天不显示训练安排。若出现紧急或严重症状，请及时联系医疗服务。' : safety.safetyStatus === 'clear' ? '今天的训练安排已开放；如果身体状况变化，请重新确认。' : '如果今天有明显不适或无法判断，请暂停今天的训练建议。' }}</p>
    </div>
    <div v-if="safety.safetyStatus === 'loading'" class="safety-module-loading"><span class="loading-dot"></span>正在读取今日确认状态</div>
    <div v-else-if="safety.safetyStatus !== 'clear' && safety.safetyStatus !== 'stop'" class="safety-module-actions">
      <button class="button button-primary" type="button" :disabled="safety.submittingCheck" @click="choose(true)">今天没有明显不适</button>
      <button class="button button-quiet" type="button" :disabled="safety.submittingCheck" @click="choose(false)">有不适或无法判断</button>
    </div>
    <div v-else class="safety-module-done">
      <span class="safety-module-status">{{ safety.safetyStatus === 'stop' ? '今日训练建议已暂停' : '今日确认已完成' }}</span>
      <button v-if="safety.safetyStatus === 'clear'" class="text-button" type="button" @click="recheck">重新确认</button>
    </div>
    <p class="safety-module-note">这不是医疗筛查或诊断。若出现紧急或严重症状，请停止运动并及时联系当地急救或医疗服务。</p>
  </article>
</template>
