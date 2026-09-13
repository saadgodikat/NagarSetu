'use client'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/lib/auth'
import { LayoutDashboard, ClipboardList, Map, Bot, LogOut, Building2 } from 'lucide-react'
import clsx from 'clsx'
import { Role } from '@/lib/types'

const navItems: { href: string; icon: React.ElementType; key: string; roles: Role[] }[] = [
  { href: '/dashboard', icon: LayoutDashboard, key: 'nav.dashboard', roles: ['admin', 'department_head'] },
  { href: '/complaints', icon: ClipboardList, key: 'nav.complaints', roles: ['admin', 'department_head', 'officer'] },
  { href: '/map', icon: Map, key: 'nav.map', roles: ['admin', 'officer', 'department_head'] },
  { href: '/assistant', icon: Bot, key: 'nav.assistant', roles: ['admin', 'officer', 'department_head'] },
]

export function Sidebar() {
  const pathname = usePathname()
  const { t, i18n } = useTranslation()
  const { user, logout } = useAuth()
  const router = useRouter()

  const visible = navItems.filter((item) => !user || item.roles.includes(user.role))

  function toggleLang() {
    const next = i18n.language === 'en' ? 'mr' : 'en'
    void i18n.changeLanguage(next)
    localStorage.setItem('smcp_lang', next)
  }

  function handleLogout() {
    logout()
    router.push('/login')
  }

  return (
    <aside className="fixed left-0 top-0 h-screen w-56 bg-white border-r border-gray-200 flex flex-col z-20">
      <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
        <Building2 size={20} className="text-blue-600 shrink-0" />
        <div>
          <p className="text-sm font-bold text-blue-700 leading-tight">{t('app.name')}</p>
          <p className="text-xs text-gray-400 mt-0.5">{t('app.tagline')}</p>
        </div>
      </div>

      <nav className="flex-1 py-4 px-3 space-y-1">
        {visible.map(({ href, icon: Icon, key }) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
              pathname.startsWith(href)
                ? 'bg-blue-50 text-blue-700 font-medium'
                : 'text-gray-600 hover:bg-gray-50'
            )}
          >
            <Icon size={18} />
            {t(key)}
          </Link>
        ))}
      </nav>

      <div className="px-3 py-4 border-t border-gray-100 space-y-1">
        <button
          onClick={toggleLang}
          className="flex items-center gap-2 px-3 py-2 text-xs text-gray-500 hover:text-gray-700 hover:bg-gray-50 rounded-lg w-full font-medium"
        >
          {i18n.language === 'en' ? 'मराठी' : 'English'}
        </button>
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-3 py-2 text-sm text-gray-600 hover:bg-gray-50 rounded-lg w-full"
        >
          <LogOut size={18} />
          {t('nav.logout')}
        </button>
        {user && (
          <p className="px-3 text-xs text-gray-400 truncate pt-1">{user.name}</p>
        )}
      </div>
    </aside>
  )
}
