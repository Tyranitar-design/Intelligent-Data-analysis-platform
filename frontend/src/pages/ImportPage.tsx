import { useState, useRef } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  Upload, FileSpreadsheet, FileJson, FileText, Database,
  Loader2, CheckCircle, AlertCircle, Table, Save,
} from 'lucide-react'
import { crawlApi } from '@/api/crawl'
import { useAppStore } from '@/stores/appStore'

const FORMAT_CONFIG = {
  csv: { icon: FileText, label: 'CSV', color: 'text-green-600', ext: '.csv' },
  excel: { icon: FileSpreadsheet, label: 'Excel', color: 'text-blue-600', ext: '.xlsx' },
  json: { icon: FileJson, label: 'JSON', color: 'text-yellow-600', ext: '.json' },
  parquet: { icon: Database, label: 'Parquet', color: 'text-purple-600', ext: '.parquet' },
  html: { icon: Table, label: 'HTML 表格', color: 'text-orange-600', ext: '.html' },
}

export default function ImportPage() {
  const { addNotification } = useAppStore()
  const [file, setFile] = useState<File | null>(null)
  const [filePath, setFilePath] = useState('')
  const [fileType, setFileType] = useState('')
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<any>(null)
  const [datasetName, setDatasetName] = useState('')
  const [datasetDesc, setDatasetDesc] = useState('')
  const [saving, setSaving] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0]
    if (!selected) return
    setFile(selected)
    setFilePath(selected.name)
    // 推断类型
    const ext = selected.name.split('.').pop()?.toLowerCase()
    const typeMap: Record<string, string> = {
      csv: 'csv',
      xlsx: 'excel',
      xls: 'excel',
      json: 'json',
      parquet: 'parquet',
      html: 'html',
      htm: 'html',
    }
    setFileType(typeMap[ext || ''] || '')
    setDatasetName(selected.name.replace(/\.[^/.]+$/, ''))
    setImportResult(null)
  }

  const handleImport = async () => {
    if (!filePath) return
    setImporting(true)
    setImportResult(null)
    try {
      // 由于前端无法直接访问文件系统路径，我们需要用 FormData 上传
      // 但当前后端 API 接收的是 file_path，所以我们需要调整
      // 这里先模拟：读取文件内容作为文本导入
      const res = await crawlApi.importFile({
        file_path: filePath,
        file_type: fileType || undefined,
      })
      setImportResult(res.data)
      addNotification({
        type: res.data?.success ? 'success' : 'error',
        title: res.data?.success ? '导入成功' : '导入失败',
        description: res.data?.message || '',
      })
    } catch (e: any) {
      addNotification({ type: 'error', title: '导入失败', description: e.message })
    } finally {
      setImporting(false)
    }
  }

  const handleSaveDataset = async () => {
    if (!importResult?.data || !datasetName.trim()) return
    setSaving(true)
    try {
      const res = await crawlApi.saveDataset({
        name: datasetName,
        description: datasetDesc,
        columns: importResult.columns,
        data: importResult.data,
        source_url: filePath,
        source_type: 'import',
      })
      if (res.data?.success) {
        addNotification({ type: 'success', title: '保存成功', description: res.data.message })
      } else {
        addNotification({ type: 'error', title: '保存失败', description: res.data?.error || '' })
      }
    } catch (e: any) {
      addNotification({ type: 'error', title: '保存失败', description: e.message })
    } finally {
      setSaving(false)
    }
  }

  const detectedFormat = fileType ? FORMAT_CONFIG[fileType as keyof typeof FORMAT_CONFIG] : null

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div>
        <h2 className="text-3xl font-bold tracking-tight">数据导入</h2>
        <p className="text-muted-foreground">CSV · Excel · JSON · Parquet · HTML 表格</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* 导入区 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="w-5 h-5 text-primary" />
              导入文件
            </CardTitle>
            <CardDescription>
              支持 CSV、Excel、JSON、Parquet、HTML 表格
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* 文件选择 */}
            <div className="space-y-2">
              <Label>选择文件</Label>
              <div className="flex gap-2">
                <Input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,.xlsx,.xls,.json,.parquet,.html,.htm"
                  onChange={handleFileSelect}
                  className="hidden"
                />
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Upload className="w-4 h-4 mr-2" />
                  {file ? file.name : '点击选择文件'}
                </Button>
              </div>
              {detectedFormat && (
                <div className="flex items-center gap-2 text-sm">
                  <detectedFormat.icon className={`w-4 h-4 ${detectedFormat.color}`} />
                  <span>检测到格式: {detectedFormat.label}</span>
                </div>
              )}
            </div>

            {/* 文件路径（用于后端） */}
            <div className="space-y-2">
              <Label>文件路径</Label>
              <Input
                placeholder="D:\\data\\example.csv"
                value={filePath}
                onChange={(e) => setFilePath(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                请输入文件的完整路径，后端将从此路径读取文件
              </p>
            </div>

            {/* 格式选择 */}
            <div className="space-y-2">
              <Label>格式（可选，自动检测）</Label>
              <div className="flex flex-wrap gap-2">
                {Object.entries(FORMAT_CONFIG).map(([key, config]) => (
                  <Button
                    key={key}
                    variant={fileType === key ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => setFileType(key)}
                  >
                    <config.icon className={`w-3 h-3 mr-1 ${config.color}`} />
                    {config.label}
                  </Button>
                ))}
              </div>
            </div>

            <Button
              className="w-full"
              onClick={handleImport}
              disabled={importing || !filePath.trim()}
            >
              {importing ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Upload className="w-4 h-4 mr-2" />
              )}
              开始导入
            </Button>
          </CardContent>
        </Card>

        {/* 结果区 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Table className="w-5 h-5 text-primary" />
              导入结果
              {importResult && (
                <Badge variant={importResult.success ? 'default' : 'destructive'} className="ml-2">
                  {importResult.row_count || 0} 行
                </Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!importResult ? (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Upload className="w-8 h-8 mb-2 opacity-30" />
                <p className="text-sm">选择文件并导入后查看结果</p>
              </div>
            ) : !importResult.success ? (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <AlertCircle className="w-8 h-8 mb-2 text-destructive" />
                <p className="text-sm">{importResult.error || '导入失败'}</p>
              </div>
            ) : (
              <div className="space-y-4">
                {/* 统计 */}
                <div className="grid grid-cols-3 gap-2 text-sm">
                  <div className="border rounded p-2 text-center">
                    <div className="text-lg font-bold">{importResult.row_count}</div>
                    <div className="text-xs text-muted-foreground">行数</div>
                  </div>
                  <div className="border rounded p-2 text-center">
                    <div className="text-lg font-bold">{importResult.column_count}</div>
                    <div className="text-xs text-muted-foreground">列数</div>
                  </div>
                  <div className="border rounded p-2 text-center">
                    <div className="text-lg font-bold">{importResult.source_type}</div>
                    <div className="text-xs text-muted-foreground">来源</div>
                  </div>
                </div>

                {/* 字段列表 */}
                <div className="space-y-2">
                  <Label className="text-xs">字段</Label>
                  <div className="flex flex-wrap gap-1">
                    {importResult.columns?.map((col: string) => (
                      <Badge key={col} variant="secondary" className="text-xs">{col}</Badge>
                    ))}
                  </div>
                </div>

                <Separator />

                {/* 保存为数据集 */}
                <div className="space-y-2">
                  <Label>保存为数据集</Label>
                  <Input
                    placeholder="数据集名称"
                    value={datasetName}
                    onChange={(e) => setDatasetName(e.target.value)}
                  />
                  <Textarea
                    placeholder="数据集描述（可选）"
                    value={datasetDesc}
                    onChange={(e) => setDatasetDesc(e.target.value)}
                    rows={2}
                  />
                  <Button
                    className="w-full"
                    onClick={handleSaveDataset}
                    disabled={saving || !datasetName.trim()}
                  >
                    {saving ? (
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Save className="w-4 h-4 mr-2" />
                    )}
                    保存为数据集
                  </Button>
                </div>

                <Separator />

                {/* 数据预览 */}
                <Label className="text-xs">数据预览（前 20 行）</Label>
                <ScrollArea className="h-64">
                  <div className="space-y-2">
                    {importResult.data?.slice(0, 20).map((row: any, i: number) => (
                      <div key={i} className="border rounded p-2 text-sm bg-muted/20">
                        {Object.entries(row).map(([k, v]) => (
                          <div key={k} className="flex gap-2 py-0.5">
                            <span className="font-medium text-muted-foreground min-w-[80px]">{k}:</span>
                            <span className="truncate">{String(v)}</span>
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
