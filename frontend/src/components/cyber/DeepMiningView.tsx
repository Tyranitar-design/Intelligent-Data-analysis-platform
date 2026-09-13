import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Database, BrainCircuit, Activity, AlertTriangle, CheckCircle, Loader2,
  RefreshCw,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface MiningResult {
  type: string;
  status: string;
  result?: any;
}

export default function DeepMiningView() {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<MiningResult[]>([]);
  const [stockData, setStockData] = useState<any[]>([]);
  const [selectedSource, setSelectedSource] = useState('stock');
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [countdown, setCountdown] = useState(30);
  const [lastUpdate, setLastUpdate] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  // 自动刷新
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (autoRefresh) {
      interval = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) {
            fetchData();
            return 30;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const fetchData = async () => {
    try {
      const res = await fetch('/api/v1/analysis/db/data/stock?limit=500');
      const data = await res.json();
      if (data.data) {
        setStockData(data.data);
        setLastUpdate(new Date().toLocaleTimeString('zh-CN'));
      }
    } catch (e) {
      console.error('Failed to fetch data:', e);
    }
  };

  // 关联规则挖掘（使用 Apriori 算法）
  const runApriori = async () => {
    setLoading(true);
    setResults(prev => [...prev, { type: '关联规则 (Apriori)', status: 'running' }]);
    
    try {
      const res = await fetch('/api/v1/mining/apriori', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source: 'ecommerce',
          platform: 'jd',
          item_col: 'brand',
          group_col: 'keyword',
          min_support: 0.05,
          min_confidence: 0.3,
          limit: 500,
        }),
      });
      const data = await res.json();
      
      if (data.detail) {
        setResults(prev => prev.map(r => r.type === '关联规则 (Apriori)' ? { ...r, status: 'error', result: { error: data.detail } } : r));
      } else {
        setResults(prev => prev.map(r => r.type === '关联规则 (Apriori)' ? { ...r, status: 'completed', result: data } : r));
      }
    } catch (e) {
      setResults(prev => prev.map(r => r.type === '关联规则 (Apriori)' ? { ...r, status: 'error', result: { error: String(e) } } : r));
    } finally {
      setLoading(false);
    }
  };

  // 异常检测（使用 Isolation Forest）
  const runAnomalyDetection = async () => {
    setLoading(true);
    setResults(prev => [...prev, { type: '异常检测 (Isolation Forest)', status: 'running' }]);
    
    try {
      const res = await fetch('/api/v1/mining/isolation-forest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source: 'stock',
          contamination: 0.1,
          n_estimators: 50,
          limit: 500,
        }),
      });
      const data = await res.json();
      
      if (data.detail) {
        setResults(prev => prev.map(r => r.type === '异常检测 (Isolation Forest)' ? { ...r, status: 'error', result: { error: data.detail } } : r));
      } else {
        setResults(prev => prev.map(r => r.type === '异常检测 (Isolation Forest)' ? { ...r, status: 'completed', result: data } : r));
      }
    } catch (e) {
      setResults(prev => prev.map(r => r.type === '异常检测 (Isolation Forest)' ? { ...r, status: 'error', result: { error: String(e) } } : r));
    } finally {
      setLoading(false);
    }
  };

  // 时序模式挖掘
  const runTimeSeriesPatterns = async () => {
    setLoading(true);
    setResults(prev => [...prev, { type: '时序模式分析', status: 'running' }]);
    
    try {
      const res = await fetch('/api/v1/mining/time-series-patterns', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source: 'stock',
          date_col: 'date',
          value_col: 'close',
          window: 5,
          limit: 500,
        }),
      });
      const data = await res.json();
      
      if (data.detail) {
        setResults(prev => prev.map(r => r.type === '时序模式分析' ? { ...r, status: 'error', result: { error: data.detail } } : r));
      } else {
        setResults(prev => prev.map(r => r.type === '时序模式分析' ? { ...r, status: 'completed', result: data } : r));
      }
    } catch (e) {
      setResults(prev => prev.map(r => r.type === '时序模式分析' ? { ...r, status: 'error', result: { error: String(e) } } : r));
    } finally {
      setLoading(false);
    }
  };

  const clearResults = () => {
    setResults([]);
  };

  return (
    <div className="flex h-full p-6 gap-6 relative overflow-hidden">
      {/* 背景网格 */}
      <div className="absolute inset-0 grid-bg opacity-30" />
      
      {/* 左侧控制面板 */}
      <motion.section
        initial={{ opacity: 0, x: -10 }} 
        animate={{ opacity: 1, x: 0 }}
        className="w-72 glass-panel rounded-xl p-4 flex flex-col gap-4 z-10"
      >
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <BrainCircuit className="text-cyber-purple-bright" size={20} />
            <h2 className="font-display font-bold text-cyber-cyan uppercase tracking-widest text-xs">
              深度挖掘工具
            </h2>
          </div>
          
          {/* 刷新控制 */}
          <div className="flex flex-col gap-2">
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={cn(
                'px-2 py-1 rounded text-[10px] font-bold transition-all',
                autoRefresh
                  ? 'bg-cyber-green/20 border border-cyber-green/50 text-cyber-green'
                  : 'bg-slate-800 border border-slate-700 text-slate-400'
              )}
            >
              {autoRefresh ? `${countdown}s` : '自动'}
            </button>
            <button 
              onClick={fetchData}
              className="px-2 py-1 bg-cyber-cyan/20 border border-cyber-cyan/50 text-cyber-cyan rounded text-[10px] font-bold flex items-center justify-center gap-1"
            >
              <RefreshCw size={10} />
              刷新
            </button>
          </div>
        </div>
        
        {lastUpdate && (
          <div className="text-[10px] font-mono text-slate-500 text-center">
            更新: {lastUpdate}
          </div>
        )}

        {/* 数据源选择 */}
        <div className="space-y-2">
          <label className="text-slate-400 text-xs font-mono">数据源</label>
          <select 
            value={selectedSource}
            onChange={(e) => setSelectedSource(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-slate-200 text-sm focus:border-cyber-cyan focus:outline-none"
          >
            <option value="stock">股票数据</option>
            <option value="energy">能源数据</option>
            <option value="news">新闻数据</option>
          </select>
        </div>

        {/* 数据统计 */}
        <div className="bg-slate-900/50 rounded p-3 border border-slate-800">
          <div className="flex items-center gap-2 mb-2">
            <Database className="text-cyber-cyan" size={14} />
            <span className="text-xs text-slate-400">数据量</span>
          </div>
          <p className="text-xl font-display font-bold text-cyber-cyan">
            {stockData.length.toLocaleString()} 条
          </p>
        </div>

        {/* 操作按钮 */}
        <div className="space-y-2 flex-1">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={runApriori}
            disabled={loading}
            className="w-full py-2.5 bg-cyber-cyan/10 border border-cyber-cyan/50 text-cyber-cyan font-display font-bold text-xs tracking-widest uppercase hover:bg-cyber-cyan/20 transition-all rounded disabled:opacity-50"
          >
            关联规则挖掘
          </motion.button>
          
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={runAnomalyDetection}
            disabled={loading}
            className="w-full py-2.5 bg-cyber-purple/10 border border-cyber-purple/50 text-cyber-purple-bright font-display font-bold text-xs tracking-widest uppercase hover:bg-cyber-purple/20 transition-all rounded disabled:opacity-50"
          >
            异常检测
          </motion.button>
          
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={runTimeSeriesPatterns}
            disabled={loading}
            className="w-full py-2.5 bg-cyber-green/10 border border-cyber-green/50 text-cyber-green font-display font-bold text-xs tracking-widest uppercase hover:bg-cyber-green/20 transition-all rounded disabled:opacity-50"
          >
            时序模式分析
          </motion.button>
        </div>

        <button
          onClick={clearResults}
          className="w-full py-2 border border-slate-700 text-slate-400 font-display font-bold text-xs tracking-widest uppercase hover:border-slate-500 hover:text-slate-300 transition-all rounded"
        >
          清空结果
        </button>
      </motion.section>

      {/* 右侧结果面板 */}
      <motion.section
        initial={{ opacity: 0, x: 10 }}
        animate={{ opacity: 1, x: 0 }}
        className="flex-1 glass-panel rounded-xl overflow-hidden flex flex-col z-10"
      >
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <h2 className="font-display font-bold text-slate-200 uppercase tracking-widest text-xs">
            挖掘结果
          </h2>
          {loading && (
            <div className="flex items-center gap-2 text-cyber-cyan">
              <Loader2 className="animate-spin" size={14} />
              <span className="text-xs font-mono">处理中...</span>
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {results.length === 0 ? (
            <div className="flex-1 flex items-center justify-center h-full">
              <div className="text-center text-slate-500">
                <Activity size={48} className="mx-auto mb-4 opacity-30" />
                <p className="font-mono text-sm">点击左侧按钮开始数据挖掘</p>
              </div>
            </div>
          ) : (
            results.map((result, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="bg-slate-900/50 border border-slate-800 rounded-lg p-4"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    {result.status === 'completed' && <CheckCircle className="text-cyber-green" size={16} />}
                    {result.status === 'running' && <Loader2 className="text-cyber-cyan animate-spin" size={16} />}
                    {result.status === 'error' && <AlertTriangle className="text-cyber-red" size={16} />}
                    <span className="font-display font-bold text-slate-200 text-sm">{result.type}</span>
                  </div>
                  <span className={cn(
                    'text-xs font-mono px-2 py-1 rounded',
                    result.status === 'completed' && 'bg-cyber-green/20 text-cyber-green',
                    result.status === 'running' && 'bg-cyber-cyan/20 text-cyber-cyan',
                    result.status === 'error' && 'bg-cyber-red/20 text-cyber-red',
                  )}>
                    {result.status === 'completed' ? '完成' : result.status === 'running' ? '运行中' : '错误'}
                  </span>
                </div>
                
                {result.result && !result.result.error && (
                  <div className="space-y-3">
                    {/* 关键指标展示 */}
                    {result.type.includes('异常检测') && result.result.metrics && (
                      <div className="grid grid-cols-2 gap-3">
                        <div className="bg-slate-950/50 rounded p-3 text-center">
                          <p className="text-xs text-slate-400 mb-1">总样本数</p>
                          <p className="text-xl font-display font-bold text-cyber-cyan">{result.result.metrics.total_samples}</p>
                        </div>
                        <div className="bg-syber-red/10 rounded p-3 text-center border border-cyber-red/30">
                          <p className="text-xs text-slate-400 mb-1">异常数量</p>
                          <p className="text-xl font-display font-bold text-cyber-red">{result.result.metrics.anomaly_count}</p>
                        </div>
                        <div className="bg-slate-950/50 rounded p-3 text-center">
                          <p className="text-xs text-slate-400 mb-1">异常比例</p>
                          <p className="text-xl font-display font-bold text-cyber-purple-bright">{result.result.metrics.anomaly_pct}%</p>
                        </div>
                        <div className="bg-slate-950/50 rounded p-3 text-center">
                          <p className="text-xs text-slate-400 mb-1">特征数量</p>
                          <p className="text-xl font-display font-bold text-cyber-green">{result.result.features_used?.length || 0}</p>
                        </div>
                      </div>
                    )}
                    
                    {/* 关联规则展示 */}
                    {result.type.includes('关联规则') && result.result.rules && (
                      <div className="space-y-2">
                        <p className="text-xs text-slate-400">发现规则: {result.result.rules.length} 条</p>
                        {result.result.rules.slice(0, 5).map((rule: any, i: number) => (
                          <div key={i} className="bg-slate-950/50 rounded p-2 text-xs">
                            <span className="text-cyber-cyan">{rule.antecedent?.join(', ')}</span>
                            <span className="text-slate-400"> → </span>
                            <span className="text-cyber-purple-bright">{rule.consequent?.join(', ')}</span>
                            <span className="text-slate-500 ml-2">(置信度: {(rule.confidence * 100).toFixed(1)}%)</span>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {/* 时序模式展示 */}
                    {result.type.includes('时序') && result.result.metrics && (
                      <div className="space-y-3">
                        <div className="grid grid-cols-2 gap-3">
                          <div className="bg-slate-950/50 rounded p-3 text-center">
                            <p className="text-xs text-slate-400 mb-1">趋势方向</p>
                            <p className="text-lg font-display font-bold text-cyber-green">{result.result.pattern_summary?.trend_direction || '稳定'}</p>
                          </div>
                          <div className="bg-slate-950/50 rounded p-3 text-center">
                            <p className="text-xs text-slate-400 mb-1">趋势强度</p>
                            <p className="text-lg font-display font-bold text-cyber-cyan">{result.result.pattern_summary?.trend_strength || '弱'}</p>
                          </div>
                          <div className="bg-slate-950/50 rounded p-3 text-center">
                            <p className="text-xs text-slate-400 mb-1">波动性</p>
                            <p className="text-lg font-display font-bold text-cyber-purple-bright">{result.result.pattern_summary?.volatility_level || '低'}</p>
                          </div>
                          <div className="bg-slate-950/50 rounded p-3 text-center">
                            <p className="text-xs text-slate-400 mb-1">数据点数</p>
                            <p className="text-lg font-display font-bold text-slate-200">{result.result.metrics?.data_points || 0}</p>
                          </div>
                        </div>
                        <div className="bg-slate-950/50 rounded p-3 text-xs text-slate-400">
                          <span>最大涨幅: </span>
                          <span className="text-cyber-green">{result.result.pattern_summary?.max_single_day_gain}</span>
                          <span className="ml-4">最大跌幅: </span>
                          <span className="text-cyber-red">{result.result.pattern_summary?.max_single_day_loss}</span>
                        </div>
                      </div>
                    )}
                    
                    {/* 详情按钮 */}
                    <details className="text-xs">
                      <summary className="text-cyber-cyan cursor-pointer hover:text-cyber-cyan-bright">查看原始数据</summary>
                      <pre className="bg-slate-950/50 rounded p-2 mt-2 text-slate-400 overflow-x-auto">{JSON.stringify(result.result, null, 2)}</pre>
                    </details>
                  </div>
                )}
                
                {result.result?.error && (
                  <div className="bg-cyber-red/10 border border-cyber-red/30 rounded p-3 text-xs text-cyber-red">
                    错误: {result.result.error}
                  </div>
                )}
              </motion.div>
            ))
          )}
        </div>
      </motion.section>
    </div>
  );
}