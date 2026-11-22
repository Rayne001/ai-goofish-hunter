<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useTasks } from '@/composables/useTasks'
import type { Task, TaskUpdate } from '@/types/task.d.ts'
import { filterTasks, getPageItems, paginateTasks, type TaskListModeFilter, type TaskListStatusFilter } from '@/lib/taskListFilters'
import { parseTaskFormDefaults } from '@/lib/taskFormQuery'
import TaskCreateDialog from '@/components/tasks/TaskCreateDialog.vue'
import TasksTable from '@/components/tasks/TasksTable.vue'
import TaskForm from '@/components/tasks/TaskForm.vue'
import { listAccounts, type AccountItem } from '@/api/accounts'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { toast } from '@/components/ui/toast'
import { ChevronLeft, ChevronRight, RotateCcw, Search, SlidersHorizontal } from 'lucide-vue-next'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
const { t } = useI18n()

const {
  tasks,
  isLoading,
  error,
  fetchTasks,
  removeTask,
  updateTask,
  startTask,
  stopTask,
  stoppingTaskIds,
} = useTasks()
const route = useRoute()
const taskQuery = ref('')
const statusFilter = ref<TaskListStatusFilter>('all')
const decisionModeFilter = ref<TaskListModeFilter>('all')
const currentPage = ref(1)
const pageSize = ref(10)

const filteredTasks = computed(() => filterTasks(tasks.value, {
  query: taskQuery.value,
  status: statusFilter.value,
  decisionMode: decisionModeFilter.value,
}))
const pageInfo = computed(() => paginateTasks(
  filteredTasks.value,
  currentPage.value,
  pageSize.value,
))
const pageItems = computed(() => getPageItems(pageInfo.value.page, pageInfo.value.pageCount))
const hasActiveFilters = computed(() => Boolean(
  taskQuery.value.trim() || statusFilter.value !== 'all' || decisionModeFilter.value !== 'all'
))

watch([taskQuery, statusFilter, decisionModeFilter, pageSize], () => {
  currentPage.value = 1
})

watch(() => pageInfo.value.pageCount, (pageCount) => {
  if (currentPage.value > pageCount) currentPage.value = pageCount
})

function clearTaskFilters() {
  taskQuery.value = ''
  statusFilter.value = 'all'
  decisionModeFilter.value = 'all'
}

function handlePageSizeChange(value: unknown) {
  const nextSize = Number(value)
  if (Number.isFinite(nextSize) && nextSize > 0) pageSize.value = nextSize
}

// State for dialogs
const isEditDialogOpen = ref(false)
const isCriteriaDialogOpen = ref(false)
const isEditSubmitting = ref(false)
const selectedTask = ref<Task | null>(null)
const criteriaTask = ref<Task | null>(null)
const criteriaDescription = ref('')
const isCriteriaSubmitting = ref(false)
const isDeleteDialogOpen = ref(false)
const taskToDeleteId = ref<number | null>(null)
const accountOptions = ref<AccountItem[]>([])

const taskToDelete = computed(() => {
  if (taskToDeleteId.value === null) return null
  return tasks.value.find((task) => task.id === taskToDeleteId.value) || null
})
const editDefaults = computed(() => parseTaskFormDefaults(route.query))

function handleDeleteTask(taskId: number) {
  taskToDeleteId.value = taskId
  isDeleteDialogOpen.value = true
}

async function handleConfirmDeleteTask() {
  if (!taskToDelete.value) {
    toast({ title: t('tasks.toasts.notFound'), variant: 'destructive' })
    isDeleteDialogOpen.value = false
    return
  }
  try {
    await removeTask(taskToDelete.value.id)
    toast({ title: t('tasks.toasts.deleted') })
  } catch (e) {
    toast({
      title: t('tasks.toasts.deleteFailed'),
      description: (e as Error).message,
      variant: 'destructive',
    })
  } finally {
    isDeleteDialogOpen.value = false
    taskToDeleteId.value = null
  }
}

function handleEditTask(task: Task) {
  selectedTask.value = task
  isEditDialogOpen.value = true
}

watch(
  () => [route.query.edit, tasks.value],
  () => {
    const editTaskId = typeof route.query.edit === 'string' ? Number(route.query.edit) : NaN
    if (!Number.isFinite(editTaskId)) return
    const match = tasks.value.find((task) => task.id === editTaskId)
    if (!match) return
    selectedTask.value = match
    isEditDialogOpen.value = true
  },
  { immediate: true }
)

