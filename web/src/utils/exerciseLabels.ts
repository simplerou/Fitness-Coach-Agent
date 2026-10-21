const equipmentLabels: Record<string, string> = {
  bodyweight_only: '仅自重',
  bodyweight: '自重',
  dumbbells: '哑铃',
  dumbbell: '哑铃',
  gym: '健身房常见器械',
  resistance_bands: '弹力带',
  resistance_band: '弹力带',
  barbell: '杠铃',
  cable: '绳索器械',
  machine: '固定器械',
  bench: '训练凳',
  pull_up_bar: '单杠',
  mat: '训练垫',
  none: '无器械',
}

const muscleLabels: Record<string, string> = {
  chest: '胸',
  back: '背',
  legs: '腿',
  leg: '腿',
  shoulders: '肩',
  shoulder: '肩',
  arms: '手臂',
  arm: '手臂',
  core: '核心',
  glutes: '臀部',
  quadriceps: '股四头肌',
  hamstrings: '腘绳肌',
  biceps: '肱二头肌',
  triceps: '肱三头肌',
}

const exerciseNameLabels: Record<string, string> = {
  'Pallof 抗旋转': '帕洛夫抗旋转',
  'Pallof press': '帕洛夫抗旋转推压',
  'Pallof Press': '帕洛夫抗旋转推压',
}

const containsLatinLetters = (value: string): boolean => /[A-Za-z]/.test(value)

export function equipmentLabel(value: string): string {
  return equipmentLabels[value] ?? (containsLatinLetters(value) ? '其他器械' : value)
}

export function muscleLabel(value: string): string {
  return muscleLabels[value.toLowerCase()] ?? value
}

export function exerciseNameLabel(value: string): string {
  return exerciseNameLabels[value] ?? value.replaceAll('Pallof', '帕洛夫')
}
