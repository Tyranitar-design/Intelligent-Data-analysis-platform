import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Brain, Play, Download, Trash2 } from 'lucide-react'

const models = [
  { 
    id: 1, 
    name: '客户分类模型', 
    type: '分类',
    algorithm: 'Random Forest',
    accuracy: 0.92,
    status: 'deployed',
    createdAt: '2024-01-15'
  },
  { 
    id: 2, 
    name: '销售预测模型', 
    type: '回归',
    algorithm: 'XGBoost',
    accuracy: 0.88,
    status: 'training',
    createdAt: '2024-01-20'
  },
  { 
    id: 3, 
    name: '情感分析模型', 
    type: 'NLP',
    algorithm: 'BERT',
    accuracy: 0.95,
    status: 'deployed',
    createdAt: '2024-02-01'
  },
]

export default function ModelPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">模型管理</h2>
          <p className="text-muted-foreground">管理和部署您的机器学习模型</p>
        </div>
        <Button>
          <Brain className="mr-2 h-4 w-4" />
          训练新模型
        </Button>
      </div>

      {/* 模型列表 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {models.map((model) => (
          <Card key={model.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">{model.name}</CardTitle>
                <Badge 
                  variant={model.status === 'deployed' ? 'default' : 'secondary'}
                >
                  {model.status === 'deployed' ? '已部署' : '训练中'}
                </Badge>
              </div>
              <CardDescription>{model.algorithm}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex justify-between text-sm">
                <span>准确率</span>
                <span className="font-medium">{(model.accuracy * 100).toFixed(1)}%</span>
              </div>
              <Progress value={model.accuracy * 100} />
              
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-muted-foreground">类型</span>
                  <p className="font-medium">{model.type}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">创建时间</span>
                  <p className="font-medium">{model.createdAt}</p>
                </div>
              </div>
              
              <div className="flex justify-end space-x-2">
                <Button variant="outline" size="sm">
                  <Play className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="sm">
                  <Download className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="sm">
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
