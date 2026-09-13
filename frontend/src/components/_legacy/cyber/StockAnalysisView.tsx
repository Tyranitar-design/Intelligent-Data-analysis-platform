import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  ComposedChart, CandlestickChart
} from 'recharts';
import { 
  TrendingUp, TrendingDown, Activity, RefreshCw, 
  BarChart3, PieChart as PieChartIcon, LineChart as LineChartIcon,
  Zap, Database
} from 'lucide-react';
import { cn } from '@/lib/utils';

// 颜色配置
const COLORS = {
  up: '#2ae500',
  down: '#ffb4ab',
  cyan: '#00dbe7',
  purple: '#7701d0',
  yellow: '#fbbf24',
  green: '#22c55e',
};

interface StockData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  symbol: string;
  name?: string;
}

export default function StockAnalysisView() {
  const [loading, setLoading] = useState(true);
  const [stockData, setStockData] = useState<StockData[]>([]);
  const [selectedStock, setSelectedStock] = useState('600519');
  const [chartType, setChartType] = useState<'line' | 'area' | 'bar'>('area');
  const [lastUpdate, setLastUpdate] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [countdown, setCountdown] = useState(30);

  // 股票列表
  const stockList = [
    { code: '600519', name: '贵州茅台' },
    { code: '601318', name: '中国平安' },
    { code: '000001', name: '平安银行' },
    { code: '600036', name: '招商银行' },
  ];

  useEffect(() => {
    fetchStockData();
  }, [selectedStock]);

  // 自动刷新
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (autoRefresh) {
      interval = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) {
            fetchStockData();
            return 30;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [autoRefresh, selectedStock]);

  const fetchStockData = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/analysis/db/data/stock?limit=100`);
      const data = await res.json();
      
      if (data.data && data.data.length > 0) {
        // 按选中股票筛选并按日期排序
        const filtered = data.data
          .filter((item: any) => item.symbol === selectedStock)
          .sort((a: any, b: any) => new Date(a.date).getTime() - new Date(b.date).getTime())
          .slice(-30); // 最近30天
        
        setStockData(filtered.map((item: any) => ({
          date: item.date,
          open: parseFloat(item.open) || 0,
          high: parseFloat(item.high) || 0,
          low: parseFloat(item.low) || 0,
          close: parseFloat(item.close) || 0,
          volume: parseFloat(item.volume) || 0,
          symbol: item.symbol,
        })));
      }
      setLastUpdate(new Date().toLocaleTimeString('zh-CN'));
    } catch (e) {
      console.error('Failed to fetch stock data:', e);
    } finally {
      setLoading(false);
    }
  };

  // 计算统计数据
  const stats = {
    latestPrice: stockData.length > 0 ? stockData[stockData.length - 1]?.close : 0,
    priceChange: stockData.length > 1 
      ? stockData[stockData.length - 1]?.close - stockData[stockData.length - 2]?.close 
      : 0,
    highPrice: Math.max(...stockData.map(d => d.high)),
    lowPrice: Math.min(...stockData.map(d => d.low)),
    avgVolume: stockData.length > 0 
      ? Math.round(stockData.reduce((sum, d) => sum + d.volume, 0) / stockData.length)
      : 0,
  };

  const priceChangePercent = stats.latestPrice > 0 
    ? ((stats.priceChange / stats.latestPrice) * 100).toFixed(2) 
    : '0.00';

  // 计算涨跌分布（用于饼图）
  const upDays = stockData.filter((d, i) => i > 0 && d.close > stockData[i-1].close).length;
  const downDays = stockData.filter((d, i) => i > 0 && d.close < stockData[i-1].close).length;
  const flatDays = stockData.length - 1 - upDays - downDays;

  const pieData = [
    { name: '上涨', value: upDays, color: COLORS.up },
    { name: '下跌', value: downDays, color: COLORS.down },
    { name: '持平', value: Math.max(0, flatDays), color: '#64748b' },
  ];

  // 成交量数据
  const volumeData = stockData.slice(-10).map(d => ({
    date: d.date.slice(5), // 只显示月-日
    volume: d.volume / 10000, // 转换为万手
    fill: d.close >= d.open ? COLORS.up : COLORS.down,
  }));

  // 自定义 Tooltip
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-slate-900 border border-cyber-cyan/50 rounded p-3 text-xs font-mono">
          <p className="text-slate-400 mb-2">{label}</p>
          {payload.map((entry: any, index: number) => (
            <p key={index} style={{ color: entry.color }}>
              {entry.name}: {typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="flex flex-col h-full p-6 gap-6 overflow-y-auto pb-20">
      {/* 标题栏 */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <TrendingUp className="text-cyber-cyan" size={24} />
          <h1 className="text-3xl font-display font-bold text-cyber-cyan uppercase tracking-wider">
            股票数据分析
          </h1>
        </div>
        
        <div className="flex items-center gap-4">
          {/* 股票选择 */}
          <select
            value={selectedStock}
            onChange={(e) => setSelectedStock(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-200 text-sm focus:border-cyber-cyan focus:outline-none"
          >
            {stockList.map(stock => (
              <option key={stock.code} value={stock.code}>
                {stock.code} - {stock.name}
              </option>
            ))}
          </select>

          {/* 自动刷新 */}
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

          {/* 手动刷新 */}
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={fetchStockData}
            disabled={loading}
            className="px-4 py-2 bg-cyber-cyan/20 border border-cyber-cyan/50 text-cyber-cyan font-display font-bold text-xs uppercase tracking-widest hover:bg-cyber-cyan/30 transition-all rounded disabled:opacity-50 flex items-center gap-2"
          >
            <RefreshCw className={loading ? 'animate-spin' : ''} size={14} />
            刷新
          </motion.button>
        </div>
      </motion.div>

      {/* 关键指标 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid grid-cols-5 gap-4"
      >
        <div className="glass-panel p-4 text-center">
          <p className="text-xs text-slate-400 mb-1 font-mono">最新价</p>
          <p className="text-2xl font-display font-bold text-cyber-cyan">{stats.latestPrice.toFixed(2)}</p>
        </div>
        <div className={cn('glass-panel p-4 text-center', stats.priceChange >= 0 ? 'border-cyber-green/30' : 'border-cyber-red/30')}>
          <p className="text-xs text-slate-400 mb-1 font-mono">涨跌幅</p>
          <div className="flex items-center justify-center gap-1">
            {stats.priceChange >= 0 ? (
              <TrendingUp className="text-cyber-green" size={18} />
            ) : (
              <TrendingDown className="text-cyber-red" size={18} />
            )}
            <p className={cn('text-xl font-display font-bold', stats.priceChange >= 0 ? 'text-cyber-green' : 'text-cyber-red')}>
              {stats.priceChange >= 0 ? '+' : ''}{priceChangePercent}%
            </p>
          </div>
        </div>
        <div className="glass-panel p-4 text-center">
          <p className="text-xs text-slate-400 mb-1 font-mono">最高价</p>
          <p className="text-xl font-display font-bold text-cyber-purple-bright">{stats.highPrice.toFixed(2)}</p>
        </div>
        <div className="glass-panel p-4 text-center">
          <p className="text-xs text-slate-400 mb-1 font-mono">最低价</p>
          <p className="text-xl font-display font-bold text-cyber-red">{stats.lowPrice.toFixed(2)}</p>
        </div>
        <div className="glass-panel p-4 text-center">
          <p className="text-xs text-slate-400 mb-1 font-mono">平均成交量</p>
          <p className="text-xl font-display font-bold text-slate-200">{(stats.avgVolume / 10000).toFixed(0)}万手</p>
        </div>
      </motion.div>

      {/* 图表切换按钮 */}
      <div className="flex gap-2">
        {[
          { type: 'area', icon: LineChartIcon, label: '趋势图' },
          { type: 'bar', icon: BarChart3, label: '成交量' },
          { type: 'line', icon: Activity, label: '折线图' },
        ].map(btn => (
          <button
            key={btn.type}
            onClick={() => setChartType(btn.type as any)}
            className={cn(
              'px-4 py-2 rounded font-display font-bold text-xs uppercase tracking-widest transition-all flex items-center gap-2',
              chartType === btn.type
                ? 'bg-cyber-cyan/20 border border-cyber-cyan/50 text-cyber-cyan'
                : 'bg-slate-800 border border-slate-700 text-slate-400 hover:border-cyber-cyan/50'
            )}
          >
            <btn.icon size={14} />
            {btn.label}
          </button>
        ))}
      </div>

      {/* 主图表区域 */}
      <div className="grid grid-cols-3 gap-6 flex-1">
        {/* 主价格图表 */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
          className="col-span-2 glass-panel p-4"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-display font-bold text-slate-200 flex items-center gap-2">
              <TrendingUp className="text-cyber-cyan" size={16} />
              价格走势
            </h3>
            <span className="text-xs text-slate-500 font-mono">
              {stockList.find(s => s.code === selectedStock)?.name} · 近30天
            </span>
          </div>
          
          <div className="h-72">
            {stockData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                {chartType === 'area' ? (
                  <AreaChart data={stockData}>
                    <defs>
                      <linearGradient id="colorClose" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#00dbe7" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#00dbe7" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,219,231,0.1)" />
                    <XAxis dataKey="date" stroke="#64748b" fontSize={10} tickFormatter={(v) => v.slice(5)} />
                    <YAxis stroke="#64748b" fontSize={10} domain={['auto', 'auto']} />
                    <Tooltip content={<CustomTooltip />} />
                    <Area 
                      type="monotone" 
                      dataKey="close" 
                      stroke="#00dbe7" 
                      strokeWidth={2}
                      fill="url(#colorClose)" 
                      name="收盘价"
                    />
                  </AreaChart>
                ) : chartType === 'line' ? (
                  <LineChart data={stockData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,219,231,0.1)" />
                    <XAxis dataKey="date" stroke="#64748b" fontSize={10} tickFormatter={(v) => v.slice(5)} />
                    <YAxis stroke="#64748b" fontSize={10} domain={['auto', 'auto']} />
                    <Tooltip content={<CustomTooltip />} />
                    <Line 
                      type="monotone" 
                      dataKey="close" 
                      stroke="#00dbe7" 
                      strokeWidth={2}
                      dot={false}
                      name="收盘价"
                    />
                    <Line 
                      type="monotone" 
                      dataKey="high" 
                      stroke="#7701d0" 
                      strokeWidth={1}
                      strokeDasharray="5 5"
                      dot={false}
                      name="最高价"
                    />
                    <Line 
                      type="monotone" 
                      dataKey="low" 
                      stroke="#ffb4ab" 
                      strokeWidth={1}
                      strokeDasharray="5 5"
                      dot={false}
                      name="最低价"
                    />
                  </LineChart>
                ) : (
                  <BarChart data={volumeData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,219,231,0.1)" />
                    <XAxis dataKey="date" stroke="#64748b" fontSize={10} />
                    <YAxis stroke="#64748b" fontSize={10} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="volume" name="成交量(万手)" radius={[4, 4, 0, 0]}>
                      {volumeData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Bar>
                  </BarChart>
                )}
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-slate-500">
                {loading ? '加载中...' : '暂无数据'}
              </div>
            )}
          </div>
        </motion.div>

        {/* 涨跌分布饼图 */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
          className="glass-panel p-4"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-display font-bold text-slate-200 flex items-center gap-2">
              <PieChartIcon className="text-cyber-purple-bright" size={16} />
              涨跌分布
            </h3>
          </div>
          
          <div className="h-52">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={70}
                  paddingAngle={2}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ background: '#0d1321', border: '1px solid #00dbe7' }}
                />
                <Legend 
                  formatter={(value) => <span className="text-slate-300 text-xs">{value}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* 统计数据 */}
          <div className="mt-4 grid grid-cols-3 gap-2 text-center">
            <div className="bg-slate-900/50 rounded p-2">
              <p className="text-lg font-display font-bold text-cyber-green">{upDays}</p>
              <p className="text-xs text-slate-500">上涨天数</p>
            </div>
            <div className="bg-slate-900/50 rounded p-2">
              <p className="text-lg font-display font-bold text-cyber-red">{downDays}</p>
              <p className="text-xs text-slate-500">下跌天数</p>
            </div>
            <div className="bg-slate-900/50 rounded p-2">
              <p className="text-lg font-display font-bold text-slate-400">{flatDays}</p>
              <p className="text-xs text-slate-500">持平天数</p>
            </div>
          </div>
        </motion.div>
      </div>

      {/* 底部状态栏 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="glass-panel p-3 flex items-center justify-between"
      >
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className={cn(
              'w-2 h-2 rounded-full',
              loading ? 'bg-cyber-cyan animate-pulse' : 'bg-cyber-green'
            )} />
            <span className="text-xs font-mono text-slate-400">
              {loading ? '数据加载中...' : '数据已加载'}
            </span>
          </div>
          {lastUpdate && (
            <span className="text-xs font-mono text-slate-500">
              更新时间: {lastUpdate}
            </span>
          )}
        </div>
        <div className="text-xs font-mono text-cyber-cyan flex items-center gap-2">
          <Database size={12} />
          数据来源: 本地数据库 · 东方财富
        </div>
      </motion.div>
    </div>
  );
}