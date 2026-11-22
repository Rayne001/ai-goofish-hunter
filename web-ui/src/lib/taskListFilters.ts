export type TaskListStatusFilter = 'all' | 'enabled' | 'disabled' | 'running'
export type TaskListModeFilter = 'all' | 'ai' | 'keyword'

export interface TaskListFilters {
  query?: string
  status?: TaskListStatusFilter
  decisionMode?: TaskListModeFilter
}

interface TaskListItem {
  task_name?: string | null
  keyword?: string | null
  description?: string | null
  region?: string | null
  enabled?: boolean
  is_running?: boolean
  decision_mode?: string | null
}

export interface TaskPage<T> {
  items: T[]
  page: number
  pageCount: number
  total: number
  start: number
  end: number
}

export function filterTasks<T extends TaskListItem>(
  tasks: readonly T[],
  filters: TaskListFilters = {},
): T[] {
  const query = String(filters.query ?? '').trim().toLowerCase()
  const status = filters.status ?? 'all'
  const decisionMode = filters.decisionMode ?? 'all'

  return tasks.filter((task) => {
    if (status === 'running' && task.is_running !== true) return false
    if (status === 'enabled' && task.enabled !== true) return false
    if (status === 'disabled' && task.enabled !== false) return false

    if (decisionMode !== 'all' && (task.decision_mode || 'ai') !== decisionMode) {
      return false
    }

    if (!query) return true

    const searchableFields = [task.task_name, task.keyword, task.description, task.region]
    return searchableFields.some((field) => String(field ?? '').toLowerCase().includes(query))
  })
}

export function paginateTasks<T>(
  items: readonly T[],
  requestedPage: number,
  requestedPageSize: number,
): TaskPage<T> {
  const pageSize = Number.isFinite(requestedPageSize) && requestedPageSize > 0
    ? Math.floor(requestedPageSize)
    : 10
  const total = items.length
  const pageCount = Math.max(1, Math.ceil(total / pageSize))
  const safeRequestedPage = Number.isFinite(requestedPage) ? Math.floor(requestedPage) : 1
  const page = Math.min(Math.max(safeRequestedPage, 1), pageCount)
  const offset = (page - 1) * pageSize

  return {
    items: items.slice(offset, offset + pageSize),
    page,
    pageCount,
    total,
    start: total === 0 ? 0 : offset + 1,
    end: Math.min(offset + pageSize, total),
  }
}

export type PaginationItem = number | 'ellipsis'

export function getPageItems(currentPage: number, pageCount: number): PaginationItem[] {
  const total = Number.isFinite(pageCount) ? Math.max(0, Math.floor(pageCount)) : 0
  if (total === 0) return []

  const current = Number.isFinite(currentPage)
    ? Math.min(Math.max(Math.floor(currentPage), 1), total)
    : 1

  if (total <= 7) {
    return Array.from({ length: total }, (_, index) => index + 1)
  }
  if (current <= 3) return [1, 2, 3, 4, 'ellipsis', total]
  if (current >= total - 2) {
    return [1, 'ellipsis', total - 3, total - 2, total - 1, total]
  }
  return [1, 'ellipsis', current - 1, current, current + 1, 'ellipsis', total]
}
