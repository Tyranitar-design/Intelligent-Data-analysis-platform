import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { FileText, Loader2, Eye, Trash2, Database } from 'lucide-react'
import { reportApi } from '@/api/analysis'
import { extractApiError } from '@/api/crawl'
import { useAppStore } from '@/stores/appStore'

export default function ReportsPage() {
  const [searchParams] = useSearchParams()
  const { addNotification } = useAppStore()
  const [loading, setLoading] = useState(false)
  const [reports, setReports] = useState<any[]>([])
  const [reportFormat, setReportFormat] = useState<'markdown' | 'html'>('markdown')
  const [selectedReport, setSelectedReport] = useState<any>(null)
  const [generating, setGenerating] = useState(false)
  const [sourceTableHint, setSourceTableHint] = useState(searchParams.get('sourceTable') || '')

  useEffect(() => {
    fetchReports()
  }, [])

  useEffect(() => {
    const sourceTable = searchParams.get('sourceTable')
    if (sourceTable) {
      setSourceTableHint(sourceTable)
    }
  }, [searchParams])

  const fetchReports = async () => {
    try {
      setLoading(true)
      const res = await reportApi.list()
      const nextReports = res.data?.reports || res.data || []
      setReports(nextReports)
      if (!selectedReport && nextReports.length > 0) {
        setSelectedReport(nextReports[0])
      }
    } catch (e: any) {
      addNotification({ type: 'error', title: '加载失败', description: extractApiError(e) })
    } finally {
      setLoading(false)
    }
  }

  const generateReport = async () => {
    if (!sourceTableHint.trim()) {
      addNotification({ type: 'warning', title: '请先提供数据来源', description: '请先输入真实数据表名，或从分析页跳转过来。' })
      return
    }
    try {
      setGenerating(true)
      const reportType = reportFormat === 'html' ? 'comprehensive' : 'eda'
      const res = await reportApi.generateFromTable({
        table_name: sourceTableHint,
        report_type: reportType,
      })
      addNotification({
        type: 'success',
        title: '报告生成完成',
        description: `已基于真实数据表 ${sourceTableHint} 生成报告`,
      })
      await fetchReports()
    } catch (e: any) {
      addNotification({ type: 'error', title: '生成失败', description: extractApiError(e) })
    } finally {
      setGenerating(false)
    }
  }

  const viewReport = async (id: number) => {
    try {
      const res = await reportApi.get(id)
      setSelectedReport(res.data)
    } catch (e: any) {
      addNotification({ type: 'error', title: '加载失败', description: extractApiError(e) })
    }
  }

  const deleteReport = async (id: number) => {
    try {
      await reportApi.delete(id)
      setReports(reports.filter((r) => r.id !== id))
      if (selectedReport?.id === id) setSelectedReport(null)
      addNotification({ type: 'info', title: '报告已删除' })
    } catch (e: any) {
      addNotification({ type: 'error', title: '删除失败', description: extractApiError(e) })
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">报告中心</h2>
          <p className="text-muted-foreground">自动分析报告 · Markdown/HTML · 导出分享</p>
        </div>
        <div className="flex items-center gap-2">
          <Input
            placeholder="输入来源标识，例如 table 名"
            className="w-56"
            value={sourceTableHint}
            onChange={(e) => setSourceTableHint(e.target.value)}
          />
          <Select value={reportFormat} onValueChange={(v: any) => setReportFormat(v)}>
            <SelectTrigger className="w-32"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="markdown">Markdown</SelectItem>
              <SelectItem value="html">HTML</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={generateReport} disabled={generating}>
            {generating ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <FileText className="h-4 w-4 mr-2" />}
            生成报告
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* 报告列表 */}
        <Card>
          <CardHeader>
            <CardTitle>历史报告</CardTitle>
          </CardHeader>
          <CardContent>
            {reports.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <FileText className="h-10 w-10 mb-2 opacity-30" />
                <p className="text-sm">暂无报告</p>
                <p className="text-xs">可从分析页跳转，或直接输入真实数据表名生成报告</p>
              </div>
            ) : (
              <div className="space-y-2">
                {reports.map((report) => (
                  <div key={report.id} className="flex items-center justify-between p-3 rounded-lg border">
                    <div>
                      <p className="font-medium text-sm">{report.name || `报告 #${report.id}`}</p>
                      <p className="text-xs text-muted-foreground">{report.created_at}</p>
                      {report.meta?.table_name && (
                        <p className="text-xs text-muted-foreground mt-1">
                          数据表：{report.meta.table_name}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-1">
                      <Button variant="ghost" size="sm" onClick={() => viewReport(report.id)}>
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => deleteReport(report.id)}>
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* 报告预览 */}
        <Card>
          <CardHeader>
            <CardTitle>报告预览</CardTitle>
          </CardHeader>
          <CardContent>
            {selectedReport ? (
              <div className="space-y-4">
                <div className="rounded-lg border p-4 bg-muted/20">
                  <div className="flex items-center gap-2 mb-2">
                    <Database className="h-4 w-4 text-primary" />
                    <span className="text-sm font-medium">报告元信息</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>名称：{selectedReport.name}</div>
                    <div>类型：{selectedReport.report_type}</div>
                    <div>格式：{selectedReport.format}</div>
                    <div>创建时间：{selectedReport.created_at}</div>
                  </div>
                  {selectedReport.meta?.table_name && (
                    <p className="text-xs text-muted-foreground mt-2">
                      来源数据表：{selectedReport.meta.table_name}
                    </p>
                  )}
                </div>

                {selectedReport.html_content ? (
                  <div className="prose prose-sm dark:prose-invert max-w-none">
                    <div dangerouslySetInnerHTML={{ __html: selectedReport.html_content }} />
                  </div>
                ) : (
                  <ReportStructuredPreview report={selectedReport} />
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <FileText className="h-10 w-10 mb-2 opacity-30" />
                <p className="text-sm">选择报告查看内容</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function ReportStructuredPreview({ report }: { report: any }) {
  let parsedContent: any = null

  try {
    parsedContent = report.content ? JSON.parse(report.content) : null
  } catch {
    parsedContent = null
  }

  if (!parsedContent) {
    return (
      <pre className="whitespace-pre-wrap text-sm font-mono rounded-lg bg-muted/50 p-3 overflow-auto">
        {report.content || JSON.stringify(report, null, 2)}
      </pre>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold">{parsedContent.title || report.name}</h3>
        <p className="text-sm text-muted-foreground">
          {parsedContent.dataset_name ? `数据集：${parsedContent.dataset_name}` : ''}
          {parsedContent.table_name ? ` · 数据表：${parsedContent.table_name}` : ''}
        </p>
      </div>

      {parsedContent.sections?.length ? (
        <div className="space-y-4">
          {parsedContent.sections.map((section: any, index: number) => (
            <div key={`${section.title}-${index}`} className="rounded-lg border p-4">
              <h4 className="font-medium mb-2">{section.title}</h4>
              <div className="space-y-1 text-sm text-muted-foreground">
                {(section.content || []).map((line: string, lineIndex: number) => (
                  <p key={lineIndex}>{line}</p>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <pre className="whitespace-pre-wrap text-sm font-mono rounded-lg bg-muted/50 p-3 overflow-auto">
          {JSON.stringify(parsedContent, null, 2)}
        </pre>
      )}
    </div>
  )
}
