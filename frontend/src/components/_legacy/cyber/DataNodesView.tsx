import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Database, Server, TrendingUp, Zap, Newspaper, ShoppingCart,
  Search, Plus, Layers, BarChart3, X, ChevronLeft, ChevronRight,
  RefreshCw, Eye, ArrowLeft,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface StatsData {
  totalData: number;
  stockCount: number;
  energyCount: number;
  newsCount: number;
  ecomCount: number;
}

interface Props {
  stats?: StatsData;
}

// 数据源配置
const DATA_SOURCES = [
  { 
    id: 'stock', 
    name: '股票数据', 
    table: 'stock_data',
    icon: TrendingUp,
    color: 'text-cyber-green',
    borderColor: 'border-cyber-green/30',
    columns: ['id', 'symbol', 'name', 'date', 'open', 'high', 'low', 'close', 'volume'],
  },
  { 
    id: 'energy', 
    name: '能源数据', 
    table: 'energy_data',
    icon: Zap,
    color: 'text-cyber-purple-bright',
    borderColor: 'border-cyber-purple/30',
    columns: ['id', 'province', 'city', 'power_usage', 'date', 'type'],
  },
  { 
    id: 'news', 
    name: '新闻数据', 
    table: 'news_data',
    icon: Newspaper,
    color: 'text-cyber-cyan',
    borderColor: 'border-cyber-cyan/30',
    columns: ['id', 'title', 'source', 'category', 'published_at', 'url'],
  },
  { 
    id: 'ecommerce', 
    name: '电商数据', 
    table: 'ecom_products',
    icon: ShoppingCart,
    color: 'text-slate-200',
    borderColor: 'border-slate-500/30',
    columns: ['id', 'name', 'brand', 'price', 'platform', 'keyword'],
  },
];

const PAGE_SIZE = 15;

