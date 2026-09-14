/**
 * 接入管理
 * ========
 *
 * MCP 对外接入的配置与观测：端点状态、配置片段、工具清单、调用统计。
 *
 * 安全约束：本页不显示 token 原文——配置片段用占位符，
 * token 的生成与轮换仍在 .env 中完成。
 */
import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowUpRight,
  Check,
  Copy,
  Loader2,
  Plug,
  RefreshCw,
  Wrench,
  Zap,
} from 'lucide-react'

import apiClient from '@/api/client'
import CountUp from '@/components/motion/CountUp'
import Reveal from '@/components/motion/Reveal'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface McpTool {
  name?: string
  description?: string
}

interface McpInfo {
  protocol: string
  auth_configured: boolean
  tool_count: number
  tools: McpTool[]
  usage: string
}

interface McpStats {
  days: number
  total: number
  by_result: Record<string, number>
  by_tool: Record<string, number>
  recent: {
    id: number
    ts: string | null
    principal_id: string | null
    action: string
    result: string
  }[]
  auth_configured: boolean
  tool_count: number
  protocol: string
}

interface SelftestResult {
  ok: boolean
  elapsed_ms: number
  protocol: string
  server: { name?: string; version?: string } | null
  auth_configured: boolean
}

const RESULT_TONE: Record<string, string> = {
  ok: 'badge-ok',
  denied: 'badge-err',
  error: 'badge-err',
}

/** 配置片段：token 用占位符——本页绝不显示 token 原文 */
const CONFIG_SNIPPET = `{
  "mcpServers": {
    "webinsight": {
      "url": "http://127.0.0.1:8000/mcp",
      "headers": {
        "Authorization": "Bearer <MCP_API_KEY>"
      }
    }
  }
}`

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

