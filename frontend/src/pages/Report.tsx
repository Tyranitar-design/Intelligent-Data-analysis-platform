import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { FileText, Download, Eye, Plus } from 'lucide-react'

const reports = [
  { 
    id: 1, 
    name: '2024年Q1销售分析报告', 
    type: 'pdf',
    status: 'completed',
    createdAt: '2024-03-31',
    size: '2.5 MB'
  },
  { 
    id: 2, 
    name: '用户行为分析报告', 
    type: 'html',
    status: 'completed',
    createdAt: '2024-03-15',
    size: '1.8 MB'
  },
  { 
    id: 3, 
    name: '市场趋势预测报告', 
    type: 'pdf',
    status: 'generating',
    createdAt: '2024-04-01',
    size: '-'
  },
]

export default function ReportPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">报告中心</h2>
          <p className="text-muted-foreground">生成和管理分析报告</p>
        </div>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          生成报告
        </Button>
      </div>

      {/* 报告列表 */}
      <div className="space-y-4">
        {reports.map((report) => (
          <Card key={report.id}>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <FileText className="h-5 w-5 text-primary" />
                  <div>
                    <CardTitle className="text-base">{report.name}</CardTitle>
                    <CardDescription>
                      创建于 {report.createdAt} · {report.size}
                    </CardDescription>
                  </div>
                </div>
                <Badge 
                  variant={report.status === 'completed' ? 'default' : 'secondary'}
                >
                  {report.status === 'completed' ? '完成' : '生成中'}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex justify-end space-x-2">
                <Button variant="outline" size="sm">
                  <Eye className="h-4 w-4 mr-1" />
                  预览
                </Button>
                <Button variant="outline" size="sm">
                  <Download className="h-4 w-4 mr-1" />
                  下载
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