async function handleUpdateTask(data: TaskUpdate) {
  if (!selectedTask.value) return
  isEditSubmitting.value = true
  try {
    await updateTask(selectedTask.value.id, data)
    isEditDialogOpen.value = false
  }
  catch (e) {
    toast({
      title: t('tasks.toasts.updateFailed'),
      description: (e as Error).message,
      variant: 'destructive',
    })
  }
  finally {
    isEditSubmitting.value = false
  }
}

function handleOpenCriteriaDialog(task: Task) {
  criteriaTask.value = task
  criteriaDescription.value = task.description || ''
  isCriteriaDialogOpen.value = true
}

async function handleRefreshCriteria() {
  if (!criteriaTask.value) return
  if (!criteriaDescription.value.trim()) {
    toast({
      title: t('tasks.toasts.descriptionRequired'),
      description: t('tasks.criteria.descriptionRequired'),
      variant: 'destructive',
    })
    return
  }

  isCriteriaSubmitting.value = true
  try {
    await updateTask(criteriaTask.value.id, { description: criteriaDescription.value })
    isCriteriaDialogOpen.value = false
  } catch (e) {
    toast({
      title: t('tasks.toasts.regenerateFailed'),
      description: (e as Error).message,
      variant: 'destructive',
    })
  } finally {
    isCriteriaSubmitting.value = false
  }
}

async function handleStartTask(taskId: number) {
  try {
    await startTask(taskId)
  } catch (e) {
    toast({
      title: t('tasks.toasts.startFailed'),
      description: (e as Error).message,
      variant: 'destructive',
    })
  }
}

async function handleStopTask(taskId: number) {
  try {
    await stopTask(taskId)
  } catch (e) {
    toast({
      title: t('tasks.toasts.stopFailed'),
      description: (e as Error).message,
      variant: 'destructive',
    })
  }
}

async function handleToggleEnabled(task: Task, enabled: boolean) {
  const previous = task.enabled
  task.enabled = enabled
  try {
    await updateTask(task.id, { enabled })
  } catch (e) {
    task.enabled = previous
    toast({
      title: t('tasks.toasts.toggleFailed'),
      description: (e as Error).message,
      variant: 'destructive',
    })
  }
}

async function fetchAccountOptions() {
  try {
    accountOptions.value = await listAccounts()
  } catch (e) {
    toast({
      title: t('tasks.toasts.loadAccountsFailed'),
      description: (e as Error).message,
      variant: 'destructive',
    })
  }
}

onMounted(fetchAccountOptions)
</script>

