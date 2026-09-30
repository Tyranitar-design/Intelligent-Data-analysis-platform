import React from 'react';
import { 
  Database, 
  Code, 
  BrainCircuit, 
  Activity, 
  Cpu, 
  Rocket, 
  RefreshCcw, 
  Layers,
  Settings,
  TrendingUp,
  Workflow,
  AdjustmentsHorizontal
} from 'lucide-react';
import { motion } from 'motion/react';
import { cn } from '../lib/utils';

export default function DeepMiningView() {
  return (
    <div className="flex h-full p-6 gap-6 relative overflow-hidden">
      {/* Node Workflow Editor */}
      <section className="flex-[2] glass-panel rounded-xl overflow-hidden relative flex shadow-[inset_0_0_40px_rgba(0,0,0,0.8)]">
        {/* Editor Grid */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(0,242,255,0.05)_1px,transparent_1px),linear-gradient(to_bottom,rgba(0,242,255,0.05)_1px,transparent_1px)] bg-[size:40px_40px] opacity-40" />

        {/* Sidebar Library */}
        <aside className="w-64 border-r border-slate-800 bg-slate-950/80 backdrop-blur-3xl z-20 flex flex-col h-full shadow-[4px_0_24px_rgba(0,0,0,0.4)]">
          <div className="p-4 border-b border-slate-800 bg-slate-900/40 flex items-center justify-between">
            <h2 className="font-display font-bold text-cyber-cyan uppercase tracking-widest text-xs">Node Library</h2>
            <Settings size={14} className="text-slate-500" />
          </div>

          <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-6 scroll-smooth">
            {/* Category */}
            <div>
              <h3 className="text-[10px] font-display font-bold text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2">
                <Database size={12} /> Data Ingestion
              </h3>
              <div className="flex flex-col gap-2">
                {['CSV Parser', 'REST Stream', 'SQL Query'].map(name => (
                  <div key={name} className="bg-slate-900 border border-slate-800 p-2 rounded flex items-center gap-2.5 cursor-grab hover:border-cyber-cyan/50 hover:bg-cyber-cyan/5 transition-all group">
                    <div className="w-6 h-6 rounded bg-slate-800 flex items-center justify-center text-slate-500 group-hover:text-cyber-cyan">
                      <Layers size={12} />
                    </div>
                    <span className="font-mono text-[11px] text-slate-300">{name}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* AI Models */}
            <div>
              <h3 className="text-[10px] font-display font-bold text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2">
                <BrainCircuit size={12} /> Deep Learning
              </h3>
              <div className="flex flex-col gap-2">
                {['CNN 2D', 'RNN LSTM', 'Transformer'].map(name => (
                  <div key={name} className="bg-cyber-purple/5 border border-cyber-purple/20 p-2 rounded flex items-center gap-2.5 cursor-grab hover:border-cyber-purple transition-all group">
                    <div className="w-6 h-6 rounded bg-cyber-purple/20 flex items-center justify-center text-cyber-purple-bright">
                      <Cpu size={12} />
                    </div>
                    <span className="font-mono text-[11px] text-cyber-purple-bright">{name}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </aside>

        {/* Canvas Area */}
        <div className="flex-1 relative cursor-crosshair">
           <svg className="absolute inset-0 w-full h-full pointer-events-none z-10Opacity-40">
             <path d="M 220 180 C 300 180, 300 240, 400 240" fill="none" stroke="#00dbe7" strokeWidth="1.5" strokeDasharray="4 4" />
             <path d="M 600 240 C 680 240, 680 320, 750 320" fill="none" stroke="#7701d0" strokeWidth="2" className="drop-shadow-[0_0_8px_#7701d0]" />
           </svg>

           {/* Ingest Node */}
           <div className="absolute top-[140px] left-[60px] w-44 bg-slate-900 border border-slate-800 rounded shadow-2xl z-20 overflow-hidden">
             <div className="bg-slate-800/50 px-3 py-1.5 border-b border-slate-700 flex justify-between items-center">
               <span className="font-mono text-[10px] font-bold text-slate-200">S3_Bucket</span>
               <div className="w-1.5 h-1.5 rounded-full bg-cyber-green animate-pulse" />
             </div>
             <div className="p-3">
               <div className="text-[9px] font-mono text-slate-500">Shape: (10k, 256, 256)</div>
               <div className="flex justify-end pt-2">
                 <div className="w-3 h-3 rounded-full border border-cyber-cyan bg-bg-deep translate-x-4.5" />
               </div>
             </div>
           </div>

           {/* Model Node */}
           <div className="absolute top-[180px] left-[380px] w-52 bg-slate-900 border border-cyber-cyan rounded shadow-2xl z-20 glow-cyan">
             <div className="bg-cyber-cyan/10 px-3 py-1.5 border-b border-cyber-cyan/30 flex justify-between items-center text-cyber-cyan font-bold">
               <span className="font-mono text-[10px]">Simple_CNN</span>
               <Settings size={12} />
             </div>
             <div className="p-3 relative">
                <div className="absolute -left-1.5 top-5 w-3 h-3 rounded-full border border-cyber-cyan bg-bg-deep" />
                <div className="space-y-1.5 text-[9px] font-mono text-slate-300">
                  <div className="flex justify-between border-b border-slate-800 pb-1"><span>Filters</span> <span className="text-cyber-cyan">64</span></div>
                  <div className="flex justify-between"><span>Kernel</span> <span className="text-cyber-cyan">(3, 3)</span></div>
                </div>
                <div className="absolute -right-1.5 top-1/2 -translate-y-1/2 w-3 h-3 rounded-full border border-cyber-purple bg-bg-deep" />
             </div>
           </div>

           {/* Active Scanning Line */}
           <motion.div 
             animate={{ top: ['0%', '100%', '0%'] }}
             transition={{ duration: 6, repeat: Infinity, ease: 'linear' }}
             className="absolute left-0 w-full h-[1px] bg-cyber-cyan/20 z-10"
           />
        </div>
      </section>

      {/* Training Metrics Panel */}
      <section className="flex-[1] flex flex-col gap-4 min-w-[320px] max-w-[420px]">
        {/* Status Card */}
        <div className="glass-panel p-5 rounded-xl bg-slate-900/40 relative overflow-hidden">
          <div className="flex justify-between items-start mb-6 relative z-10">
            <div>
              <h2 className="text-xl font-display font-bold text-slate-100 uppercase tracking-tight">Training Active</h2>
              <p className="font-mono text-[11px] text-slate-500">ID: <span className="text-cyber-purple-bright">#TRN-8892-X</span></p>
            </div>
            <button className="w-10 h-10 rounded-full border border-cyber-green/50 bg-cyber-green/5 flex items-center justify-center text-cyber-green shadow-[0_0_15px_rgba(42,229,0,0.2)]">
              <RefreshCcw size={18} className="animate-spin-slow" />
            </button>
          </div>

          <div className="mb-2 flex justify-between items-end font-mono text-[11px]">
            <span className="text-slate-400">Epoch Progress</span>
            <span className="text-cyber-cyan font-bold">45 / 100</span>
          </div>
          <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden border border-slate-700/50">
            <motion.div 
              initial={{ width: 0 }}
              animate={{ width: '45%' }}
              className="h-full bg-cyber-cyan shadow-[0_0_10px_rgba(0,219,231,0.8)] relative"
            >
              <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1.5 h-1.5 bg-white rounded-full shadow-[0_0_8px_white]" />
            </motion.div>
          </div>
          <div className="mt-2.5 flex justify-between font-mono text-[10px] text-slate-500 uppercase">
            <span>ETA: 02h 14m</span>
            <span>Batches: 256</span>
          </div>
        </div>

        {/* Dynamic Stats */}
        <div className="grid grid-cols-2 gap-4">
          <div className="glass-panel p-5 flex flex-col gap-4 items-center justify-center text-center">
            <div className="relative w-20 h-20">
              <svg className="w-full h-full transform -rotate-90">
                <circle cx="40" cy="40" r="34" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="4" />
                <circle cx="40" cy="40" r="34" fill="none" stroke="#2ae500" strokeWidth="4" strokeDasharray="213" strokeDashoffset="20" strokeLinecap="round" className="drop-shadow-[0_0_8px_rgba(42,229,0,0.5)]" />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center font-display font-bold text-lg text-cyber-green">92%</div>
            </div>
            <span className="text-[10px] font-display font-bold text-slate-500 uppercase tracking-widest">Val Accuracy</span>
          </div>

          <div className="glass-panel p-5 flex flex-col justify-between">
            <span className="text-[10px] font-display font-bold text-slate-500 uppercase tracking-widest">F1 Score</span>
            <div className="flex flex-col gap-1.5">
               <span className="text-3xl font-display font-bold text-slate-100">0.894</span>
               <div className="inline-flex items-center gap-1.5 text-cyber-green text-[10px] font-mono bg-cyber-green/5 border border-cyber-green/20 px-2 py-0.5 rounded w-fit">
                 <TrendingUp size={10} /> +0.012
               </div>
            </div>
          </div>
        </div>

        {/* Large Loss Chart */}
        <div className="glass-panel p-5 flex-1 flex flex-col overflow-hidden">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-[11px] font-display font-bold text-slate-200 uppercase tracking-widest">Loss Function</h3>
            <div className="flex gap-4 font-mono text-[9px] text-slate-500">
               <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-cyber-cyan" /> TRAIN</span>
               <span className="flex items-center gap-2"><div className="w-2 h-2 rounded-full bg-cyber-purple" /> VAL</span>
            </div>
          </div>

          <div className="flex-1 border-l border-b border-slate-800 relative py-2 pr-2">
             <div className="absolute inset-0 flex flex-col justify-between opacity-10 pointer-events-none">
               {[1, 2, 3, 4].map(i => <div key={i} className="border-t border-dashed border-slate-500 w-full" />)}
             </div>
             <svg className="w-full h-full overflow-visible" viewBox="0 0 100 80" preserveAspectRatio="none">
                <path d="M 0 70 Q 20 60, 40 30 T 70 15 T 100 10" fill="none" stroke="#00dbe7" strokeWidth="1.5" className="drop-shadow-[0_0_4px_#00dbe7]" />
                <path d="M 0 65 Q 20 55, 40 25 T 70 20 T 100 25" fill="none" stroke="#7701d0" strokeWidth="1.5" strokeDasharray="3 3" />
                <circle cx="80" cy="15" r="2.5" fill="#00dbe7" className="shadow-[0_0_10px_#00dbe7]" />
             </svg>
          </div>
        </div>

        <button className="h-16 bg-cyber-cyan text-bg-deep font-display font-bold text-md tracking-[0.2em] uppercase hover:bg-cyber-cyan-bright hover:shadow-[0_0_25px_rgba(0,219,231,0.6)] transition-all flex items-center justify-center gap-3 active:scale-[0.98] mt-2 mb-2">
          <Rocket size={20} />
          Deploy Model
        </button>
      </section>

      <style>{`
        .animate-spin-slow {
          animation: spin 6s linear infinite;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
