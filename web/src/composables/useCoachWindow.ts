import { ref } from 'vue'

const open = ref(false)
const suggestedQuestion = ref('')

export function useCoachWindow() {
  function openCoach(question = ''): void {
    suggestedQuestion.value = question
    open.value = true
  }
  function closeCoach(): void { open.value = false }
  return { open, suggestedQuestion, openCoach, closeCoach }
}