<template>
  <div>
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold text-gray-800">
        {{ t('tasks.title') }}
      </h1>
      <TaskCreateDialog :account-options="accountOptions" @created="fetchTasks" />
    </div>

    <!-- Edit Task Dialog -->
    <Dialog v-model:open="isEditDialogOpen">
      <DialogContent class="sm:max-w-[640px] max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{{ t('tasks.editDialog.title', { task: selectedTask?.task_name || "" }) }}</DialogTitle>
        </DialogHeader>
        <TaskForm
          v-if="selectedTask"
          mode="edit"
          :initial-data="selectedTask"
          :account-options="accountOptions"
          :default-values="editDefaults"
          @submit="(data) => handleUpdateTask(data as TaskUpdate)"
        />
        <DialogFooter>
          <Button type="submit" form="task-form" :disabled="isEditSubmitting">
            {{ isEditSubmitting ? t('common.saving') : t('tasks.editDialog.save') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Refresh Criteria Dialog -->
    <Dialog v-model:open="isCriteriaDialogOpen">
      <DialogContent class="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>{{ t('tasks.criteria.title') }}</DialogTitle>
          <DialogDescription>
            {{ t('tasks.criteria.description') }}
          </DialogDescription>
        </DialogHeader>
        <div class="grid gap-3">
          <label class="text-sm font-medium text-gray-700">{{ t('tasks.form.description') }}</label>
          <Textarea
            v-model="criteriaDescription"
            class="min-h-[140px]"
            :placeholder="t('tasks.form.descriptionPlaceholder')"
          />
        </div>
        <DialogFooter>
          <Button variant="outline" @click="isCriteriaDialogOpen = false">
            {{ t('common.cancel') }}
          </Button>
          <Button :disabled="isCriteriaSubmitting" @click="handleRefreshCriteria">
            {{ isCriteriaSubmitting ? t('tasks.criteria.generating') : t('tasks.criteria.action') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <div v-if="error" class="app-alert-error mb-4" role="alert">
      <strong class="font-bold">{{ t('common.error') }}</strong>
      <span class="block sm:inline">{{ error.message }}</span>
    </div>

    <section class="app-surface mb-6 overflow-hidden" :aria-label="t('tasks.list.ariaLabel')">
      <div class="flex flex-col gap-3 border-b border-slate-100/80 bg-white/55 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
        <div class="flex items-start gap-3">
          <div class="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
            <SlidersHorizontal class="h-4 w-4" />
          </div>
          <div class="min-w-0">
            <h2 class="text-sm font-bold text-slate-800">{{ t('tasks.list.toolbarTitle') }}</h2>
            <p class="mt-0.5 text-xs leading-5 text-slate-500">{{ t('tasks.list.toolbarDescription') }}</p>
          </div>
        </div>
        <div class="inline-flex w-fit shrink-0 items-center gap-2 rounded-full border border-slate-200/80 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 shadow-sm" aria-live="polite">
          <span class="h-1.5 w-1.5 rounded-full bg-primary/80" />
          {{ t('tasks.list.range', { start: pageInfo.start, end: pageInfo.end, total: pageInfo.total }) }}
        </div>
      </div>

      <div class="grid gap-3 p-4 sm:p-5 md:grid-cols-2 xl:grid-cols-[minmax(240px,1.45fr)_minmax(170px,1fr)_minmax(170px,1fr)]">
        <div class="grid min-w-0 gap-1.5 md:col-span-2 xl:col-span-1">
          <Label for="task-list-search" class="text-xs font-semibold text-slate-500">{{ t('tasks.list.searchLabel') }}</Label>
          <div class="relative">
            <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input
              id="task-list-search"
              v-model="taskQuery"
              type="search"
              :placeholder="t('tasks.list.searchPlaceholder')"
              :aria-label="t('tasks.list.searchPlaceholder')"
              class="h-10 rounded-xl border-slate-200/80 bg-white/85 pl-9 shadow-sm placeholder:text-slate-400 focus-visible:bg-white"
            />
          </div>
        </div>

        <div class="grid min-w-0 gap-1.5">
          <Label for="task-status-filter" class="text-xs font-semibold text-slate-500">{{ t('tasks.list.statusLabel') }}</Label>
          <Select
            :model-value="statusFilter"
            @update:model-value="(value) => statusFilter = value as TaskListStatusFilter"
          >
            <SelectTrigger id="task-status-filter" class="h-10 rounded-xl border-slate-200/80 bg-white/85 shadow-sm">
              <SelectValue :placeholder="t('tasks.list.allStatuses')" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{{ t('tasks.list.allStatuses') }}</SelectItem>
              <SelectItem value="running">{{ t('tasks.list.running') }}</SelectItem>
              <SelectItem value="enabled">{{ t('tasks.list.enabled') }}</SelectItem>
              <SelectItem value="disabled">{{ t('tasks.list.disabled') }}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div class="grid min-w-0 gap-1.5">
          <Label for="task-mode-filter" class="text-xs font-semibold text-slate-500">{{ t('tasks.list.modeLabel') }}</Label>
          <Select
            :model-value="decisionModeFilter"
            @update:model-value="(value) => decisionModeFilter = value as TaskListModeFilter"
          >
            <SelectTrigger id="task-mode-filter" class="h-10 rounded-xl border-slate-200/80 bg-white/85 shadow-sm">
              <SelectValue :placeholder="t('tasks.list.allModes')" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{{ t('tasks.list.allModes') }}</SelectItem>
              <SelectItem value="ai">{{ t('tasks.list.aiMode') }}</SelectItem>
              <SelectItem value="keyword">{{ t('tasks.list.keywordMode') }}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div class="flex flex-col gap-3 border-t border-slate-100/80 bg-slate-50/45 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-5">
        <div class="flex min-h-9 items-center gap-2">
          <span v-if="hasActiveFilters" class="inline-flex items-center rounded-full bg-primary/5 px-2.5 py-1 text-xs font-medium text-primary">
            {{ t('tasks.list.activeFilters') }}
          </span>
          <Button v-if="hasActiveFilters" size="sm" variant="ghost" class="h-8 rounded-lg px-2.5 text-slate-500" @click="clearTaskFilters">
            <RotateCcw class="h-3.5 w-3.5" />
            {{ t('tasks.list.clearFilters') }}
          </Button>
        </div>

        <div v-if="pageInfo.total > 0" class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-end">
          <div class="flex items-center gap-2">
            <Label for="task-page-size" class="whitespace-nowrap text-xs font-medium text-slate-500">{{ t('tasks.list.pageSize') }}</Label>
            <Select :model-value="String(pageSize)" @update:model-value="handlePageSizeChange">
              <SelectTrigger id="task-page-size" class="h-9 w-[76px] rounded-lg border-slate-200/80 bg-white px-2 shadow-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="5">5</SelectItem>
                <SelectItem value="10">10</SelectItem>
                <SelectItem value="20">20</SelectItem>
                <SelectItem value="50">50</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="flex items-center gap-2 sm:pl-1">
            <span class="hidden whitespace-nowrap text-xs font-medium text-slate-500 md:inline">
              {{ t('tasks.list.page', { page: pageInfo.page, pages: pageInfo.pageCount }) }}
            </span>
            <nav class="flex items-center gap-0.5 rounded-xl border border-slate-200/80 bg-white p-1 shadow-sm" :aria-label="t('tasks.list.pageNavigation')">
              <Button
                size="icon-sm"
                variant="ghost"
                class="size-8 rounded-lg text-slate-500"
                :disabled="pageInfo.page <= 1"
                :aria-label="t('tasks.list.previous')"
                @click="currentPage = pageInfo.page - 1"
              >
                <ChevronLeft class="h-4 w-4" />
              </Button>
              <template v-for="(item, index) in pageItems" :key="`page-${index}-${item}`">
                <span v-if="item === 'ellipsis'" class="min-w-5 px-1 text-center text-xs font-medium text-slate-400" aria-hidden="true">…</span>
                <Button
                  v-else
                  size="icon-sm"
                  :variant="item === pageInfo.page ? 'default' : 'ghost'"
                  :class="item === pageInfo.page ? 'size-8 rounded-lg shadow-sm' : 'size-8 rounded-lg text-slate-600'"
                  :aria-label="t('tasks.list.goToPage', { page: item })"
                  :aria-current="item === pageInfo.page ? 'page' : undefined"
                  @click="currentPage = item"
                >
                  {{ item }}
                </Button>
              </template>
              <Button
                size="icon-sm"
                variant="ghost"
                class="size-8 rounded-lg text-slate-500"
                :disabled="pageInfo.page >= pageInfo.pageCount"
                :aria-label="t('tasks.list.next')"
                @click="currentPage = pageInfo.page + 1"
              >
                <ChevronRight class="h-4 w-4" />
              </Button>
            </nav>
          </div>
        </div>
      </div>
    </section>

    <div v-if="tasks.length > 0 && filteredTasks.length === 0" class="app-surface p-8 text-center text-sm text-slate-500">
      {{ t('tasks.list.noMatches') }}
    </div>

    <TasksTable
      v-else
      :tasks="pageInfo.items"
      :is-loading="isLoading"
      :stopping-ids="stoppingTaskIds"
      @delete-task="handleDeleteTask"
      @edit-task="handleEditTask"
      @run-task="handleStartTask"
      @stop-task="handleStopTask"
      @refresh-criteria="handleOpenCriteriaDialog"
      @toggle-enabled="handleToggleEnabled"
    />

    <Dialog v-model:open="isDeleteDialogOpen">
      <DialogContent class="sm:max-w-[420px]">
        <DialogHeader>
          <DialogTitle>{{ t('tasks.deleteDialog.title') }}</DialogTitle>
          <DialogDescription>
            {{ taskToDelete ? t('tasks.deleteDialog.descriptionWithTask', { task: taskToDelete.task_name }) : t('tasks.deleteDialog.descriptionFallback') }}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" @click="isDeleteDialogOpen = false">{{ t('common.cancel') }}</Button>
          <Button variant="destructive" @click="handleConfirmDeleteTask">{{ t('tasks.deleteDialog.confirm') }}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
