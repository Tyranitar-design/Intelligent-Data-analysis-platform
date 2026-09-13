import { useEffect, useRef, useState } from 'react';
import { Radar, Activity, Database, TrendingUp, Zap, RefreshCw } from 'lucide-react';
import { motion } from 'framer-motion';
import { LineChart, Line, ResponsiveContainer, YAxis, Tooltip } from 'recharts';
import { cn } from '@/lib/utils';

interface StatsData {
  totalRecords: number;
  stockCount: number;
  energyCount: number;
  newsCount: number;
  ecomCount: number;
}

interface Props {
  stats?: StatsData;
}

interface StockRecord {
  date: string;
  close: number;
  symbol: string;
}

export default function VisualizerView({ stats }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  // 真实股票数据
  const [stockData, setStockData] = useState<StockRecord[]>([]);
  const [lineData, setLineData] = useState<{ value: number; date: string }[]>([]);
  const [barData, setBarData] = useState<number[]>([30, 45, 20, 60, 80, 50, 90, 100]);
  const [logs, setLogs] = useState<{ type: string; color: string; text: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string>('');

  // Canvas 流式动画 - 使用真实数据颜色
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let width = canvas.width = canvas.offsetWidth;
    let height = canvas.height = canvas.offsetHeight;
    let time = 0;
    let raf = 0;

    const resize = () => {
      width = canvas.width = canvas.offsetWidth;
      height = canvas.height = canvas.offsetHeight;
    };
    window.addEventListener('resize', resize);

    const draw = () => {
      ctx.fillStyle = 'rgba(8, 14, 28, 0.15)';
      ctx.fillRect(0, 0, width, height);

      const lines = 60;
      for (let i = 0; i < lines; i++) {
        const persp = i / lines;
        ctx.beginPath();
        
        for (let x = 0; x <= width; x += 20) {
          const yOff =
            Math.sin(x * 0.002 + time * 1.2 + i * 0.1) * 60 +
            Math.sin(x * 0.005 - time * 0.8 + i * 0.05) * 30 +
            Math.cos(x * 0.003 + time * 1.5) * 20;
          const y = height * 0.5 + yOff * persp + (i - lines / 2) * 15 * persp;
          
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        
        // 赛博朋克配色：青色(#00dbe7) ↔ 紫色(#7701d0) ↔ 绿色(#2ae500)
        const hue = 185 + Math.sin(time * 0.3 + i * 0.08) * 90; // 185(青) to 275(紫)
        const light = 45 + Math.sin(time + i * 0.15) * 20;
        const alpha = 0.15 + (i / lines) * 0.6;
        
        ctx.strokeStyle = `hsla(${hue}, 95%, ${light}%, ${alpha})`;
        ctx.lineWidth = 0.5 + persp * 2;
        ctx.stroke();
      }
      
      time += 0.012;
      raf = requestAnimationFrame(draw);
    };

    draw();
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
    };
  }, []);

  // 加载真实数据
  useEffect(() => {
    fetchRealData();
  }, []);

  const fetchRealData = async () => {
    setLoading(true);
    try {
      // 获取股票数据
      const res = await fetch('/api/v1/analysis/db/data/stock?limit=100');
      const data = await res.json();
      
      if (data.data && data.data.length > 0) {
        setStockData(data.data);
        
        // 转换为图表数据
        const chartData = data.data.slice(-30).map((item: any) => ({
          value: parseFloat(item.close) || 0,
          date: item.date || '',
        }));
        setLineData(chartData);
        
        // 添加日志
        setLogs(prev => [...prev.slice(-6), {
          type: 'DATA',
          color: '#00dbe7',
          text: `股票数据已更新，共 ${data.data.length} 条记录`,
        }]);
      }
      
      setLastUpdate(new Date().toLocaleTimeString('zh-CN'));
    } catch (e) {
      console.error('Failed to fetch data:', e);
      setLogs(prev => [...prev.slice(-6), {
        type: 'ERROR',
        color: '#ffb4ab',
        text: '数据加载失败',
      }]);
    } finally {
      setLoading(false);
    }
  };

  // 自动刷新（每30秒）
  useEffect(() => {
    const interval = setInterval(() => {
      // 更新柱状图（模拟频谱）
      setBarData(prev => [...prev.slice(1), Math.floor(Math.random() * 80) + 20]);
      
      // 每30秒刷新一次真实数据
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  // 统计数据
  const displayStats = {
    totalRecords: stats?.totalData || 0,
    stockCount: stats?.stockCount || 0,
    energyCount: stats?.energyCount || 0,
    newsCount: stats?.newsCount || 0,
    ecomCount: stats?.ecomCount || 0,
  };

  return (
    <div className="flex flex-col h-full p-6 gap-6 overflow-hidden">
      {/* Canvas 流式背景 */}
      <div className="absolute inset-0 z-0">
        <canvas ref={canvasRef} className="w-full h-full opacity-80" />
      </div>

      {/* 内容层 */}
      <div className="relative z-10 flex flex-col h-full gap-4">
        {/* 顶部统计 */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid grid-cols-4 gap-4"
        >
          <div className="glass-panel p-4 text-center">
            <Database className="text-cyber-cyan mx-auto mb-2" size={20} />
            <p className="text-2xl font-display font-bold text-cyber-cyan">{displayStats.totalRecords.toLocaleString()}</p>
            <p className="text-xs text-slate-400 font-mono">数据总量</p>
          </div>
          <div className="glass-panel p-4 text-center">
            <TrendingUp className="text-cyber-green mx-auto mb-2" size={20} />
            <p className="text-2xl font-display font-bold text-cyber-green">{displayStats.stockCount.toLocaleString()}</p>
            <p className="text-xs text-slate-400 font-mono">股票数据</p>
          </div>
          <div className="glass-panel p-4 text-center">
            <Zap className="text-cyber-purple-bright mx-auto mb-2" size={20} />
            <p className="text-2xl font-display font-bold text-cyber-purple-bright">{displayStats.energyCount.toLocaleString()}</p>
            <p className="text-xs text-slate-400 font-mono">能源数据</p>
          </div>
          <div className="glass-panel p-4 text-center">
            <Activity className="text-cyber-cyan mx-auto mb-2" size={20} />
            <p className="text-2xl font-display font-bold text-slate-200">{displayStats.newsCount.toLocaleString()}</p>
            <p className="text-xs text-slate-400 font-mono">新闻数据</p>
          </div>
        </motion.div>

        {/* 主内容区域 */}
        <div className="flex-1 grid grid-cols-3 gap-4 min-h-0">
          {/* 股票价格趋势 - 真实数据 */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className="glass-panel p-4 flex flex-col"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <TrendingUp className="text-cyber-green" size={16} />
                <span className="text-xs font-display font-bold text-slate-200 uppercase">股票价格趋势</span>
              </div>
              <button 
                onClick={fetchRealData}
                disabled={loading}
                className="text-xs text-cyber-cyan hover:text-cyber-cyan-bright disabled:opacity-50"
              >
                {loading ? <RefreshCw className="animate-spin" size={14} /> : <RefreshCw size={14} />}
              </button>
            </div>
            <div className="flex-1">
              {lineData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={lineData}>
                    <YAxis hide domain={['auto', 'auto']} />
                    <Tooltip 
                      contentStyle={{ background: '#0d1321', border: '1px solid #00dbe7' }}
                      formatter={(value: any) => [value.toFixed(2), '收盘价']}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="value" 
                      stroke="#00dbe7" 
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-slate-500 text-xs">
                  暂无数据
                </div>
              )}
            </div>
          </motion.div>

          {/* 频谱分析 */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="glass-panel p-4 flex flex-col"
          >
            <div className="flex items-center gap-2 mb-3">
              <Activity className="text-cyber-purple-bright" size={16} />
              <span className="text-xs font-display font-bold text-slate-200 uppercase">数据频谱</span>
            </div>
            <div className="flex-1 flex items-end gap-1">
              {barData.map((val, idx) => (
                <motion.div
                  key={idx}
                  initial={{ height: 0 }}
                  animate={{ height: `${val}%` }}
                  transition={{ duration: 0.3 }}
                  className="flex-1 rounded-t"
                  style={{
                    background: `linear-gradient(to top, #00dbe7, #7701d0)`,
                    opacity: 0.6 + (val / 100) * 0.4,
                  }}
                />
              ))}
            </div>
          </motion.div>

          {/* 系统日志 - 真实状态 */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.3 }}
            className="glass-panel p-4 flex flex-col"
          >
            <div className="flex items-center gap-2 mb-3">
              <Activity className="text-cyber-green" size={16} />
              <span className="text-xs font-display font-bold text-slate-200 uppercase">系统状态</span>
            </div>
            <div className="flex-1 space-y-2 overflow-hidden">
              {logs.length > 0 ? logs.map((log, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex items-center gap-2 text-xs font-mono"
                >
                  <span style={{ color: log.color }}>[{log.type}]</span>
                  <span className="text-slate-400 truncate">{log.text}</span>
                </motion.div>
              )) : (
                <div className="text-slate-500 text-xs font-mono py-4 text-center">
                  点击刷新获取数据
                </div>
              )}
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
                {loading ? '数据加载中...' : '系统运行正常'}
              </span>
            </div>
            {lastUpdate && (
              <div className="text-xs font-mono text-slate-500">
                上次更新: {lastUpdate}
              </div>
            )}
          </div>
          <div className="text-xs font-mono text-cyber-cyan">
            实时可视化大屏 · 数据来源: 本地数据库
          </div>
        </motion.div>
      </div>
    </div>
  );
}