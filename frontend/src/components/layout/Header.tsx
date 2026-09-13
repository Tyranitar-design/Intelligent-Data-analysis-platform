import { Button } from '@/components/ui/button'
import { ThemeToggle } from '@/components/theme-toggle'
import { Bell, User } from 'lucide-react'

export function Header() {
  return (
    <header className="flex items-center justify-between h-16 px-6 border-b bg-card">
      <div>
        <h1 className="text-xl font-semibold">智能数据分析平台</h1>
      </div>
      
      <div className="flex items-center space-x-4">
        {/* 通知 */}
        <Button variant="ghost" size="icon">
          <Bell className="w-5 h-5" />
        </Button>
        
        {/* 主题切换 */}
        <ThemeToggle />
        
        {/* 用户 */}
        <Button variant="ghost" size="icon">
          <User className="w-5 h-5" />
        </Button>
      </div>
    </header>
  )
}
