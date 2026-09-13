import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  Table, List, RefreshCw, Loader2, Search, Download, Database,
  ChevronLeft, ChevronRight, Eye, Sparkles, FileSpreadsheet,
  FileJson, FileText, BarChart3, Filter, X,
} from 'lucide-react'
import { dataBrowserApi } from '@/api/data'
import { extractApiError } from '@/api/crawl'
import { useAppStore } from '@/stores/appStore'

export default function DataBrowserPage() {
  const [searchParams] = useSearchParams()
  const { addNotification } = useAppStore()
  const [loading, setLoading] = useState(true)

  // 表列表
  const [tables, setTables] = useState<any[]>([])
  const [selectedTable, setSelectedTable] = useState<string>('')

  // 数据查询
  const [rows, setRows] = useState<any[]>([])
  const [columns, setColumns] = useState<string[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [search, setSearch] = useState('')
  const [sortColumn, setSortColumn] = useState('')
  const [sortOrder, setSortOrder] = useState('desc')

  // 表结构
  const [schema, setSchema] = useState<any>(null)
  const [tableStats, setTableStats] = useState<any>(null)

  // 导出
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    loadTables()
  }, [])

  const loadTables = async () => {
    try {
      setLoading(true)
      const res = await dataBrowserApi.listTables()
      const nextTables = res.data?.tables || []
      setTables(nextTables)

      const tableFromQuery = searchParams.get('table')
      if (tableFromQuery && nextTables.some((table: any) => table.name === tableFromQuery)) {
        await selectTable(tableFromQuery)
      } else if (tableFromQuery) {
        addNotification({
          type: 'error',
          title: '表不存在',
          description: `未找到数据表：${tableFromQuery}`,
        })
      }
    } catch (e: any) {
      addNotification({ type: 'error', title: '加载失败', description: extractApiError(e) })
    } finally {
      setLoading(false)
    }
  }

  const selectTable = async (tableName: string) => {
    setSelectedTable(tableName)
    setPage(1)
    setSearch('')
    setSortColumn('')
    await Promise.all([
      queryData(tableName, 1),
      loadSchema(tableName),
      loadStats(tableName),
    ])
  }

  const queryData = async (tableName: string, pg: number = page) => {
    try {
      const res = await dataBrowserApi.queryTable(tableName, {
        page: pg,
        size: pageSize,
        search: search || undefined,
        sort: sortColumn || undefined,
        order: sortOrder,
      })
      setRows(res.data?.data || [])
      setColumns(res.data?.columns || [])
      setTotal(res.data?.total || 0)
      setPage(pg)
    } catch (e: any) {
      addNotification({ type: 'error', title: '查询失败', description: extractApiError(e) })
    }
  }

  const loadSchema = async (tableName: string) => {
    try {
      const res = await dataBrowserApi.tableSchema(tableName)
      setSchema(res.data)
    } catch {}
  }

  const loadStats = async (tableName: string) => {
    try {
      const res = await dataBrowserApi.tableStats(tableName)
      setTableStats(res.data)
    } catch {}
  }

  const handleSearch = () => {
    setPage(1)
    if (selectedTable) queryData(selectedTable, 1)
  }

  const handlePageChange = (newPage: number) => {
    if (selectedTable) queryData(selectedTable, newPage)
  }

  const handleExport = async (format: string) => {
    if (!selectedTable) return
    setExporting(true)
    try {
      const res = await dataBrowserApi.exportTable(selectedTable, {
        format,
        search: search || undefined,
        max_rows: 10000,
      })
      // 下载文件
      const url = window.URL.createObjectURL(new Blob([res.data]))
      const a = document.createElement('a')
      a.href = url
      a.download = `${selectedTable}_${new Date().toISOString().slice(0, 10)}.${format}`
      a.click()
      window.URL.revokeObjectURL(url)
      addNotification({ type: 'success', title: '导出成功', description: `已导出 ${total} 条数据` })
    } catch (e: any) {
      addNotification({ type: 'error', title: '导出失败', description: extractApiError(e) })
    } finally {
      setExporting(false)
    }
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">数据浏览</h2>
          <p className="text-muted-foreground">
            浏览已采集数据 · 搜索筛选 · 导出 CSV/Excel/JSON
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={loadTables} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          {selectedTable && (
            <>
              <Button variant="outline" onClick={() => handleExport('csv')} disabled={exporting}>
                <FileText className="h-4 w-4 mr-2" /> CSV
              </Button>
              <Button variant="outline" onClick={() => handleExport('excel')} disabled={exporting}>
                <FileSpreadsheet className="h-4 w-4 mr-2" /> Excel
              </Button>
              <Button variant="outline" onClick={() => handleExport('json')} disabled={exporting}>
                <FileJson className="h-4 w-4 mr-2" /> JSON
              </Button>
            </>
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-4">
        {/* 左侧：表列表 */}
        <Card className="lg:col-span-1">
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Database className="w-4 h-4 text-primary" />
              数据表
            </CardTitle>
            <CardDescription>{tables.length} 个表</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[500px]">
              <div className="px-3 pb-3 space-y-1">
                {tables.map((t) => (
                  <button
                    key={t.name}
                    onClick={() => selectTable(t.name)}
                    className={`
                      w-full text-left p-3 rounded-lg text-sm transition-colors
                      ${selectedTable === t.name
                        ? 'bg-primary/10 border-primary text-primary font-medium'
                        : 'hover:bg-muted border-transparent'
                      }
                      border
                    `}
                  >
                    <div className="flex items-center justify-between">
                      <span className="truncate">{t.name}</span>
                      <Badge variant="secondary" className="text-xs ml-2 shrink-0">
                        {t.count}
                      </Badge>
                    </div>
                    {t.columns && (
                      <div className="text-xs text-muted-foreground mt-1 truncate">
                        {t.columns.slice(0, 3).map((c: any) => c.name).join(', ')}
                        {t.columns.length > 3 ? '...' : ''}
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* 右侧：数据详情 */}
        <div className="lg:col-span-3 space-y-4">
          {!selectedTable ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-16">
                <Table className="w-12 h-12 text-muted-foreground/30 mb-3" />
                <p className="text-muted-foreground">选择一个数据表开始浏览</p>
              </CardContent>
            </Card>
          ) : (
            <>
              {/* 表信息 */}
              {schema && (
                <Card>
                  <CardContent className="py-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-lg font-semibold flex items-center gap-2">
                          <Database className="w-5 h-5 text-primary" />
                          {selectedTable}
                        </h3>
                        <p className="text-sm text-muted-foreground mt-1">
                          {schema.columns?.length || 0} 列 · {schema.count || 0} 条记录
                        </p>
                        {total > 1000 && (
                          <p className="text-xs text-muted-foreground mt-1">
                            当前默认分页展示，建议通过搜索、筛选或导出查看更大规模数据。
                          </p>
                        )}
                      </div>
                      {tableStats?.by_platform && (
                        <div className="flex gap-2">
                          {tableStats.by_platform.map((p: any) => (
                            <Badge key={p.platform} variant="secondary">
                              {p.platform}: {p.count}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* 搜索和筛选 */}
              <Card>
                <CardContent className="py-3">
                  <div className="flex items-center gap-3">
                    <div className="flex-1 relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input
                        placeholder="搜索关键词..."
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                        className="pl-9"
                      />
                    </div>
                    {search && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => { setSearch(''); setPage(1); queryData(selectedTable, 1) }}
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    )}
                    <Button onClick={handleSearch} size="sm">
                      <Search className="w-4 h-4 mr-2" /> 搜索
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* 数据表格 */}
              <Card>
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b bg-muted/50">
                          <th className="text-left p-3 font-medium text-xs text-muted-foreground w-12">#</th>
                          {columns.map((col) => (
                            <th
                              key={col}
                              className="text-left p-3 font-medium text-xs text-muted-foreground cursor-pointer hover:text-foreground"
                              onClick={() => {
                                if (sortColumn === col) {
                                  setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
                                } else {
                                  setSortColumn(col)
                                  setSortOrder('desc')
                                }
                                queryData(selectedTable)
                              }}
                            >
                              <div className="flex items-center gap-1">
                                {col}
                                {sortColumn === col && (
                                  <span className="text-primary">{sortOrder === 'asc' ? '↑' : '↓'}</span>
                                )}
                              </div>
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {rows.length === 0 ? (
                          <tr>
                            <td colSpan={columns.length + 1} className="text-center py-12 text-muted-foreground">
                              {search ? '未找到匹配数据' : '暂无数据'}
                            </td>
                          </tr>
                        ) : (
                          rows.map((row, i) => (
                            <tr key={i} className="border-b hover:bg-muted/30 transition-colors">
                              <td className="p-3 text-xs text-muted-foreground">
                                {(page - 1) * pageSize + i + 1}
                              </td>
                              {columns.map((col) => (
                                <td key={col} className="p-3 max-w-[250px] truncate">
                                  {renderCell(row[col])}
                                </td>
                              ))}
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>

              {/* 分页 */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>共 {total} 条</span>
                  <Separator orientation="vertical" className="h-4" />
                  <Select
                    value={String(pageSize)}
                    onValueChange={(v) => { setPageSize(Number(v)); setPage(1); queryData(selectedTable, 1) }}
                  >
                    <SelectTrigger className="h-8 w-[80px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="10">10</SelectItem>
                      <SelectItem value="20">20</SelectItem>
                      <SelectItem value="50">50</SelectItem>
                      <SelectItem value="100">100</SelectItem>
                    </SelectContent>
                  </Select>
                  <span>条/页</span>
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => handlePageChange(page - 1)}
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                  {generatePagination(page, totalPages).map((p, i) => (
                    <Button
                      key={i}
                      variant={p === page ? 'default' : 'outline'}
                      size="sm"
                      disabled={p === '...'}
                      onClick={() => typeof p === 'number' && handlePageChange(p)}
                      className="min-w-[36px]"
                    >
                      {p}
                    </Button>
                  ))}
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => handlePageChange(page + 1)}
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

// 辅助：渲染表格单元格
function renderCell(value: any): React.ReactNode {
  if (value === null || value === undefined) {
    return <span className="text-muted-foreground/50 italic">null</span>
  }
  if (typeof value === 'boolean') {
    return <Badge variant={value ? 'default' : 'secondary'} className="text-xs">{value ? '是' : '否'}</Badge>
  }
  const str = String(value)
  if (str.startsWith('http')) {
    return (
      <a href={str} target="_blank" rel="noopener noreferrer"
        className="text-primary hover:underline truncate block">
        {str.substring(0, 50)}...
      </a>
    )
  }
  if (str.length > 100) {
    return (
      <span title={str} className="cursor-help">
        {str.substring(0, 100)}...
      </span>
    )
  }
  return <span>{str}</span>
}

// 辅助：生成分页按钮
function generatePagination(current: number, total: number): (number | string)[] {
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const pages: (number | string)[] = [1]
  if (current > 3) pages.push('...')
  for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) {
    pages.push(i)
  }
  if (current < total - 2) pages.push('...')
  pages.push(total)
  return pages
}
