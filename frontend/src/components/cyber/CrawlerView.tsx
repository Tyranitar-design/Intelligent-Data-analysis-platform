import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Database, PlayCircle, RefreshCw, Download, Activity, CheckCircle,
  AlertTriangle, Clock, TrendingUp, Zap, Newspaper, ShoppingCart,
  X, ChevronDown, ChevronUp
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface CrawlTask {
  id: number;
  source_name: string;
  status: string;
  created_at: string;
  progress?: number;
}

interface CrawlResult {
  source: string;
  type: string;
  count: number;
  status: string;
  message: string;
  details?: any[];
  time?: string;
}

export default function CrawlerView() {
  const [loading, setLoading] = useState(false);
  const [tasks, setTasks] = useState<CrawlTask[]>([]);
  const [results, setResults] = useState<CrawlResult[]>([]);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [countdown, setCountdown] = useState(30);
  const [expandedResult, setExpandedResult] = useState<number | null>(null);

  // 统计数据
  const [stats, setStats] = useState({
    totalRecords: 0,
    stockRecords: 0,
    energyRecords: 0,
    newsRecords: 0,
    ecomRecords: 0,
  });

  useEffect(() => {
    fetchTasks();
    fetchStats();
  }, []);

  // 自动刷新定时器
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (autoRefresh) {
      interval = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) {
            crawlAllData();
            return 30;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const fetchTasks = async () => {
    try {
      const res = await fetch('/api/v1/crawl/tasks');
      const data = await res.json();
      setTasks(data || []);
    } catch (e) {
      console.error('Failed to fetch tasks:', e);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/v1/analysis/overview');
      const data = await res.json();
      setStats({
        totalRecords: data.total_records || 0,
        stockRecords: data.stock_records || 0,
        energyRecords: data.energy_records || 0,
        newsRecords: data.news_records || 0,
        ecomRecords: data.ecom_products || 0,
      });
    } catch (e) {
      console.error('Failed to fetch stats:', e);
    }
  };

  // 爬取所有数据
  const crawlAllData = async () => {
    setLoading(true);
    setResults([]);
    
    const crawlTasks = [
      { name: '股票数据', type: 'stock', fn: () => crawlStockData() },
      { name: '新闻数据', type: 'news', fn: () => crawlNewsData() },
      { name: '能源数据', type: 'energy', fn: () => crawlEnergyData() },
    ];

    for (const task of crawlTasks) {
      try {
        const result = await task.fn();
        setResults(prev => [...prev, result]);
      } catch (e) {
        setResults(prev => [...prev, {
          source: task.name,
          type: task.type,
          count: 0,
          status: 'error',
          message: String(e),
          time: new Date().toLocaleTimeString('zh-CN'),
        }]);
      }
    }

    // 刷新统计和任务
    await fetchStats();
    await fetchTasks();
    setLoading(false);
  };

  const crawlStockData = async (): Promise<CrawlResult> => {
    const startTime = Date.now();
    try {
      const stocks = ['600519', '601318', '000001', '600036'];
      const details: any[] = [];
      let total = 0;
      
      for (const code of stocks) {
        const res = await fetch(`/api/v1/crawl/finance/stock/${code}?days=30`);
        const data = await res.json();
        const count = data.count || 0;
        total += count;
        details.push({
          code: code,
          name: getStockName(code),
          count: count,
          status: count > 0 ? 'success' : 'failed',
        });
      }
      
      return {
        source: '股票数据',
        type: 'stock',
        count: total,
        status: 'success',
        message: `成功爬取 ${stocks.length} 只股票，共 ${total} 条数据`,
        details: details,
        time: new Date().toLocaleTimeString('zh-CN'),
      };
    } catch (e) {
      return {
        source: '股票数据',
        type: 'stock',
        count: 0,
        status: 'error',
        message: String(e),
        time: new Date().toLocaleTimeString('zh-CN'),
      };
    }
  };

  const crawlNewsData = async (): Promise<CrawlResult> => {
    try {
      const res = await fetch('/api/v1/crawl/news/tech?per_page=20');
      const data = await res.json();
      const count = data.count || 20;
      
      const details = (data.data || []).slice(0, 5).map((item: any) => ({
        title: item.title || '未知标题',
        source: item.source || '36kr',
        time: item.published_at || '',
      }));
      
      return {
        source: '科技新闻',
        type: 'news',
        count: count,
        status: 'success',
        message: `成功爬取 ${count} 条科技新闻`,
        details: details,
        time: new Date().toLocaleTimeString('zh-CN'),
      };
    } catch (e) {
      return {
        source: '科技新闻',
        type: 'news',
        count: 0,
        status: 'error',
        message: String(e),
        time: new Date().toLocaleTimeString('zh-CN'),
      };
    }
  };

  const crawlEnergyData = async (): Promise<CrawlResult> => {
    try {
      const res = await fetch('/api/v1/crawl/finance/power-stocks');
      const data = await res.json();
      const count = data.count || 0;
      
      return {
        source: '能源数据',
        type: 'energy',
        count: count,
        status: count > 0 ? 'success' : 'warning',
        message: count > 0 ? `成功爬取 ${count} 条能源数据` : '暂无新数据',
        details: [],
        time: new Date().toLocaleTimeString('zh-CN'),
      };
    } catch (e) {
      return {
        source: '能源数据',
        type: 'energy',
        count: 0,
        status: 'error',
        message: String(e),
        time: new Date().toLocaleTimeString('zh-CN'),
      };
    }
  };

  const getStockName = (code: string): string => {
    const names: Record<string, string> = {
      '600519': '贵州茅台',
      '601318': '中国平安',
      '000001': '平安银行',
      '600036': '招商银行',
    };
    return names[code] || code;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success': return <CheckCircle className="text-cyber-green" size={18} />;
      case 'error': return <AlertTriangle className="text-cyber-red" size={18} />;
      case 'warning': return <AlertTriangle className="text-yellow-500" size={18} />;
      default: return <Activity className="text-slate-400" size={18} />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'text-cyber-green';
      case 'error': return 'text-cyber-red';
      case 'warning': return 'text-yellow-500';
      default: return 'text-slate-400';
    }
  };

  return (
    <div className="flex flex-col h-full p-6 gap-6 overflow-y-auto pb-20">
      {/* 标题 */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <Database className="text-cyber-cyan" size={24} />
          <h1 className="text-3xl font-display font-bold text-cyber-cyan uppercase tracking-wider">
            数据爬取中心
          </h1>
        </div>
        
        {/* 自动刷新控制 */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={cn(
              'px-4 py-2 rounded font-display font-bold text-xs uppercase tracking-widest transition-all',
              autoRefresh
                ? 'bg-cyber-green/20 border border-cyber-green/50 text-cyber-green'
                : 'bg-slate-800 border border-slate-700 text-slate-400 hover:border-cyber-cyan/50'
            )}
          >
            {autoRefresh ? `自动刷新 ${countdown}s` : '开启自动刷新'}
          </button>
          
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={crawlAllData}
            disabled={loading}
            className="px-6 py-2 bg-cyber-cyan/20 border border-cyber-cyan/50 text-cyber-cyan font-display font-bold text-xs uppercase tracking-widest hover:bg-cyber-cyan/30 transition-all rounded disabled:opacity-50 flex items-center gap-2"
          >
            {loading ? (
              <RefreshCw className="animate-spin" size={16} />
            ) : (
              <Download size={16} />
            )}
            {loading ? '爬取中...' : '一键爬取全部'}
          </motion.button>
        </div>
      </motion.div>

      {/* 数据统计 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid grid-cols-5 gap-4"
      >
        <div className="glass-panel p-4 text-center">
          <Database className="text-cyber-cyan mx-auto mb-2" size={20} />
          <p className="text-2xl font-display font-bold text-cyber-cyan">{stats.totalRecords.toLocaleString()}</p>
          <p className="text-xs text-slate-400 font-mono">数据总量</p>
        </div>
        <div className="glass-panel p-4 text-center">
          <TrendingUp className="text-cyber-green mx-auto mb-2" size={20} />
          <p className="text-2xl font-display font-bold text-cyber-green">{stats.stockRecords.toLocaleString()}</p>
          <p className="text-xs text-slate-400 font-mono">股票数据</p>
        </div>
        <div className="glass-panel p-4 text-center">
          <Zap className="text-cyber-purple-bright mx-auto mb-2" size={20} />
          <p className="text-2xl font-display font-bold text-cyber-purple-bright">{stats.energyRecords.toLocaleString()}</p>
          <p className="text-xs text-slate-400 font-mono">能源数据</p>
        </div>
        <div className="glass-panel p-4 text-center">
          <Newspaper className="text-cyber-cyan mx-auto mb-2" size={20} />
          <p className="text-2xl font-display font-bold text-slate-200">{stats.newsRecords.toLocaleString()}</p>
          <p className="text-xs text-slate-400 font-mono">新闻数据</p>
        </div>
        <div className="glass-panel p-4 text-center">
          <ShoppingCart className="text-cyber-red mx-auto mb-2" size={20} />
          <p className="text-2xl font-display font-bold text-cyber-red">{stats.ecomRecords.toLocaleString()}</p>
          <p className="text-xs text-slate-400 font-mono">电商数据</p>
        </div>
      </motion.div>

      {/* 爬取结果 - 详细展示 */}
      {results.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel p-4"
        >
          <h3 className="font-display font-bold text-slate-200 mb-4 flex items-center gap-2">
            <Activity className="text-cyber-cyan" size={16} />
            爬取结果详情
          </h3>
          <div className="space-y-3">
            {results.map((result, idx) => (
              <div key={idx} className="bg-slate-900/50 rounded-lg overflow-hidden">
                {/* 结果头部 */}
                <div 
                  className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-800/50 transition-colors"
                  onClick={() => setExpandedResult(expandedResult === idx ? null : idx)}
                >
                  <div className="flex items-center gap-3">
                    {getStatusIcon(result.status)}
                    <div>
                      <span className="font-display font-bold text-slate-200">{result.source}</span>
                      <span className="ml-2 text-xs text-slate-500 font-mono">({result.type})</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className={cn('text-sm font-mono font-bold', getStatusColor(result.status))}>
                      +{result.count} 条
                    </span>
                    <span className="text-xs text-slate-500 font-mono">{result.time}</span>
                    {result.details && result.details.length > 0 && (
                      expandedResult === idx ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />
                    )}
                  </div>
                </div>
                
                {/* 详细内容 */}
                {expandedResult === idx && result.details && result.details.length > 0 && (
                  <div className="border-t border-slate-800 p-4 bg-slate-950/50">
                    {result.type === 'stock' && (
                      <div className="grid grid-cols-2 gap-2">
                        {result.details.map((item: any, i: number) => (
                          <div key={i} className="flex items-center justify-between bg-slate-900/50 rounded p-2">
                            <div className="flex items-center gap-2">
                              <span className="text-cyber-cyan font-mono text-xs">{item.code}</span>
                              <span className="text-slate-300 text-sm">{item.name}</span>
                            </div>
                            <span className={cn('text-xs font-mono', item.status === 'success' ? 'text-cyber-green' : 'text-cyber-red')}>
                              {item.count} 条
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {result.type === 'news' && (
                      <div className="space-y-2">
                        {result.details.map((item: any, i: number) => (
                          <div key={i} className="bg-slate-900/50 rounded p-2">
                            <p className="text-sm text-slate-300 truncate">{item.title}</p>
                            <p className="text-xs text-slate-500 mt-1">{item.source} · {item.time}</p>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    <p className="text-xs text-slate-400 mt-3 pt-3 border-t border-slate-800">
                      {result.message}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* 任务历史 - 完整展示 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="glass-panel p-4 flex-1"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-display font-bold text-slate-200 flex items-center gap-2">
            <Clock className="text-cyber-purple-bright" size={16} />
            爬取任务历史
          </h3>
          <button 
            onClick={fetchTasks}
            className="text-xs text-cyber-cyan hover:text-cyber-cyan-bright flex items-center gap-1"
          >
            <RefreshCw size={12} />
            刷新
          </button>
        </div>
        
        {tasks.length === 0 ? (
          <div className="text-center text-slate-500 py-8">
            <Database size={40} className="mx-auto mb-3 opacity-30" />
            <p className="font-mono text-sm">暂无爬取任务</p>
            <p className="text-xs mt-1">点击上方按钮开始爬取数据</p>
          </div>
        ) : (
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {tasks.slice(0, 15).map((task) => (
              <div key={task.id} className="flex items-center justify-between bg-slate-900/50 rounded p-3 hover:bg-slate-800/50 transition-colors">
                <div className="flex items-center gap-3">
                  <span className={cn(
                    'w-2 h-2 rounded-full',
                    task.status === 'completed' ? 'bg-cyber-green' :
                    task.status === 'running' ? 'bg-cyber-cyan animate-pulse' :
                    task.status === 'failed' ? 'bg-cyber-red' : 'bg-slate-500'
                  )} />
                  <div>
                    <span className="text-sm text-slate-300">{task.source_name}</span>
                    <p className="text-xs text-slate-500 font-mono">ID: {task.id}</p>
                  </div>
                </div>
                <div className="text-right">
                  <span className={cn(
                    'text-xs font-mono px-2 py-0.5 rounded',
                    task.status === 'completed' ? 'bg-cyber-green/20 text-cyber-green' :
                    task.status === 'running' ? 'bg-cyber-cyan/20 text-cyber-cyan' :
                    task.status === 'failed' ? 'bg-cyber-red/20 text-cyber-red' : 'bg-slate-700 text-slate-400'
                  )}>
                    {task.status === 'completed' ? '已完成' :
                     task.status === 'running' ? '运行中' :
                     task.status === 'failed' ? '失败' : task.status}
                  </span>
                  <p className="text-xs text-slate-500 mt-1">
                    {task.created_at ? new Date(task.created_at).toLocaleString('zh-CN') : '-'}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
}