/**
 * 对比分析
 * ========
 *
 * 跨数据集差异：选两个数据集 → 行数 / 字段 / 覆盖差异一览。
 *
 * 两个典型场景：
 * - 同一来源的两次采集（版本演进：字段增减、行数变化）；
 * - 不同来源同类数据的对照（schema 对齐程度）。
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ArrowLeftRight, GitCompare, Loader2 } from 'lucide-react'

import apiClient from '@/api/client'
import Reveal from '@/components/motion/Reveal'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'

interface DatasetOption {
  dataset_id: number
  name: string
  row_count: number
  column_count: number
  created_at: string | null
}

interface DiffSide {
  dataset_id: number
  name: string
  row_count: number
  column_count: number
  created_at: string | null
}

interface DiffPayload {
  a: DiffSide
  b: DiffSide
  row_delta: number
  common_fields: string[]
  only_a: string[]
  only_b: string[]
  type_changed: { field: string; a: string | null; b: string | null }[]
  coverage_changes: { field: string; a: number; b: number; delta: number }[]
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

export default function ComparePage() {
  const [searchParams] = useSearchParams()
  const [options, setOptions] = useState<DatasetOption[]>([])
  // 支持 /compare?a=..&b=.. 带入预选（如数据集版本卡的「对比」入口）
  const [a, setA] = useState<string>(searchParams.get('a') ?? '')
  const [b, setB] = useState<string>(searchParams.get('b') ?? '')
  const [diff, setDiff] = useState<DiffPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [comparing, setComparing] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const autoCompared = useRef(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await apiClient.get<{ items: DatasetOption[] }>(
        '/collect/datasets',
        { params: { limit: 200 } },
      )
      setOptions(data.items ?? [])
    } catch {
      setOptions([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  // URL 带入 a/b 时自动执行一次对比（从版本卡跳转即见结果）
  useEffect(() => {
    if (autoCompared.current || !a || !b) return
    if (options.length === 0) return
    const hasA = options.some((o) => String(o.dataset_id) === a)
    const hasB = options.some((o) => String(o.dataset_id) === b)
    if (!hasA || !hasB) return
    autoCompared.current = true
    void compare()
  }, [options, a, b]) // eslint-disable-line react-hooks/exhaustive-deps

  async function compare() {
    if (!a || !b) {
      setMessage('请选择两个数据集')
      return
    }
    if (a === b) {
      setMessage('A 与 B 是同一个数据集——请选择两个不同的数据集')
      return
    }
    setComparing(true)
    setMessage(null)
    try {
      const { data } = await apiClient.get<DiffPayload>('/collect/datasets/diff', {
        params: { a: Number(a), b: Number(b) },
      })
      setDiff(data)
    } catch {
      setMessage('对比失败（数据集可能已被清理）')
      setDiff(null)
    } finally {
      setComparing(false)
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-muted-foreground">
          对比两个数据集的行数、字段与覆盖差异——同一来源的两次采集对比即版本演进视图。
        </p>
      </div>

      {loading && options.length === 0 ? (
        <div className="glass flex items-center gap-3 rounded-xl px-5 py-10 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" /> 加载数据集列表…
        </div>
      ) : options.length < 2 ? (
        <div className="glass rounded-xl px-5 py-14 text-center">
          <GitCompare className="mx-auto mb-3 h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">对比需要至少两个数据集</p>
          <p className="mt-1 text-xs text-muted-foreground/70">
            在「采集任务」完成两次采集并物化，或对同一计划执行两次后回来对比
          </p>
        </div>
      ) : (
        <>
          {/* ---------------- 选择器 ---------------- */}
          <div className="glass rounded-xl p-5">
            <div className="flex flex-wrap items-end gap-3">
              <div className="space-y-1.5">
                <label className="text-xs text-muted-foreground">数据集 A（基线）</label>
                <Select value={a} onValueChange={setA}>
                  <SelectTrigger className="h-9 w-64">
                    <SelectValue placeholder="选择数据集" />
                  </SelectTrigger>
                  <SelectContent className="max-h-72">
                    {options.map((option) => (
                      <SelectItem key={option.dataset_id} value={String(option.dataset_id)}>
                        {option.name}（{option.row_count} 行）
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <ArrowLeftRight className="mb-2.5 h-4 w-4 shrink-0 text-muted-foreground" />

              <div className="space-y-1.5">
                <label className="text-xs text-muted-foreground">数据集 B（对照）</label>
                <Select value={b} onValueChange={setB}>
                  <SelectTrigger className="h-9 w-64">
                    <SelectValue placeholder="选择数据集" />
                  </SelectTrigger>
                  <SelectContent className="max-h-72">
                    {options.map((option) => (
                      <SelectItem key={option.dataset_id} value={String(option.dataset_id)}>
                        {option.name}（{option.row_count} 行）
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <Button size="sm" className="h-9" onClick={() => void compare()} disabled={comparing}>
                {comparing ? (
                  <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                ) : (
                  <GitCompare className="mr-1.5 h-3.5 w-3.5" />
                )}
                开始对比
              </Button>
            </div>
          </div>

          {message && (
            <div className="glass rounded-lg px-4 py-2.5 text-xs text-muted-foreground">
              {message}
            </div>
          )}

          {/* ---------------- 结果 ---------------- */}
          {diff && (
            <Reveal className="space-y-4">
              {/* 概览 */}
              <div className="grid gap-3 sm:grid-cols-[1fr_auto_1fr]">
                <SummaryCard title="A · 基线" side={diff.a} />
                <div className="flex flex-col items-center justify-center gap-1 px-2">
                  <span className="section-title">行数差</span>
                  <span
                    className={cn(
                      diff.row_delta === 0
                        ? 'chip'
                        : diff.row_delta > 0
                          ? 'delta-up'
                          : 'delta-down',
                    )}
                  >
                    {diff.row_delta > 0
                      ? `↑ +${diff.row_delta}`
                      : diff.row_delta < 0
                        ? `↓ ${diff.row_delta}`
                        : '持平'}
                  </span>
                </div>
                <SummaryCard title="B · 对照" side={diff.b} />
              </div>

              {/* 字段与覆盖 */}
              <div className="grid gap-5 lg:grid-cols-2">
                <div className="glass rounded-xl p-5">
                  <h3 className="mb-3 text-sm font-semibold">
                    字段变化（共同 {diff.common_fields.length}）
                  </h3>
                  <div className="space-y-3">
                    {diff.only_b.length > 0 && (
                      <ChipRow label="B 新增" items={diff.only_b} tone="ok" />
                    )}
                    {diff.only_a.length > 0 && (
                      <ChipRow label="B 缺失（仅 A 有）" items={diff.only_a} tone="warn" />
                    )}
                    {diff.type_changed.length === 0 &&
                      diff.only_a.length === 0 &&
                      diff.only_b.length === 0 && (
                        <p className="text-xs text-muted-foreground">
                          字段集合一致，无类型变化
                        </p>
                      )}
                    {diff.type_changed.length > 0 && (
                      <div className="overflow-hidden rounded-lg border border-border/60">
                        <table className="w-full text-left text-[0.7rem]">
                          <thead className="bg-muted/40 text-muted-foreground">
                            <tr>
                              <th className="px-3 py-2 font-medium">字段</th>
                              <th className="px-2 py-2 font-medium">A 类型</th>
                              <th className="px-2 py-2 font-medium">B 类型</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border/40">
                            {diff.type_changed.map((change) => (
                              <tr key={change.field}>
                                <td className="px-3 py-1.5 font-medium">{change.field}</td>
                                <td className="px-2 py-1.5 text-muted-foreground">
                                  {change.a ?? '—'}
                                </td>
                                <td className="px-2 py-1.5 text-muted-foreground">
                                  {change.b ?? '—'}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </div>

                <div className="glass rounded-xl p-5">
                  <h3 className="mb-3 text-sm font-semibold">覆盖变化（共同字段）</h3>
                  {diff.coverage_changes.length === 0 ? (
                    <p className="text-xs text-muted-foreground">
                      覆盖无显著变化（差异 &lt; 1%）
                    </p>
                  ) : (
                    <div className="overflow-hidden rounded-lg border border-border/60">
                      <table className="w-full text-left text-[0.7rem]">
                        <thead className="bg-muted/40 text-muted-foreground">
                          <tr>
                            <th className="px-3 py-2 font-medium">字段</th>
                            <th className="px-2 py-2 font-medium">A</th>
                            <th className="px-2 py-2 font-medium">B</th>
                            <th className="px-2 py-2 font-medium">变化</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border/40">
                          {diff.coverage_changes.map((change) => (
                            <tr key={change.field}>
                              <td className="px-3 py-1.5 font-medium">{change.field}</td>
                              <td className="px-2 py-1.5 tabular-nums text-muted-foreground">
                                {Math.round(change.a * 100)}%
                              </td>
                              <td className="px-2 py-1.5 tabular-nums text-muted-foreground">
                                {Math.round(change.b * 100)}%
                              </td>
                              <td
                                className={cn(
                                  'px-2 py-1.5 tabular-nums',
                                  change.delta >= 0 ? 'text-primary' : 'text-amber-500',
                                )}
                              >
                                {change.delta >= 0 ? '+' : ''}
                                {Math.round(change.delta * 100)}%
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            </Reveal>
          )}
        </>
      )}
    </div>
  )
}

function SummaryCard({ title, side }: { title: string; side: DiffSide }) {
  return (
    <div className="glass rounded-xl p-4">
      <div className="section-title mb-1.5">{title}</div>
      <div className="truncate text-sm font-medium">{side.name}</div>
      <div className="mt-1 text-xs text-muted-foreground">
        <span className="tabular-nums">{side.row_count}</span> 行 ×{' '}
        <span className="tabular-nums">{side.column_count}</span> 列
        <span className="ml-2">{formatDateTime(side.created_at)}</span>
      </div>
    </div>
  )
}

function ChipRow({
  label,
  items,
  tone,
}: {
  label: string
  items: string[]
  tone: 'ok' | 'warn'
}) {
  return (
    <div>
      <div className="mb-1.5 flex items-center gap-2">
        <span className={cn('badge-dot', tone === 'ok' ? 'badge-ok' : 'badge-warn')}>
          {label}
        </span>
        <span className="text-[0.66rem] text-muted-foreground">{items.length} 个</span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item) => (
          <span key={item} className="mono-tag">
            {item}
          </span>
        ))}
      </div>
    </div>
  )
}
