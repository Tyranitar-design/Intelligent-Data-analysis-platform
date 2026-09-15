/**
 * 调度中心
 * ========
 *
 * 采集从「手动触发」变成「按计划运行」的控制台。
 *
 * - 频率用可视化选择（每 N 小时 / 每天 / 每周），不让用户手写 cron；
 * - 重复执行不会造成重复数据（内容级去重兜底，见后端逻辑）；
 * - 手动「立即执行」与调度循环走同一条执行路径。
 */
import { useCallback, useEffect, useState } from 'react'
import { CalendarClock, Loader2, Play, Plus, RefreshCw, Trash2 } from 'lucide-react'

import apiClient from '@/api/client'
import Reveal from '@/components/motion/Reveal'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'

interface ScheduleItem {
  schedule_id: number
  name: string
  plan_id: number
  frequency: 'hourly' | 'daily' | 'weekly'
  interval_hours: number | null
  time_of_day: string | null
  weekday: number | null
  frequency_text: string
  enabled: boolean
  last_run_at: string | null
  next_run_at: string | null
  run_count: number
  fail_count: number
  last_job_id: number | null
}

interface PlanItem {
  plan_id: number
  target_url: string
  requirement: string | null
  status: string
}

const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

const FREQ_OPTIONS = [
  { value: 'hourly', label: '每 N 小时' },
  { value: 'daily', label: '每天定点' },
  { value: 'weekly', label: '每周定点' },
] as const

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  const now = new Date()
  const time = date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
  if (date.toDateString() === now.toDateString()) return `今天 ${time}`
  const tomorrow = new Date(now)
  tomorrow.setDate(now.getDate() + 1)
  if (date.toDateString() === tomorrow.toDateString()) return `明天 ${time}`
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

function errorDetail(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data
    ?.detail
  return typeof detail === 'string' ? detail : fallback
}