export default function DataNodesView({ stats }: Props) {
  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  const [data, setData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [lastUpdate, setLastUpdate] = useState('');

  // 当选择数据源时获取数据
  useEffect(() => {
    if (selectedSource) {
      fetchData(selectedSource, 1, '');
    }
  }, [selectedSource]);

  const fetchData = async (source: string, page: number, search: string) => {
    setLoading(true);
    try {
      const offset = (page - 1) * PAGE_SIZE;
      let url = `/api/v1/analysis/db/data/${source}?limit=${PAGE_SIZE}&offset=${offset}`;
      
      const res = await fetch(url);
      const result = await res.json();
      
      let filteredData = result.data || [];
      
      // 前端搜索过滤
      if (search) {
        const searchLower = search.toLowerCase();
        filteredData = filteredData.filter((item: any) => 
          Object.values(item).some(val => 
            String(val).toLowerCase().includes(searchLower)
          )
        );
      }
      
      setData(filteredData);
      setTotalCount(result.total || filteredData.length);
      setCurrentPage(page);
      setLastUpdate(new Date().toLocaleTimeString('zh-CN'));
    } catch (e) {
      console.error('Failed to fetch data:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    if (selectedSource) {
      fetchData(selectedSource, 1, searchTerm);
    }
  };

  const handlePageChange = (newPage: number) => {
    if (selectedSource) {
      fetchData(selectedSource, newPage, searchTerm);
    }
  };

  const totalPages = Math.ceil(totalCount / PAGE_SIZE);

  // 获取当前数据源配置
  const currentSource = DATA_SOURCES.find(s => s.id === selectedSource);

  // 统计数据
  const displayStats = {
    stock: stats?.stockCount || 0,
    energy: stats?.energyCount || 0,
    news: stats?.newsCount || 0,
    ecommerce: stats?.ecomCount || 0,
  };

  return (
    <div className="flex h-full">
      <div className="flex-1 p-6 flex flex-col gap-6 overflow-hidden">
        {/* 标题栏 */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between"
        >
          <div>
            <h1 className="text-3xl font-display font-bold text-cyber-cyan uppercase tracking-wider">
              数据节点管理
            </h1>
            <p className="text-slate-400 text-sm font-mono mt-1">
              查看和管理本地数据库中的所有数据
            </p>
          </div>
          
          {lastUpdate && selectedSource && (
            <span className="text-xs font-mono text-slate-500">
              更新: {lastUpdate}
            </span>
          )}
        </motion.div>

        {/* 数据源列表 或 详细数据视图 */}
        <AnimatePresence mode="wait">
          {!selectedSource ? (
            // 数据源卡片列表
            <motion.div
              key="sources"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="grid grid-cols-2 gap-6"
            >
              {DATA_SOURCES.map((source, idx) => {
                const Icon = source.icon;
                const count = displayStats[source.id as keyof typeof displayStats];
                
                return (
                  <motion.div
                    key={source.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.1 }}
                    className={cn(
                      'glass-panel p-6 cursor-pointer hover:border-opacity-60 transition-all group',
                      source.borderColor
                    )}
                    onClick={() => setSelectedSource(source.id)}
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className={cn(
                        'w-12 h-12 rounded-lg flex items-center justify-center',
                        'bg-slate-900/50 border border-slate-800',
                        'group-hover:scale-110 transition-transform'
                      )}>
                        <Icon className={source.color} size={24} />
                      </div>
                      <button className="text-xs text-slate-500 hover:text-cyber-cyan flex items-center gap-1">
                        <Eye size={12} />
                        查看详情
                      </button>
                    </div>
                    
                    <h3 className="font-display font-bold text-slate-200 text-lg mb-1">
                      {source.name}
                    </h3>
                    <p className="text-slate-500 text-xs font-mono mb-4">
                      {source.table}
                    </p>
                    
                    <div className="flex items-center justify-between pt-4 border-t border-slate-800">
                      <div>
                        <p className="text-slate-400 text-xs">数据量</p>
                        <p className={cn('text-2xl font-display font-bold', source.color)}>
                          {count.toLocaleString()}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-cyber-green animate-pulse" />
                        <span className="text-xs text-cyber-green">在线</span>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </motion.div>
          ) : (
            // 详细数据视图
            <motion.div
              key="detail"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="flex-1 flex flex-col gap-4 overflow-hidden"
            >
              {/* 返回按钮和标题 */}
              <div className="flex items-center justify-between">
                <button
                  onClick={() => {
                    setSelectedSource(null);
                    setSearchTerm('');
                    setData([]);
                  }}
                  className="flex items-center gap-2 text-slate-400 hover:text-cyber-cyan transition-colors"
                >
                  <ArrowLeft size={18} />
                  <span className="text-sm font-mono">返回数据源列表</span>
                </button>
                
                <div className="flex items-center gap-3">
                  {/* 搜索框 */}
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={14} />
                    <input
                      type="text"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                      placeholder="搜索数据..."
                      className="bg-slate-900/50 border border-slate-700 rounded pl-9 pr-4 py-2 text-sm text-slate-200 w-64 focus:border-cyber-cyan focus:outline-none"
                    />
                  </div>
                  
                  <button
                    onClick={handleSearch}
                    className="px-4 py-2 bg-cyber-cyan/20 border border-cyber-cyan/50 text-cyber-cyan rounded text-sm font-bold hover:bg-cyber-cyan/30 transition-colors"
                  >
                    搜索
                  </button>
                  
                  <button
                    onClick={() => fetchData(selectedSource, currentPage, searchTerm)}
                    disabled={loading}
                    className="px-4 py-2 bg-slate-800 border border-slate-700 text-slate-300 rounded text-sm hover:border-cyber-cyan/50 transition-colors flex items-center gap-2"
                  >
                    <RefreshCw className={loading ? 'animate-spin' : ''} size={14} />
                    刷新
                  </button>
                </div>
              </div>

              {/* 数据表头 */}
              {currentSource && (
                <div className="flex items-center gap-2">
                  <currentSource.icon className={currentSource.color} size={18} />
                  <h2 className="font-display font-bold text-slate-200">
                    {currentSource.name}
                  </h2>
                  <span className="text-slate-500 text-sm font-mono">
                    共 {totalCount.toLocaleString()} 条记录
                  </span>
                </div>
              )}

              {/* 数据表格 */}
              <div className="flex-1 glass-panel overflow-hidden flex flex-col">
                {loading ? (
                  <div className="flex-1 flex items-center justify-center">
                    <RefreshCw className="animate-spin text-cyber-cyan" size={32} />
                  </div>
                ) : data.length === 0 ? (
                  <div className="flex-1 flex items-center justify-center text-slate-500">
                    <div className="text-center">
                      <Database size={40} className="mx-auto mb-3 opacity-30" />
                      <p className="font-mono">暂无数据</p>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="overflow-auto flex-1">
                      <table className="w-full text-sm">
                        <thead className="bg-slate-900/50 sticky top-0">
                          <tr>
                            {Object.keys(data[0] || {}).map((key) => (
                              <th
                                key={key}
                                className="px-4 py-3 text-left text-xs font-display font-bold text-slate-400 uppercase tracking-wider border-b border-slate-800"
                              >
                                {key}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/50">
                          {data.map((row, idx) => (
                            <motion.tr
                              key={idx}
                              initial={{ opacity: 0, y: 10 }}
                              animate={{ opacity: 1, y: 0 }}
                              transition={{ delay: idx * 0.02 }}
                              className="hover:bg-cyber-cyan/5 transition-colors"
                            >
                              {Object.values(row).map((val: any, i) => (
                                <td
                                  key={i}
                                  className="px-4 py-2 text-slate-300 font-mono text-xs whitespace-nowrap max-w-[200px] truncate"
                                  title={String(val)}
                                >
                                  {typeof val === 'number' ? val.toLocaleString() : String(val)}
                                </td>
                              ))}
                            </motion.tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* 分页 */}
                    <div className="flex items-center justify-between p-4 border-t border-slate-800">
                      <div className="text-xs text-slate-500 font-mono">
                        显示 {(currentPage - 1) * PAGE_SIZE + 1} - {Math.min(currentPage * PAGE_SIZE, totalCount)} 条，共 {totalCount} 条
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handlePageChange(currentPage - 1)}
                          disabled={currentPage <= 1}
                          className="p-2 rounded border border-slate-700 text-slate-400 hover:border-cyber-cyan/50 hover:text-cyber-cyan disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                        >
                          <ChevronLeft size={16} />
                        </button>
                        
                        <div className="flex items-center gap-1">
                          {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                            let pageNum;
                            if (totalPages <= 5) {
                              pageNum = i + 1;
                            } else if (currentPage <= 3) {
                              pageNum = i + 1;
                            } else if (currentPage >= totalPages - 2) {
                              pageNum = totalPages - 4 + i;
                            } else {
                              pageNum = currentPage - 2 + i;
                            }
                            
                            return (
                              <button
                                key={i}
                                onClick={() => handlePageChange(pageNum)}
                                className={cn(
                                  'w-8 h-8 rounded text-sm font-mono transition-colors',
                                  pageNum === currentPage
                                    ? 'bg-cyber-cyan/20 border border-cyber-cyan/50 text-cyber-cyan'
                                    : 'border border-slate-700 text-slate-400 hover:border-cyber-cyan/50'
                                )}
                              >
                                {pageNum}
                              </button>
                            );
                          })}
                        </div>
                        
                        <button
                          onClick={() => handlePageChange(currentPage + 1)}
                          disabled={currentPage >= totalPages}
                          className="p-2 rounded border border-slate-700 text-slate-400 hover:border-cyber-cyan/50 hover:text-cyber-cyan disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                        >
                          <ChevronRight size={16} />
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 底部统计 */}
        {!selectedSource && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="glass-panel p-4 mt-auto"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Database className="text-cyber-cyan" size={16} />
                <span className="text-sm text-slate-400 font-mono">
                  数据库总记录: <span className="text-cyber-cyan font-bold">{(stats?.totalData || 0).toLocaleString()}</span> 条
                </span>
              </div>
              <div className="text-xs text-slate-500">
                点击数据源卡片查看详细数据
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}