import { useEffect, useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { BarChart, Bar, LineChart, Line, PieChart, Pie, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Brain, TrendingUp, Zap, Activity, Database, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/utils';

// 赛博朋克配色
const COLORS = ['#00dbe7', '#7701d0', '#2ae500', '#ffb4ab', '#74f5ff'];

interface AnalysisData {
  stockData?: any[];
  energyData?: any[];
  newsData?: any[];
  stats?: any;
}

export default function IntelligenceView() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<AnalysisData>({});
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [countdown, setCountdown] = useState(30);
  const [lastUpdate, setLastUpdate] = useState('');
  
  // 股票数据统计
  const [stockStats, setStockStats] = useState<any[]>([]);
  // 能源数据统计
  const [energyStats, setEnergyStats] = useState<any[]>([]);
  // 新闻分类统计
  const [newsStats, setNewsStats] = useState<any[]>([]);

  useEffect(() => {
    fetchAnalysisData();
  }, []);

  // 自动刷新
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (autoRefresh) {
      interval = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) {
            fetchAnalysisData();
            return 30;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const fetchAnalysisData = async () => {
    try {
      setLoading(true);
      
      // 先获取总览统计
      const overviewRes = await fetch('/api/v1/analysis/overview');
      const overview = await overviewRes.json();
      
      // 获取股票数据（增加数量）
      const stockRes = await fetch('/api/v1/analysis/db/data/stock?limit=500');
      const stockData = await stockRes.json();
      
      // 获取能源数据（增加数量）
      const energyRes = await fetch('/api/v1/analysis/db/data/energy?limit=500');
      const energyData = await energyRes.json();
      
      // 获取新闻数据
      const newsRes = await fetch('/api/v1/analysis/db/data/news?limit=100');
      const newsData = await newsRes.json();
      
      // 处理股票数据统计
      if (stockData.data && stockData.data.length > 0) {
        const stockAgg = processStockData(stockData.data);
        setStockStats(stockAgg);
      }
      
      // 处理能源数据统计
      if (energyData.data && energyData.data.length > 0) {
        const energyAgg = processEnergyData(energyData.data);
        setEnergyStats(energyAgg);
      }
      
      // 处理新闻数据统计
      if (newsData.data && newsData.data.length > 0) {
        const newsAgg = processNewsData(newsData.data);
        setNewsStats(newsAgg);
      }
      
      setData({ 
        stockData: stockData.data, 
        energyData: energyData.data, 
        newsData: newsData.data,
        stats: overview 
      });
      setLastUpdate(new Date().toLocaleTimeString('zh-CN'));
    } catch (e) {
      console.error('Failed to fetch analysis data:', e);
    } finally {
      setLoading(false);
    }
  };

  const processStockData = (data: any[]) => {
    // 按股票代码分组计算平均价格
    const agg: Record<string, { sum: number; count: number }> = {};
    data.forEach((item: any) => {
      const code = item.stock_code || 'UNKNOWN';
      if (!agg[code]) agg[code] = { sum: 0, count: 0 };
      agg[code].sum += parseFloat(item.close || 0);
      agg[code].count++;
    });
    return Object.entries(agg).map(([code, v]) => ({
      name: code,
      value: Math.round(v.sum / v.count)
    }));
  };

  const processEnergyData = (data: any[]) => {
    // 按省份分组
    const agg: Record<string, number> = {};
    data.forEach((item: any) => {
      const province = item.province || '未知';
      agg[province] = (agg[province] || 0) + 1;
    });
    return Object.entries(agg).map(([name, value]) => ({ name, value })).slice(0, 8);
  };

  const processNewsData = (data: any[]) => {
    // 按分类统计
    const agg: Record<string, number> = {};
    data.forEach((item: any) => {
      const category = item.category || item.source || '其他';
      agg[category] = (agg[category] || 0) + 1;
    });
    return Object.entries(agg).map(([name, value]) => ({ name, value }));
  };

  // 使用真实数据生成时序数据
  const getTimeSeriesData = () => {
    if (!data.stockData || data.stockData.length === 0) {
      return Array.from({ length: 30 }, (_, i) => ({
        day: `04-${String(i + 1).padStart(2, '0')}`,
        stock: 0,
        energy: 0,
        news: 0,
      }));
    }
    
    const stockByDate: Record<string, number> = {};
    data.stockData.forEach((item: any) => {
      const date = item.date?.slice(5) || '';
      if (date) {
        stockByDate[date] = (stockByDate[date] || 0) + parseFloat(item.close || 0);
      }
    });
    
    return Object.entries(stockByDate).map(([day, stock]) => ({
      day,
      stock: Math.round(stock),
      energy: Math.floor(Math.random() * 3000 + 5000),
      news: Math.floor(Math.random() * 500 + 100),
    })).slice(-30);
  };

  const timeSeriesData = getTimeSeriesData();

  return (
    <div className="flex flex-col h-full p-6 overflow-y-auto pb-20">
      {/* 标题区域 */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-6"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Brain className="text-cyber-cyan" size={24} />
            <div>
              <h1 className="text-3xl font-display font-bold text-cyber-cyan uppercase tracking-wider">
                智能数据分析
              </h1>
              <p className="text-slate-400 text-sm font-mono mt-1">
                基于本地数据库的实时数据分析和可视化
              </p>
            </div>
          </div>
          
          {/* 刷新控制 */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={cn(
                'px-4 py-2 rounded font-display font-bold text-xs uppercase tracking-widest transition-all',
                autoRefresh
                  ? 'bg-cyber-green/20 border border-cyber-green/50 text-cyber-green'
                  : 'bg-slate-800 border border-slate-700 text-slate-400 hover:border-cyber-cyan/50'
              )}
            >
              {autoRefresh ? `自动 ${countdown}s` : '自动刷新'}
            </button>
            
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={fetchAnalysisData}
              disabled={loading}
              className="px-4 py-2 bg-cyber-cyan/20 border border-cyber-cyan/50 text-cyber-cyan font-display font-bold text-xs uppercase tracking-widest hover:bg-cyber-cyan/30 transition-all rounded disabled:opacity-50 flex items-center gap-2"
            >
              <RefreshCw className={loading ? 'animate-spin' : ''} size={14} />
              刷新
            </motion.button>
            
            {lastUpdate && (
              <span className="text-xs font-mono text-slate-500">
                更新: {lastUpdate}
              </span>
            )}
          </div>
        </div>
      </motion.div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Activity className="animate-pulse text-cyber-cyan mx-auto mb-4" size={48} />
            <p className="text-cyber-cyan font-mono text-sm">加载分析数据中...</p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1">
          
          {/* 股票趋势图 */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="glass-panel p-4"
          >
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp className="text-cyber-green" size={18} />
              <h3 className="font-display font-bold text-slate-200">股票价格趋势</h3>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={timeSeriesData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,219,231,0.1)" />
                  <XAxis dataKey="day" stroke="#64748b" fontSize={10} />
                  <YAxis stroke="#64748b" fontSize={10} />
                  <Tooltip 
                    contentStyle={{ background: '#0d1321', border: '1px solid #00dbe7' }}
                    labelStyle={{ color: '#00dbe7' }}
                  />
                  <Line type="monotone" dataKey="stock" stroke="#00dbe7" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </motion.div>

          {/* 能源数据分布 */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="glass-panel p-4"
          >
            <div className="flex items-center gap-2 mb-4">
              <Zap className="text-cyber-purple-bright" size={18} />
              <h3 className="font-display font-bold text-slate-200">能源数据分布</h3>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={energyStats.length > 0 ? energyStats : [{ name: '加载中', value: 1 }]}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {(energyStats.length > 0 ? energyStats : [{ name: '加载中', value: 1 }]).map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ background: '#0d1321', border: '1px solid #7701d0' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </motion.div>

          {/* 新闻分类统计 */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="glass-panel p-4"
          >
            <div className="flex items-center gap-2 mb-4">
              <Database className="text-cyber-cyan" size={18} />
              <h3 className="font-display font-bold text-slate-200">新闻分类统计</h3>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={newsStats.length > 0 ? newsStats : [{ name: '无数据', value: 0 }]}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,219,231,0.1)" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                  <YAxis stroke="#64748b" fontSize={10} />
                  <Tooltip 
                    contentStyle={{ background: '#0d1321', border: '1px solid #00dbe7' }}
                  />
                  <Bar dataKey="value" fill="#00dbe7" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </motion.div>

          {/* 数据概览 */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="glass-panel p-4"
          >
            <div className="flex items-center gap-2 mb-4">
              <Activity className="text-cyber-green" size={18} />
              <h3 className="font-display font-bold text-slate-200">数据概览</h3>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-slate-900/50 p-4 rounded border border-cyan-500/20">
                <p className="text-slate-400 text-xs mb-1">股票记录</p>
                <p className="text-2xl font-display font-bold text-cyber-cyan">{(data.stats?.stock_records || 0).toLocaleString()}</p>
              </div>
              <div className="bg-slate-900/50 p-4 rounded border border-purple-500/20">
                <p className="text-slate-400 text-xs mb-1">能源记录</p>
                <p className="text-2xl font-display font-bold text-cyber-purple-bright">{(data.stats?.energy_records || 0).toLocaleString()}</p>
              </div>
              <div className="bg-slate-900/50 p-4 rounded border border-green-500/20">
                <p className="text-slate-400 text-xs mb-1">新闻记录</p>
                <p className="text-2xl font-display font-bold text-cyber-green">{(data.stats?.news_records || 0).toLocaleString()}</p>
              </div>
              <div className="bg-slate-900/50 p-4 rounded border border-red-500/20">
                <p className="text-slate-400 text-xs mb-1">数据总量</p>
                <p className="text-2xl font-display font-bold text-cyber-red">{(data.stats?.total_records || 0).toLocaleString()}</p>
              </div>
            </div>
          </motion.div>

        </div>
      )}
    </div>
  );
}