export default function SchedulesPage() {
  const [schedules, setSchedules] = useState<ScheduleItem[]>([])
  const [plans, setPlans] = useState<PlanItem[]>([])
  const [loading, setLoading] = useState(true)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)

  // 新建表单
  const [name, setName] = useState('')
  const [planId, setPlanId] = useState<string>('')
  const [frequency, setFrequency] = useState<'hourly' | 'daily' | 'weekly'>('daily')
  const [intervalHours, setIntervalHours] = useState(6)
  const [timeOfDay, setTimeOfDay] = useState('06:00')
  const [weekday, setWeekday] = useState(0)
  const [creating, setCreating] = useState(false)
  // 每个规则上一次执行的结果（手动触发后展示）
  const [lastResult, setLastResult] = useState<Record<number, string>>({})

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [schedResp, planResp] = await Promise.allSettled([
        apiClient.get<{ items: ScheduleItem[] }>('/collect/schedules'),
        apiClient.get<{ items: PlanItem[] }>('/collect/plans', { params: { limit: 50 } }),
      ])
      if (schedResp.status === 'fulfilled') setSchedules(schedResp.value.data.items ?? [])
      if (planResp.status === 'fulfilled') setPlans(planResp.value.data.items ?? [])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function create() {
    if (!name.trim() || !planId) {
      setMessage('请填写名称并选择一个采集计划')
      return
    }
    setCreating(true)
    setMessage(null)
    try {
      const payload: Record<string, unknown> = {
        name: name.trim(),
        plan_id: Number(planId),
        frequency,
        enabled: true,
      }
      if (frequency === 'hourly') {
        payload.interval_hours = intervalHours
      } else {
        payload.time_of_day = timeOfDay
        if (frequency === 'weekly') payload.weekday = weekday
      }
      const { data } = await apiClient.post<{ schedule: ScheduleItem }>(
        '/collect/schedules',
        payload,
      )
      setMessage(`已创建「${data.schedule.name}」，下次执行：${formatDateTime(data.schedule.next_run_at)}`)
      setName('')
      setShowForm(false)
      void load()
    } catch (err) {
      setMessage(errorDetail(err, '创建失败'))
    } finally {
      setCreating(false)
    }
  }

  async function toggle(item: ScheduleItem, enabled: boolean) {
    setBusyId(item.schedule_id)
    setMessage(null)
    try {
      await apiClient.patch(`/collect/schedules/${item.schedule_id}`, { enabled })
      void load()
    } catch (err) {
      setMessage(errorDetail(err, '更新失败'))
    } finally {
      setBusyId(null)
    }
  }

  async function runNow(item: ScheduleItem) {
    setBusyId(item.schedule_id)
    setMessage(null)
    try {
      const { data } = await apiClient.post<{
        result: { status: string; job_id: number | null }
        schedule: ScheduleItem
      }>(`/collect/schedules/${item.schedule_id}/run`)
      const label =
        data.result.status === 'succeeded'
          ? '成功'
          : data.result.status === 'partial'
            ? '部分成功'
            : data.result.status === 'failed'
              ? '失败'
              : data.result.status
      setLastResult((prev) => ({
        ...prev,
        [item.schedule_id]: `任务 #${data.result.job_id} · ${label}`,
      }))
      void load()
    } catch (err) {
      setMessage(errorDetail(err, '执行失败'))
    } finally {
      setBusyId(null)
    }
  }

  async function remove(item: ScheduleItem) {
    setBusyId(item.schedule_id)
    setMessage(null)
    try {
      await apiClient.delete(`/collect/schedules/${item.schedule_id}`)
      setMessage(`已删除「${item.name}」`)
      void load()
    } catch (err) {
      setMessage(errorDetail(err, '删除失败'))
    } finally {
      setBusyId(null)
    }
  }

  // KPI 聚合（真实数据）
  const enabledCount = schedules.filter((item) => item.enabled).length
  const totalRuns = schedules.reduce((sum, item) => sum + (item.run_count ?? 0), 0)
  const totalFails = schedules.reduce((sum, item) => sum + (item.fail_count ?? 0), 0)

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-muted-foreground">
          按计划自动执行采集。重复执行不会产生重复数据（内容级去重兜底）。
        </p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
            {loading ? (
              <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
            ) : (
              <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
            )}
            刷新
          </Button>
          <Button size="sm" onClick={() => setShowForm((v) => !v)}>
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            新建调度
          </Button>
        </div>
      </div>

      {message && (
        <div className="glass rounded-lg px-4 py-2.5 text-xs text-muted-foreground">
          {message}
        </div>
      )}

      {/* ---------------- KPI 读数行 ---------------- */}
      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          {
            label: '调度规则',
            value: String(schedules.length),
            hint: '全部定时任务',
            tone: '',
          },
          {
            label: '启用中',
            value: String(enabledCount),
            hint: enabledCount ? '按计划自动运行' : '当前全部暂停',
            tone: 'text-primary',
          },
          {
            label: '累计执行',
            value: totalRuns.toLocaleString(),
            hint: '所有规则的运行总次数',
            tone: '',
          },
          {
            label: '失败',
            value: String(totalFails),
            hint: totalFails > 0 ? '需要检查的目标' : '全部成功',
            tone: totalFails > 0 ? 'text-[hsl(0_74%_62%)]' : '',
          },
        ].map((item, index) => (
          <div
            key={item.label}
            className="panel animate-rise p-4"
            style={{ ['--stagger' as string]: `${index * 60}ms` }}
          >
            <div className="label-xs mb-1.5">{item.label}</div>
            <div
              className={cn(
                'num text-[1.6rem] font-semibold leading-none',
                item.tone,
              )}
            >
              {item.value}
            </div>
            <div className="mt-2 truncate text-[0.68rem] text-muted-foreground">
              {item.hint}
            </div>
          </div>
        ))}
      </section>

      {/* ---------------- 新建表单 ---------------- */}
      {showForm && (
        <div className="glass space-y-4 rounded-xl p-5">
          <div className="section-title">新建调度规则</div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground">规则名称</label>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="如：每日新闻采集"
                className="h-9"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs text-muted-foreground">采集计划</label>
              <Select value={planId} onValueChange={setPlanId}>
                <SelectTrigger className="h-9">
                  <SelectValue placeholder={plans.length ? '选择计划' : '暂无计划，先去站点分析创建'} />
                </SelectTrigger>
                <SelectContent>
                  {plans.map((p) => (
                    <SelectItem key={p.plan_id} value={String(p.plan_id)}>
                      #{p.plan_id} · {p.target_url}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs text-muted-foreground">频率</label>
            <div className="flex flex-wrap gap-2">
              {FREQ_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setFrequency(opt.value)}
                  className={cn(
                    'rounded-lg border px-3 py-1.5 text-xs transition-colors',
                    frequency === opt.value
                      ? 'border-primary/50 bg-primary/10 font-medium text-primary'
                      : 'border-border/60 text-muted-foreground hover:border-primary/30 hover:text-foreground',
                  )}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap items-end gap-4">
            {frequency === 'hourly' && (
              <div className="space-y-1.5">
                <label className="text-xs text-muted-foreground">间隔（小时）</label>
                <Input
                  type="number"
                  min={1}
                  max={24}
                  value={intervalHours}
                  onChange={(e) => setIntervalHours(Number(e.target.value) || 1)}
                  className="h-9 w-28"
                />
              </div>
            )}
            {frequency !== 'hourly' && (
              <div className="space-y-1.5">
                <label className="text-xs text-muted-foreground">执行时刻</label>
                <Input
                  type="time"
                  value={timeOfDay}
                  onChange={(e) => setTimeOfDay(e.target.value)}
                  className="h-9 w-32"
                />
              </div>
            )}
            {frequency === 'weekly' && (
              <div className="space-y-1.5">
                <label className="text-xs text-muted-foreground">星期</label>
                <Select value={String(weekday)} onValueChange={(v) => setWeekday(Number(v))}>
                  <SelectTrigger className="h-9 w-28">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {WEEKDAYS.map((label, index) => (
                      <SelectItem key={label} value={String(index)}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            <Button size="sm" onClick={() => void create()} disabled={creating}>
              {creating ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : null}
              创建
            </Button>
          </div>
        </div>
      )}

      {/* ---------------- 规则列表 ---------------- */}
      {schedules.length === 0 && !loading ? (
        <div className="glass rounded-xl px-5 py-14 text-center">
          <CalendarClock className="mx-auto mb-3 h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">暂无调度规则</p>
          <p className="mt-1 text-xs text-muted-foreground/70">
            先从「采集任务」跑通一次手动采集，再回来建立定时规则
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {schedules.map((item, index) => (
            <Reveal key={item.schedule_id} delay={index * 0.04}>
              <div className="glass glass-hover rounded-xl p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold">{item.name}</span>
                      <span className="badge-dot badge-info">{item.frequency_text}</span>
                      {!item.enabled && <span className="badge-dot badge-warn">已暂停</span>}
                    </div>
                    <div className="mt-1 truncate text-xs text-muted-foreground">
                      计划 #{item.plan_id}
                      {plans.find((p) => p.plan_id === item.plan_id) &&
                        ` · ${plans.find((p) => p.plan_id === item.plan_id)?.target_url}`}
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <span className="text-xs text-muted-foreground">
                      {item.enabled ? '启用中' : '已暂停'}
                    </span>
                    <Switch
                      checked={item.enabled}
                      disabled={busyId === item.schedule_id}
                      onCheckedChange={(checked) => void toggle(item, checked)}
                    />
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                    <span>
                      上次 <span className="tabular-nums">{formatDateTime(item.last_run_at)}</span>
                    </span>
                    <span>
                      下次 <span className="tabular-nums text-foreground/80">{formatDateTime(item.next_run_at)}</span>
                    </span>
                    <span>
                      累计 <span className="tabular-nums">{item.run_count}</span> 次
                      {item.fail_count > 0 && (
                        <span className="text-destructive"> · 失败 {item.fail_count}</span>
                      )}
                    </span>
                    {lastResult[item.schedule_id] && (
                      <span className="text-primary/80">{lastResult[item.schedule_id]}</span>
                    )}
                  </div>
                  <div className="flex shrink-0 gap-1.5">
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-8"
                      disabled={busyId === item.schedule_id}
                      onClick={() => void runNow(item)}
                    >
                      {busyId === item.schedule_id ? (
                        <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Play className="mr-1.5 h-3.5 w-3.5" />
                      )}
                      立即执行
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                      disabled={busyId === item.schedule_id}
                      onClick={() => void remove(item)}
                      aria-label={`删除 ${item.name}`}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      )}
    </div>
  )
}
