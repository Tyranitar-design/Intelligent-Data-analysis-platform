import { motion } from 'framer-motion';
import {
  FileText, Filter, Table as TableIcon, Settings, TrendingUp, AlertTriangle, Clock,
  PlusCircle, CalendarDays, ChevronDown, Radar, BrainCircuit,
} from 'lucide-react';
import { cn } from '@/lib/utils';

export default function ReportsView() {
  const archives = [
    { id: 'INTEL-092X', title: 'Q3 Sector Alpha Intelligence', date: '2023.10.24 :: 14:30', active: true, color: 'cyan' },
    { id: 'GEO-441B', title: 'Sub-surface Anomaly Detection', date: '2023.10.22 :: 09:15', color: 'purple' },
    { id: 'FIN-002', title: 'Quarterly Resource Allocation', date: '2023.10.15 :: 18:00', color: 'slate' },
    { id: 'SEC-77Y', title: 'Firewall Integrity Incident', date: '2023.10.10 :: 03:44', color: 'red' },
  ];

  return (
    <div className="flex h-full p-6 gap-6 relative">
      <motion.aside
        initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}
        className="w-[380px] flex flex-col gap-4 overflow-hidden shrink-0"
      >
        <div className="flex items-center justify-between pb-3 border-b border-slate-700/50">
          <h2 className="text-xl font-display font-bold text-cyber-cyan tracking-tight uppercase">Committed Archives</h2>
          <Filter size={16} className="text-slate-500 cursor-pointer hover:text-cyber-cyan transition-colors" />
        </div>

        <div className="flex-1 overflow-y-auto flex flex-col gap-3 pr-2">
          {archives.map((item, i) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.07 }}
              whileHover={{ scale: 1.015, x: 2 }}
              className={cn(
                'glass-panel p-4 flex gap-4 cursor-pointer transition-colors relative overflow-hidden group',
                item.active ? 'border-cyber-cyan shadow-[0_0_15px_hsl(var(--cyber-cyan)/0.2)] bg-slate-900/60' : 'hover:border-cyber-cyan/40 bg-slate-900/40',
              )}
            >
              {item.active && <div className="absolute left-0 top-0 bottom-0 w-1 bg-cyber-cyan shadow-[0_0_10px_hsl(var(--cyber-cyan))]" />}

              <div className="w-20 h-24 rounded border border-slate-800 bg-black/40 overflow-hidden shrink-0 flex items-center justify-center relative">
                {item.id === 'FIN-002' ? (
                  <TrendingUp className="text-slate-600 group-hover:text-cyber-cyan transition-colors" size={32} />
                ) : (
                  <svg viewBox="0 0 80 96" className="w-full h-full opacity-70">
                    <defs>
                      <linearGradient id={`th-${item.id}`} x1="0" y1="0" x2="1" y2="1">
                        <stop offset="0%" stopColor={item.color === 'red' ? 'hsl(var(--cyber-red))' : item.color === 'purple' ? 'hsl(var(--cyber-purple-bright))' : 'hsl(var(--cyber-cyan))'} />
                        <stop offset="100%" stopColor="transparent" />
                      </linearGradient>
                    </defs>
                    <path d={`M 0 96 L 0 ${40 + (i * 8) % 30} Q 20 ${20 + i * 5} 40 ${30 + i * 4} T 80 ${20 + i * 6} L 80 96 Z`} fill={`url(#th-${item.id})`} opacity="0.5" />
                    <path d={`M 0 ${40 + (i * 8) % 30} Q 20 ${20 + i * 5} 40 ${30 + i * 4} T 80 ${20 + i * 6}`} fill="none" stroke={item.color === 'red' ? 'hsl(var(--cyber-red))' : item.color === 'purple' ? 'hsl(var(--cyber-purple-bright))' : 'hsl(var(--cyber-cyan))'} strokeWidth="1" />
                  </svg>
                )}
              </div>

              <div className="flex flex-col justify-between py-1 min-w-0">
                <div>
                  <span className={cn('font-display font-bold text-[10px] tracking-widest uppercase mb-1 block',
                    item.color === 'cyan' && 'text-cyber-cyan',
                    item.color === 'purple' && 'text-cyber-purple-bright',
                    item.color === 'red' && 'text-cyber-red',
                    item.color === 'slate' && 'text-slate-500',
                  )}>{item.id}</span>
                  <h4 className="text-xs font-bold text-slate-100 uppercase tracking-tight leading-snug">{item.title}</h4>
                </div>
                <div className="flex items-center gap-2 text-slate-500 font-display font-bold text-[10px]">
                  <Clock size={12} />
                  <span>{item.date}</span>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </motion.aside>

      <motion.section
        initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
        className="flex-1 glass-panel flex flex-col overflow-hidden relative"
      >
        <motion.div animate={{ top: ['10%', '90%', '10%'] }} transition={{ duration: 10, repeat: Infinity, ease: 'linear' }}
          className="absolute left-0 right-0 h-px bg-cyber-cyan/15 shadow-[0_0_15px_hsl(var(--cyber-cyan)/0.4)] z-0" />

        <header className="p-6 bg-slate-950/40 border-b border-slate-800 z-10">
          <div className="flex justify-between items-start mb-6 flex-wrap gap-4">
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-display font-bold text-slate-100 uppercase tracking-tight">Q3 Sector Alpha Intelligence</h1>
                <div className="flex items-center gap-2 bg-cyber-green/5 border border-cyber-green/30 px-3 py-1 rounded-sm text-cyber-green">
                  <div className="w-1.5 h-1.5 rounded-full bg-cyber-green shadow-[0_0_5px_hsl(var(--cyber-green))]" />
                  <span className="font-display font-bold text-[10px] tracking-widest uppercase">Verified</span>
                </div>
              </div>
              <div className="flex items-center gap-4 text-xs font-mono text-slate-500">
                <span>ID: INTEL-092X</span>
                <span className="opacity-30">|</span>
                <span>GENERATED: 2023.10.24 14:30:00 UTC</span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button className="flex items-center gap-2 px-4 py-2 border border-cyber-cyan/50 text-cyber-cyan font-display font-bold text-[10px] tracking-widest uppercase hover:bg-cyber-cyan/10 transition-all">
                <FileText size={14} /> EXPORT PDF
              </button>
              <button className="flex items-center gap-2 px-4 py-2 bg-cyber-cyan text-bg-deep font-display font-bold text-[10px] tracking-widest uppercase hover:bg-cyber-cyan-bright transition-all shadow-[0_0_15px_hsl(var(--cyber-cyan)/0.5)]">
                <TableIcon size={14} /> EXPORT DATA
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: 'Nodes Scanned', val: '14,291', change: '+12.4%', up: true, icon: Radar },
              { label: 'Anomalies Detected', val: '47', change: '-3 del', up: false, icon: AlertTriangle, danger: true },
              { label: 'Processing Time', val: '0.84s', icon: Clock },
            ].map((stat, i) => (
              <motion.div key={i}
                initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 + i * 0.07 }}
                whileHover={{ y: -3 }}
                className="bg-slate-900/60 p-4 border border-slate-800 rounded flex flex-col gap-1 relative overflow-hidden group hover:border-cyber-cyan/40 transition-colors"
              >
                <div className="absolute -top-8 -right-8 w-24 h-24 bg-cyber-cyan/10 blur-2xl opacity-0 group-hover:opacity-100 transition-opacity" />
                <div className="text-[10px] font-display font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2 relative">
                  <stat.icon size={12} className={cn('inline', stat.danger && 'text-cyber-red')} />
                  {stat.label}
                </div>
                <div className={cn('text-2xl font-display font-bold mt-1 font-mono relative',
                  stat.danger ? 'text-cyber-red' : 'text-cyber-cyan-bright')}>
                  {stat.val}
                </div>
                {stat.change && (
                  <div className={cn('mt-auto text-[10px] font-mono relative', stat.up ? 'text-cyber-green' : 'text-cyber-red')}>
                    {stat.up ? '↑' : '↓'} {stat.change}
                  </div>
                )}
              </motion.div>
            ))}
            <motion.div
              initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}
              whileHover={{ y: -3 }}
              className="border border-dashed border-slate-700 bg-slate-900/20 p-4 rounded flex flex-col items-center justify-center gap-2 cursor-pointer hover:border-cyber-cyan hover:bg-cyber-cyan/5 transition-all group"
            >
              <PlusCircle size={20} className="text-slate-600 group-hover:text-cyber-cyan transition-colors" />
              <span className="text-[10px] font-display font-bold text-slate-500 group-hover:text-cyber-cyan uppercase tracking-widest">Custom Metric</span>
            </motion.div>
          </div>
        </header>

        <div className="flex-1 p-6 overflow-y-auto z-10 flex flex-col gap-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <motion.div
              initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}
              className="lg:col-span-1 bg-cyber-green/5 border border-cyber-green/20 rounded-lg p-5 flex flex-col gap-6"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 bg-cyber-green/10 rounded">
                  <BrainCircuit size={20} className="text-cyber-green" />
                </div>
                <h3 className="text-lg font-display font-bold text-cyber-green uppercase tracking-tight">Synthesized Intel</h3>
              </div>
              <div className="flex flex-col gap-4 text-sm leading-relaxed text-slate-300 italic">
                <p className="border-l-2 border-cyber-green/40 pl-3">Sector Alpha shows a <span className="text-cyber-green font-bold">14% deviation</span> from baseline communication protocols, suggesting potential unauthorized mirroring.</p>
                <p className="border-l-2 border-cyber-green/40 pl-3">Resource allocation in Sub-node 4 remains <span className="text-cyber-red font-bold">critically inefficient</span>. Recommending immediate re-routing of data streams.</p>
              </div>
              <button className="mt-auto w-full py-2 bg-cyber-green/10 border border-cyber-green/40 text-cyber-green font-display font-bold text-[10px] tracking-widest uppercase hover:bg-cyber-green hover:text-bg-deep transition-all rounded-sm">
                Execute Auto-Remediation
              </button>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}
              className="lg:col-span-2 bg-slate-900/40 border border-slate-800 rounded-lg p-5 flex flex-col"
            >
              <div className="flex justify-between items-center mb-6 text-slate-100">
                <h3 className="text-lg font-display font-bold uppercase tracking-tight">Frequency Analysis</h3>
                <div className="flex gap-2">
                  {['1H', '24H', '7D'].map((t, i) => (
                    <span key={t} className={cn('px-3 py-1 font-mono text-[9px] rounded border transition-colors cursor-pointer',
                      i === 0 ? 'bg-cyber-cyan/10 border-cyber-cyan text-cyber-cyan' : 'bg-slate-800 border-slate-700 text-slate-500 hover:text-slate-200')}>
                      {t}
                    </span>
                  ))}
                </div>
              </div>
              <div className="flex-1 border-l border-b border-slate-800 relative min-h-[160px]">
                <svg className="w-full h-full" viewBox="0 0 100 60" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="freq-area" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="hsl(var(--cyber-cyan))" stopOpacity="0.4" />
                      <stop offset="100%" stopColor="hsl(var(--cyber-cyan))" stopOpacity="0" />
                    </linearGradient>
                  </defs>
                  <motion.path
                    initial={{ pathLength: 0, opacity: 0 }} animate={{ pathLength: 1, opacity: 1 }} transition={{ duration: 1.4, delay: 0.7 }}
                    d="M0 50 Q 20 40, 40 55 T 80 20 T 100 35"
                    fill="none" stroke="hsl(var(--cyber-cyan))" strokeWidth="0.6"
                  />
                  <motion.path
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.6, duration: 0.6 }}
                    d="M0 60 L0 50 Q 20 40, 40 55 T 80 20 T 100 35 L 100 60 Z"
                    fill="url(#freq-area)"
                  />
                </svg>
              </div>
            </motion.div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <motion.div
              initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.7 }}
              className="lg:col-span-2 bg-slate-900/40 border border-slate-800 rounded-lg p-5"
            >
              <h3 className="text-[13px] font-display font-bold text-slate-300 uppercase tracking-widest mb-4">Anomalous Nodes Log</h3>
              <div className="space-y-4">
                {[
                  { id: 'N-Alpha-004', status: 'CRITICAL', dev: '+42.1%', time: '14:28:11', color: 'red' },
                  { id: 'N-Beta-992', status: 'WARN', dev: '-18.4%', time: '14:15:02', color: 'purple' },
                  { id: 'N-Gamma-117', status: 'INFO', dev: '+2.3%', time: '14:09:55', color: 'cyan' },
                ].map((row, i) => (
                  <motion.div key={i}
                    initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.8 + i * 0.08 }}
                    whileHover={{ x: 4 }}
                    className="flex justify-between items-center text-[11px] font-mono border-b border-slate-800/50 pb-2"
                  >
                    <span className="w-1/4 text-cyber-cyan-bright">{row.id}</span>
                    <span className={cn('px-2 py-0.5 rounded border text-[9px] font-bold uppercase',
                      row.color === 'red' && 'bg-cyber-red/10 border-cyber-red/30 text-cyber-red',
                      row.color === 'purple' && 'bg-cyber-purple/10 border-cyber-purple/30 text-cyber-purple-bright',
                      row.color === 'cyan' && 'bg-cyber-cyan/10 border-cyber-cyan/30 text-cyber-cyan',
                    )}>
                      {row.status}
                    </span>
                    <span className="text-slate-300">{row.dev}</span>
                    <span className="text-slate-500">{row.time}</span>
                  </motion.div>
                ))}
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.8 }}
              className="glass-panel p-5 flex flex-col gap-6"
            >
              <h3 className="text-[13px] font-display font-bold text-slate-300 uppercase tracking-widest flex items-center gap-2">
                <CalendarDays size={16} className="text-cyber-cyan" />
                Distribution
              </h3>
              <div className="flex flex-col gap-4">
                <div className="border-b border-slate-800 pb-2 flex justify-between items-center cursor-pointer hover:text-cyber-cyan group">
                  <span className="text-[11px] font-mono text-slate-200 group-hover:text-cyber-cyan">Daily Sync</span>
                  <ChevronDown size={14} className="text-slate-500 group-hover:text-cyber-cyan" />
                </div>
                <div className="border-b border-slate-800 pb-2 flex justify-between items-center cursor-pointer">
                  <span className="text-[11px] font-mono text-slate-200">2023.10.31</span>
                  <Settings size={14} className="text-cyber-cyan" />
                </div>
              </div>
              <button className="mt-auto py-2.5 bg-slate-900 border border-cyber-cyan text-cyber-cyan font-display font-bold text-[10px] tracking-widest uppercase hover:bg-cyber-cyan/10 transition-all rounded-sm">
                Initialize
              </button>
            </motion.div>
          </div>
        </div>
      </motion.section>
    </div>
  );
}
