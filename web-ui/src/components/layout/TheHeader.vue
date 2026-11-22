<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button } from '@/components/ui/button'
import DashboardTaskSearch from '@/components/layout/DashboardTaskSearch.vue'
import LocaleToggle from '@/components/layout/LocaleToggle.vue'
import { 
  Zap, 
  Bell, 
  Search, 
  UserCircle,
  HelpCircle,
  Menu,
  LogOut,
} from 'lucide-vue-next'
import Badge from '@/components/ui/badge/Badge.vue'
import { useMobileNav } from '@/composables/useMobileNav'
import { useI18n } from 'vue-i18n'
import { useAuth } from '@/composables/useAuth'

const router = useRouter()
const route = useRoute()
const { toggleMobileNav } = useMobileNav()
const inactiveSearchValue = ref('')
const { t } = useI18n()

const isDashboard = computed(() => route.name === 'Dashboard')
const { username, logout } = useAuth()
const isUserMenuOpen = ref(false)
const userMenuRef = ref<HTMLElement | null>(null)

function handleDocumentClick(event: MouseEvent) {
  const target = event.target as Node | null
  if (target && !userMenuRef.value?.contains(target)) {
    isUserMenuOpen.value = false
  }
}

function handleEscape(event: KeyboardEvent) {
  if (event.key === 'Escape') isUserMenuOpen.value = false
}

async function handleLogout() {
  isUserMenuOpen.value = false
  await logout()
}

onMounted(() => {
  document.addEventListener('click', handleDocumentClick)
  document.addEventListener('keydown', handleEscape)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
  document.removeEventListener('keydown', handleEscape)
})

function goNotifications() {
  router.push({ name: 'Settings', query: { tab: 'notifications' } })
}

function goPrompts() {
  router.push({ name: 'Settings', query: { tab: 'prompts' } })
}
</script>

<template>
  <header class="flex items-center justify-between px-6 h-16 bg-white/60 backdrop-blur-md border-b border-slate-200/60 sticky top-0 z-[100]">
    <!-- Brand Logo -->
    <RouterLink
      to="/dashboard"
      class="flex items-center gap-2 group rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      :aria-label="t('header.goHome')"
    >
      <div class="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shadow-lg shadow-primary/20 transition-transform group-hover:rotate-12">
        <Zap class="w-5 h-5 text-white fill-white" />
      </div>
      <h1 class="text-lg font-black text-slate-800 tracking-tighter">
        AI <span class="text-primary">Xianyu</span> Hunter
      </h1>
      <Badge variant="outline" class="ml-2 text-[10px] font-bold border-primary/20 text-primary bg-primary/5 uppercase tracking-widest hidden sm:flex">
        PRO
      </Badge>
    </RouterLink>

    <!-- Search & Navigation -->
    <div class="hidden md:flex flex-grow max-w-md mx-8">
      <DashboardTaskSearch v-if="isDashboard" />
      <div v-else class="relative w-full group">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 transition-colors" />
        <input 
          type="text" 
          v-model="inactiveSearchValue"
          readonly
          aria-disabled="true"
          :placeholder="t('header.searchUnavailable')"
          class="w-full h-10 pl-10 pr-4 bg-slate-100/50 border border-slate-200/50 rounded-xl text-sm transition-all focus:outline-none focus:ring-2 focus:ring-primary/20 focus:bg-white focus:border-primary/50"
        />
        <kbd class="absolute right-3 top-1/2 -translate-y-1/2 px-1.5 py-0.5 rounded border border-slate-300 bg-white text-[10px] text-slate-400 font-sans shadow-sm pointer-events-none">
          /
        </kbd>
      </div>
    </div>

    <!-- Actions -->
    <div class="flex items-center gap-3">
      <div class="flex items-center gap-2">
        <LocaleToggle />
      </div>

      <div class="flex items-center gap-1 sm:gap-2">
         <Button
           variant="ghost"
           size="icon"
           class="rounded-full text-slate-500 hover:text-primary hover:bg-primary/10"
           :aria-label="t('header.openNotifications')"
           @click="goNotifications"
         >
            <Bell class="w-5 h-5" />
         </Button>
         <Button
           variant="ghost"
           size="icon"
           class="rounded-full text-slate-500 hover:text-primary hover:bg-primary/10"
           :aria-label="t('header.openPrompts')"
           @click="goPrompts"
         >
            <HelpCircle class="w-5 h-5" />
         </Button>
      </div>
      
      <div class="h-6 w-px bg-slate-200 mx-1 hidden sm:block"></div>

      <div ref="userMenuRef" class="relative">
        <Button
          variant="ghost"
          class="flex items-center gap-2 rounded-full pl-2 pr-3 hover:bg-slate-100 transition-all active:scale-95"
          :aria-label="t('header.openUserMenu')"
          :aria-expanded="isUserMenuOpen"
          aria-haspopup="menu"
          @click.stop="isUserMenuOpen = !isUserMenuOpen"
        >
          <div class="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center overflow-hidden border border-slate-300 shadow-sm">
            <UserCircle class="w-6 h-6 text-slate-500" />
          </div>
          <div class="text-left hidden lg:block">
            <p class="text-xs font-black text-slate-700 leading-none mb-0.5">{{ username || 'Admin' }}</p>
            <p class="text-[10px] text-slate-400 font-medium">{{ t('header.userMenu') }}</p>
          </div>
        </Button>
        <div
          v-if="isUserMenuOpen"
          class="absolute right-0 top-full z-[120] mt-2 w-48 overflow-hidden rounded-xl border border-slate-200 bg-white py-1 shadow-xl"
          role="menu"
          @click.stop
        >
          <div class="border-b border-slate-100 px-4 py-2 text-xs text-slate-500">
            {{ username }}
          </div>
          <button
            type="button"
            class="flex w-full items-center gap-2 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-red-50 hover:text-red-700"
            role="menuitem"
            @click="handleLogout"
          >
            <LogOut class="h-4 w-4" />
            {{ t('header.logout') }}
          </button>
        </div>
      </div>

      <Button
        variant="ghost"
        size="icon"
        class="md:hidden"
        :aria-label="t('header.openNavigation')"
        @click="toggleMobileNav"
      >
         <Menu class="w-6 h-6 text-slate-700" />
      </Button>
    </div>
  </header>
</template>
