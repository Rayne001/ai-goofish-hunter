export interface TaskNameSource {
  task_name?: string | null
  keyword?: string | null
}

export function buildResultFilename(keyword: string | null | undefined): string {
  return `${String(keyword ?? '').replace(/ /g, '_')}_full_data.jsonl`
}

export function buildTaskNameByResultFile(tasks: readonly TaskNameSource[]): Record<string, string> {
  const taskNameByFile: Record<string, string> = {}
  for (const task of tasks) {
    if (!task.keyword) continue
    const taskName = String(task.task_name ?? '').trim()
    if (taskName) taskNameByFile[buildResultFilename(task.keyword)] = taskName
  }
  return taskNameByFile
}