export default function IntegrationsPage() {
  const [info, setInfo] = useState<McpInfo | null>(null)
  const [stats, setStats] = useState<McpStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [testing, setTesting] = useState(false)
  const [selftest, setSelftest] = useState<SelftestResult | null>(null)
  const [copied, setCopied] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [infoResp, statsResp] = await Promise.allSettled([
        fetch('/mcp').then((response) => response.json() as Promise<McpInfo>),
        apiClient.get<McpStats>('/mcp/stats'),
      ])
      if (infoResp.status === 'fulfilled') setInfo(infoResp.value)
      if (statsResp.status === 'fulfilled') setStats(statsResp.value.data)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function runSelftest() {
    setTesting(true)
    setMessage(null)
    try {
      const { data } = await apiClient.post<SelftestResult>('/mcp/selftest')
      setSelftest(data)
      void load()
    } catch {
      setMessage('自检请求失败（服务未就绪？）')
      setSelftest(null)
    } finally {
      setTesting(false)
    }
  }

  async function copyConfig() {
    try {
      await navigator.clipboard.writeText(CONFIG_SNIPPET)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      setMessage('复制失败——请手动选择代码块内容')
    }
  }

  const tools = info?.tools ?? []
  const byTool = Object.entries(stats?.by_tool ?? {})
  const maxToolCount = byTool.length
    ? Math.max(...byTool.map(([, count]) => count))
    : 1

  return (
    <div className="mx-auto max-w-6xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-muted-foreground">
          MCP 接入配置与观测。本页不显示 token 原文——密钥仍在环境变量 / .env 中管理。
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

      {message && (
        <div className="glass rounded-lg px-4 py-2.5 text-xs text-muted-foreground">
          {message}
        </div>
      )}

      {/* ---------------- 端点 ---------------- */}
      <Reveal className="glass rounded-xl p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Plug className="h-4 w-4 text-primary" />
              <span className="mono-tag">POST /mcp</span>
              <span className="badge-dot badge-ok">在线</span>
              <span
                className={cn(
                  'badge-dot',
                  info?.auth_configured ? 'badge-ok' : 'badge-warn',
                )}
              >
                {info?.auth_configured ? '鉴权已配置' : '鉴权未配置'}
              </span>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              {info?.protocol ?? 'json-rpc-2.0-over-http'} · 工具{' '}
              {info?.tool_count ?? '—'} 个 · JSON-RPC over HTTP
            </p>
            {selftest && (
              <p
                className={cn(
                  'mt-2 text-xs',
                  selftest.ok ? 'text-primary' : 'text-destructive',
                )}
              >
                {selftest.ok
                  ? `✓ initialize 握手成功（${selftest.server?.name ?? 'webinsight'} ${
                      selftest.server?.version ?? ''
                    } · ${selftest.elapsed_ms}ms）`
                  : '× 自检失败'}
              </p>
            )}
          </div>
          <div className="flex shrink-0 gap-2">
            <Button size="sm" variant="outline" onClick={() => void runSelftest()} disabled={testing}>
              {testing ? (
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
              ) : (
                <Zap className="mr-1.5 h-3.5 w-3.5" />
              )}
              测试连通
            </Button>
            <Button size="sm" variant="outline" onClick={() => void copyConfig()}>
              {copied ? (
                <Check className="mr-1.5 h-3.5 w-3.5" />
              ) : (
                <Copy className="mr-1.5 h-3.5 w-3.5" />
              )}
              {copied ? '已复制' : '复制配置'}
            </Button>
          </div>
        </div>

        <pre className="mt-4 overflow-x-auto rounded-lg border border-border/60 bg-muted/30 p-3 text-[0.68rem] leading-relaxed text-muted-foreground">
          {CONFIG_SNIPPET}
        </pre>
      </Reveal>

      {/* ---------------- 工具清单 ---------------- */}
      <Reveal delay={0.08} className="glass overflow-hidden rounded-xl">
        <div className="flex items-center gap-2 border-b border-border/60 px-5 py-3.5">
          <Wrench className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-semibold">工具清单（{tools.length}）</h3>
        </div>
        {tools.length === 0 ? (
          <div className="px-5 py-10 text-center text-sm text-muted-foreground">
            工具清单加载中或服务未就绪
          </div>
        ) : (
          <ul className="divide-y divide-border/40">
            {tools.map((tool) => (
              <li key={tool.name} className="flex items-start gap-3 px-5 py-3">
                <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary/60" />
                <div className="min-w-0">
                  <div className="font-mono text-xs font-medium">{tool.name}</div>
                  <div className="mt-0.5 text-[0.68rem] text-muted-foreground">
                    {tool.description ?? '—'}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Reveal>

      {/* ---------------- 调用统计 ---------------- */}
      <Reveal delay={0.14} className="space-y-3">
        <div className="grid gap-3 sm:grid-cols-4">
          <StatCell label={`总调用（近 ${stats?.days ?? 7} 天）`} value={stats?.total ?? 0} />
          <StatCell label="成功" value={stats?.by_result.ok ?? 0} tone="ok" />
          <StatCell label="被拒" value={stats?.by_result.denied ?? 0} tone="err" />
          <StatCell label="错误" value={stats?.by_result.error ?? 0} tone="err" />
        </div>

        <div className="grid gap-5 lg:grid-cols-2">
          {/* 按工具 */}
          <div className="glass rounded-xl p-5">
            <h3 className="mb-3 text-sm font-semibold">按工具</h3>
            {byTool.length === 0 ? (
              <p className="text-xs text-muted-foreground">
                暂无调用记录——接入 Hermes 后在此观测
              </p>
            ) : (
              <ul className="space-y-2.5">
                {byTool.map(([name, count]) => (
                  <li key={name}>
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-mono">{name}</span>
                      <span className="tabular-nums text-muted-foreground">{count}</span>
                    </div>
                    <div className="mt-1 h-1.5 overflow-hidden rounded bg-muted/50">
                      <div
                        className="h-full rounded bg-primary/60"
                        style={{ width: `${Math.max(4, (count / maxToolCount) * 100)}%` }}
                      />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* 最近调用 */}
          <div className="glass overflow-hidden rounded-xl">
            <div className="flex items-center justify-between border-b border-border/60 px-5 py-3.5">
              <h3 className="text-sm font-semibold">最近调用</h3>
              <Link
                to="/audit?action=mcp."
                className="inline-flex items-center gap-0.5 text-[0.7rem] text-primary hover:underline"
              >
                查看全部审计 <ArrowUpRight className="h-3 w-3" />
              </Link>
            </div>
            {(!stats || stats.recent.length === 0) ? (
              <div className="px-5 py-10 text-center text-sm text-muted-foreground">
                暂无调用记录
              </div>
            ) : (
              <ul className="divide-y divide-border/40">
                {stats.recent.map((row) => (
                  <li
                    key={row.id}
                    className="flex items-center justify-between gap-3 px-5 py-2.5 text-xs"
                  >
                    <div className="flex min-w-0 items-center gap-2">
                      <span className="truncate font-mono text-[0.7rem]">{row.action}</span>
                      <span className="shrink-0 text-muted-foreground">
                        {row.principal_id ?? '—'}
                      </span>
                    </div>
                    <div className="flex shrink-0 items-center gap-3">
                      <span className="tabular-nums text-muted-foreground">
                        {formatDateTime(row.ts)}
                      </span>
                      <span className={cn('badge-dot', RESULT_TONE[row.result] ?? 'badge-info')}>
                        {row.result}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </Reveal>
    </div>
  )
}

function StatCell({
  label,
  value,
  tone,
}: {
  label: string
  value: number
  tone?: 'ok' | 'err'
}) {
  return (
    <div className="glass rounded-xl p-4">
      <div className="section-title mb-1.5">{label}</div>
      <div
        className={cn(
          'text-2xl font-semibold tracking-tight tabular-nums',
          tone === 'err' && value > 0 && 'text-destructive',
        )}
      >
        <CountUp value={value} />
      </div>
    </div>
  )
}
