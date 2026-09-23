/**
 * 审计日志
 * ========
 *
 * 谁在什么时候对什么做了什么。审计是「可追溯」的落点：
 * 合规解锁、MCP 调用、采集执行都会在这里留痕。
 *
 * 不提供删除——可删的审计等于没有审计（清理走保留策略）。
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ChevronDown, FileSearch, Loader2, RefreshCw } from 'lucide-react'

import apiClient from '@/api/client'
import Reveal from '@/components/motion/Reveal'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

interface AuditItem {
  id: number
  ts: string | null
  principal_id: string | null
  action: string
  target_type: string | null
  target_id: string | null
  verdict_row_id: number | null
  request_digest?: string | null
  result: string
  detail: Record<string, unknown>
  ip: string | null
}

// v5：结果列用实底 pill（参考图统一语言）
const RESULT_TONE: Record<string, string> = {
  ok: 'pill-ok',
  denied: 'pill-err',
  error: 'pill-err',
}

const ACTION_FILTERS = [
  { value: '', label: '全部' },
  { value: 'compliance.', label: '合规' },
  { value: 'collect.', label: '采集' },
  { value: 'discover.', label: '判别' },
  { value: 'mcp.', label: 'MCP' },
] as const

const RESULT_FILTERS = [
  { value: '', label: '全部结果' },
  { value: 'ok', label: 'ok' },
  { value: 'denied', label: 'denied' },
  { value: 'error', label: 'error' },
] as const

const PAGE_SIZE = 50

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

export default function AuditPage() {
  const [items, setItems] = useState<AuditItem[]>([])
  const [total, setTotal] = useState(0)
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  // 支持 /audit?action=mcp. 这类带过滤条件的跳转（接入管理 → 审计）
  const [searchParams] = useSearchParams()
  const [actionFilter, setActionFilter] = useState<string>(
    () => searchParams.get('action') ?? '',
  )
  const [resultFilter, setResultFilter] = useState<string>('')
  const [principal, setPrincipal] = useState('')
  const principalRef = useRef('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await apiClient.get<{ total: number; items: AuditItem[] }>(
        '/audit/logs',
        {
          params: {
            limit: PAGE_SIZE,
            offset,
            ...(actionFilter ? { action: actionFilter } : {}),
            ...(resultFilter ? { result: resultFilter } : {}),
            ...(principalRef.current ? { principal: principalRef.current } : {}),
          },
        },
      )
      setItems(data.items ?? [])
      setTotal(data.total ?? 0)
    } catch {
      setItems([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [actionFilter, resultFilter, offset])

  useEffect(() => {
    void load()
  }, [load])

  function selectAction(value: string) {
    setActionFilter(value)
    setOffset(0)
  }

  function selectResult(value: string) {
    setResultFilter(value)
    setOffset(0)
  }

  function applyPrincipal() {
    principalRef.current = principal.trim()
    setOffset(0)
    void load()
  }

  const canPrev = offset > 0
  const canNext = offset + PAGE_SIZE < total

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-muted-foreground">
          合规解锁、采集执行、MCP 调用均在此留痕。审计日志不提供删除（清理走保留策略）。
        </p>
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          {loading ? (
            <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
          ) : (
            <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
          )}
          刷新
        </Button>
      </div>

      {/* ---------------- 筛选 ---------------- */}
      <div className="glass flex flex-wrap items-center gap-3 rounded-xl px-4 py-3">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="section-title mr-1">操作</span>
          {ACTION_FILTERS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => selectAction(opt.value)}
              className={cn(
                'rounded-lg border px-2.5 py-1 text-xs transition-colors',
                actionFilter === opt.value
                  ? 'border-primary/50 bg-primary/10 font-medium text-primary'
                  : 'border-border/60 text-muted-foreground hover:text-foreground',
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <span className="section-title mr-1">结果</span>
          {RESULT_FILTERS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => selectResult(opt.value)}
              className={cn(
                'rounded-lg border px-2.5 py-1 text-xs transition-colors',
                resultFilter === opt.value
                  ? 'border-primary/50 bg-primary/10 font-medium text-primary'
                  : 'border-border/60 text-muted-foreground hover:text-foreground',
              )}
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <Input
            value={principal}
            onChange={(e) => setPrincipal(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') applyPrincipal()
            }}
            placeholder="按主体过滤（回车应用）"
            className="h-8 w-52 text-xs"
          />
        </div>
      </div>

      {/* ---------------- 列表 ---------------- */}
      <Reveal className="glass overflow-hidden rounded-xl">
        <div className="flex items-center justify-between border-b border-border/60 px-5 py-3.5">
          <h3 className="text-sm font-semibold">
            留痕记录（{total}）
          </h3>
          <span className="text-[0.68rem] text-muted-foreground">点击行展开详情</span>
        </div>

        {items.length === 0 && !loading ? (
          <div className="px-5 py-12 text-center">
            <FileSearch className="mx-auto mb-3 h-8 w-8 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">暂无审计记录</p>
            <p className="mt-1 text-xs text-muted-foreground/70">
              执行一次站点分析或合规操作后回来看
            </p>
          </div>
        ) : (
          <ul className="divide-y divide-border/40">
            {items.map((item) => {
              const expanded = expandedId === item.id
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => setExpandedId(expanded ? null : item.id)}
                    className="grid w-full grid-cols-[9rem_6rem_1fr_auto] items-center gap-3 px-5 py-2.5 text-left transition-colors hover:bg-muted/40 sm:grid-cols-[10rem_7rem_1fr_9rem_4rem_1rem]"
                  >
                    <span className="truncate text-xs tabular-nums text-muted-foreground">
                      {formatDateTime(item.ts)}
                    </span>
                    <span className="hidden truncate text-xs sm:block">
                      {item.principal_id ?? '—'}
                    </span>
                    <span className="truncate font-mono text-[0.72rem]">{item.action}</span>
                    <span className="hidden truncate text-xs text-muted-foreground sm:block">
                      {item.target_type
                        ? `${item.target_type}#${item.target_id ?? ''}`
                        : '—'}
                    </span>
                    <span className={cn('pill shrink-0', RESULT_TONE[item.result] ?? 'pill-info')}>
                      {item.result}
                    </span>
                    <ChevronDown
                      className={cn(
                        'h-3.5 w-3.5 text-muted-foreground transition-transform',
                        expanded && 'rotate-180',
                      )}
                    />
                  </button>

                  {expanded && (
                    <div className="space-y-1.5 border-t border-border/40 bg-muted/20 px-5 py-3 text-xs text-muted-foreground">
                      {item.request_digest && (
                        <div>
                          入参摘要 <span className="mono-tag">{item.request_digest}</span>
                        </div>
                      )}
                      {item.verdict_row_id != null && (
                        <div>关联判定行 #{item.verdict_row_id}</div>
                      )}
                      {item.ip && <div>来源 {item.ip}</div>}
                      {Object.keys(item.detail ?? {}).length > 0 && (
                        <div className="mono-tag inline-block max-w-full overflow-x-auto whitespace-pre-wrap break-all">
                          {JSON.stringify(item.detail, null, 2)}
                        </div>
                      )}
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        )}

        {/* 分页 */}
        {total > PAGE_SIZE && (
          <div className="flex items-center justify-between border-t border-border/60 px-5 py-3">
            <span className="text-[0.68rem] text-muted-foreground">
              第 {Math.floor(offset / PAGE_SIZE) + 1} 页 · 共{' '}
              {Math.max(1, Math.ceil(total / PAGE_SIZE))} 页
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                className="h-7"
                disabled={!canPrev || loading}
                onClick={() => setOffset((v) => Math.max(0, v - PAGE_SIZE))}
              >
                上一页
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-7"
                disabled={!canNext || loading}
                onClick={() => setOffset((v) => v + PAGE_SIZE)}
              >
                下一页
              </Button>
            </div>
          </div>
        )}
      </Reveal>
    </div>
  )
}
