import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Database, RefreshCw, Search } from 'lucide-react'
import { crawlApi } from '@/api/crawl'
import { extractApiError } from '@/api/crawl'
import { useAppStore } from '@/stores/appStore'

export default function DatasetPage() {
  const navigate = useNavigate()
  const { addNotification } = useAppStore()
  const [loading, setLoading] = useState(true)
  const [datasets, setDatasets] = useState<any[]>([])
  const [search, setSearch] = useState('')

  useEffect(() => {
    loadDatasets()
  }, [])

  const loadDatasets = async () => {
    try {
      setLoading(true)
      const res = await crawlApi.listDatasets(100)
      setDatasets(res.data?.datasets || [])
    } catch (e: any) {
      addNotification({ type: 'error', title: '加载失败', description: extractApiError(e) })
    } finally {
      setLoading(false)
    }
  }

  const filteredDatasets = useMemo(() => {
    const keyword = search.trim().toLowerCase()
    if (!keyword) return datasets
    return datasets.filter((dataset) =>
      [dataset.name, dataset.description, dataset.dataset_type, dataset.table_name]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(keyword))
    )
  }, [datasets, search])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">数据集</h2>
          <p className="text-muted-foreground">查看已保存的真实数据集并跳转浏览</p>
        </div>
        <Button variant="outline" onClick={loadDatasets} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          刷新
        </Button>
      </div>

      <div className="flex items-center space-x-2">
        <Search className="h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="搜索数据集..."
          className="max-w-sm"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {filteredDatasets.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <Database className="h-12 w-12 mb-3 opacity-30" />
            <p>{loading ? '正在加载数据集...' : '暂无真实数据集'}</p>
            {!loading && (
              <p className="text-sm mt-2">
                先去“数据采集”完成一次保存，这里就会出现真实数据集。
              </p>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {filteredDatasets.map((dataset) => (
            <Card key={dataset.id}>
              <CardHeader>
                <div className="flex items-center justify-between gap-3">
                  <CardTitle className="text-base">{dataset.name}</CardTitle>
                  <Badge variant="outline">{String(dataset.dataset_type || 'dataset').toUpperCase()}</Badge>
                </div>
                <CardDescription>{dataset.description || '无描述'}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-3 gap-4 text-center">
                  <div>
                    <p className="text-2xl font-bold">{Number(dataset.row_count || 0).toLocaleString()}</p>
                    <p className="text-xs text-muted-foreground">行</p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{dataset.column_count || 0}</p>
                    <p className="text-xs text-muted-foreground">列</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium break-all">{dataset.table_name}</p>
                    <p className="text-xs text-muted-foreground">表名</p>
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  创建时间：{dataset.created_at || '未知'} · 类型：{dataset.dataset_type || 'dataset'}
                </p>
                <div className="flex justify-end space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate(`/data?table=${encodeURIComponent(dataset.table_name)}`)}
                  >
                    预览
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate(`/visualization?table=${encodeURIComponent(dataset.table_name)}`)}
                  >
                    可视化
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
