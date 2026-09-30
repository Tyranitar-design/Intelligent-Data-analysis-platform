import React from 'react';
import { 
  Database, 
  Server, 
  Globe, 
  Code, 
  CloudOff, 
  TrendingUp, 
  Zap, 
  ShieldCheck,
  Search,
  Filter,
  Plus,
  Layers
} from 'lucide-react';
import { motion } from 'motion/react';
import { cn } from '../lib/utils';

export default function DataNodesView() {
  const nodes = [
    { id: 1, type: 'SQL', name: 'Global Users DB', url: 'postgres://core-cluster:5432', sync: '12 mins ago', bandwidth: '45.2 MB/s', status: 'connected' },
    { id: 2, type: 'NoSQL', name: 'Telemetry Logs', url: 'mongodb://shard-01:27017', sync: 'Live Stream', bandwidth: '1.2k ops/s', status: 'connected' },
    { id: 3, type: 'Crawler', name: 'Market Sentinel', url: 'Target: 45 Global Exchanges', sync: 'Extracting (45%)', bandwidth: '12/12 Nodes', status: 'processing' },
    { id: 4, type: 'API', name: 'Financial Alpha', url: 'Endpoint: /v3/ticker/book', sync: 'Syncing Batches', bandwidth: '85% Utilized', status: 'connected' },
    { id: 5, type: 'Archive', name: 'Cold Storage Zeta', url: 'aws-s3-eu-west-1', sync: 'Disconnected', bandwidth: '4 Days Ago', status: 'offline' },
  ];

  return (
    <div className="flex h-full">
      {/* Left Area: Main Content */}
      <div className="flex-1 p-8 flex flex-col gap-8 overflow-y-auto pb-24">
        {/* Header Section */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 border-b border-slate-800 pb-8">
          <div>
            <h1 className="text-3xl font-display font-bold text-slate-100 tracking-tight neon-text-cyan mb-1">Data Sources & Crawlers</h1>
            <p className="text-slate-400 text-sm">Manage active connections, sync rates, and extraction nodes.</p>
          </div>
          
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-1">
            {['ALL', 'SQL', 'NoSQL', 'API', 'CRAWLER'].map((cat, i) => (
              <button 
                key={cat}
                className={cn(
                  "px-5 py-2 rounded-md font-display font-bold text-[10px] tracking-widest transition-all",
                  i === 0 ? "bg-slate-700 text-cyber-cyan shadow-[0_0_10px_rgba(0,219,231,0.2)]" : "text-slate-500 hover:text-slate-200"
                )}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Central visual bridge */}
        <div className="flex justify-center -my-4 relative h-12">
          <div className="h-px w-32 bg-gradient-to-r from-transparent to-cyber-cyan/50" />
          <div className="w-10 h-10 rounded-full border border-cyber-cyan/40 bg-slate-900 flex items-center justify-center -mt-5 relative z-10 shadow-[0_0_15px_rgba(0,219,231,0.2)]">
            <Server size={18} className="text-cyber-cyan" />
          </div>
          <div className="h-px w-32 bg-gradient-to-l from-transparent to-cyber-cyan/50" />
        </div>

        {/* Grid Area */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {nodes.map((node) => (
            <motion.div 
              key={node.id}
              whileHover={{ y: -4 }}
              className={cn(
                "glass-panel p-6 relative overflow-hidden group transition-all",
                node.status === 'offline' && "bg-slate-900/20 border-cyber-red/20",
                node.status === 'processing' && "border-cyber-purple/30 shadow-[0_0_15px_rgba(119,1,208,0.05)]"
              )}
            >
              <div className="absolute top-0 left-0 w-full h-[1px] bg-cyber-cyan/20 group-hover:bg-cyber-cyan/50" />
              
              <div className="flex justify-between items-start mb-6">
                <div className={cn(
                  "w-11 h-11 rounded border flex items-center justify-center",
                  node.status === 'offline' ? "border-cyber-red/30 text-cyber-red" : "border-slate-700 text-slate-300 group-hover:border-cyber-cyan/50"
                )}>
                  {node.type === 'SQL' && <Database size={20} />}
                  {node.type === 'NoSQL' && <Layers size={20} />}
                  {node.type === 'Crawler' && <Search size={20} />}
                  {node.type === 'API' && <Code size={20} />}
                  {node.status === 'offline' && <CloudOff size={20} />}
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-display font-bold text-[9px] tracking-widest text-slate-500 uppercase">{node.type}</span>
                  <div className={cn(
                    "w-2 h-2 rounded-full",
                    node.status === 'connected' ? "bg-cyber-green shadow-[0_0_8px_#2ae500]" : 
                    node.status === 'processing' ? "bg-cyber-purple shadow-[0_0_8px_#7701d0]" : "bg-cyber-red shadow-[0_0_8px_#ffb4ab]"
                  )} />
                </div>
              </div>

              <h3 className="text-lg font-display font-bold text-slate-200 group-hover:text-cyber-cyan transition-colors mb-1">{node.name}</h3>
              <p className="font-mono text-[10px] text-slate-500 mb-6 truncate">{node.url}</p>

              <div className="flex flex-col gap-2 mb-6 pt-4 border-t border-slate-800/50">
                <div className="flex justify-between text-[11px] font-mono">
                  <span className="text-slate-500 uppercase tracking-tight">Last Sync:</span>
                  <span className={cn(node.status === 'processing' ? "text-cyber-purple" : "text-slate-300")}>{node.sync}</span>
                </div>
                <div className="flex justify-between text-[11px] font-mono">
                  <span className="text-slate-500 uppercase tracking-tight">Throughput:</span>
                  <span className="text-slate-300">{node.bandwidth}</span>
                </div>
              </div>

              <button className={cn(
                "w-full py-2.5 rounded border font-display font-bold text-[10px] tracking-widest uppercase transition-all",
                node.status === 'offline' ? "border-slate-800 text-slate-700 bg-slate-900/50 cursor-not-allowed" : 
                node.status === 'processing' ? "bg-cyber-red/10 border-cyber-red/30 text-cyber-red hover:bg-cyber-red/20" : "border-cyber-cyan/40 text-cyber-cyan hover:bg-cyber-cyan/10"
              )}>
                {node.status === 'connected' ? 'Run Sync' : node.status === 'processing' ? 'Halt Process' : 'Reconnect'}
              </button>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Right Area: Sidebar Telemetry */}
      <aside className="w-80 border-l border-slate-800 bg-slate-950/60 backdrop-blur-3xl p-8 flex flex-col gap-10 shrink-0">
        <div>
          <h2 className="text-xl font-display font-bold text-slate-100 flex items-center gap-3 mb-6">
            <Zap size={20} className="text-cyber-cyan" />
            System Telemetry
          </h2>
          
          <div className="flex flex-col gap-4">
            <span className="text-[10px] font-display font-bold text-slate-500 tracking-widest uppercase">Overall Health</span>
            <div className="flex items-end gap-3 leading-none">
              <span className="text-5xl font-display font-bold text-cyber-green neon-text-green">98.4<span className="text-2xl opacity-50">%</span></span>
              <span className="text-xs text-cyber-green flex items-center mb-1">
                <TrendingUp size={12} className="mr-1" /> 0.2%
              </span>
            </div>
            <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden mt-2">
              <div className="h-full bg-cyber-green w-[98.4%] shadow-[0_0_10px_#2ae500]" />
            </div>
          </div>
        </div>

        <div>
           <div className="flex justify-between items-center mb-4">
             <span className="text-[10px] font-display font-bold text-slate-500 tracking-widest uppercase">Ingestion Rate</span>
             <span className="text-xs font-mono text-cyber-cyan-bright">1.2 GB/s</span>
           </div>
           <div className="h-28 glass-panel bg-slate-900/40 p-2 flex items-end gap-1.5 rounded">
             {[40, 60, 30, 80, 50, 70, 90].map((h, i) => (
                <div 
                  key={i} 
                  className={cn(
                    "flex-1 rounded-sm transition-all duration-1000",
                    i === 6 ? "bg-cyber-cyan shadow-[0_0_8px_#00dbe7]" : "bg-cyber-cyan/20"
                  )} 
                  style={{ height: `${h}%` }} 
                />
             ))}
           </div>
        </div>

        <div className="flex-1 flex flex-col overflow-hidden">
          <span className="text-[10px] font-display font-bold text-slate-500 tracking-widest uppercase mb-4">Live Event Stream</span>
          <div className="flex-1 overflow-y-auto pr-2 flex flex-col gap-4 font-mono text-[10px]">
            {[
              { time: '14:02:11', msg: 'PostgreSQL sync complete.', color: 'text-cyber-green' },
              { time: '14:02:05', msg: 'Market Sentinel node #4 spawned.', color: 'text-cyber-purple' },
              { time: '14:01:42', msg: 'WARN: Rate limit on API_02.', color: 'text-cyber-red' },
              { time: '14:00:00', msg: 'Scheduled cluster backup initiated.', color: 'text-cyber-cyan' },
              { time: '13:58:12', msg: 'Deep Miner heartbeat verified.', color: 'text-slate-400' },
            ].map((ev, i) => (
              <div key={i} className="flex gap-3 leading-relaxed">
                <span className={cn("font-bold shrink-0", ev.color)}>[{ev.time}]</span>
                <span className="text-slate-400">{ev.msg}</span>
              </div>
            ))}
          </div>
        </div>
      </aside>

      {/* FAB */}
      <button className="fixed bottom-12 right-[340px] w-14 h-14 bg-cyber-cyan text-bg-deep rounded-xl flex items-center justify-center shadow-[0_0_20px_rgba(0,219,231,0.5)] hover:scale-110 active:scale-95 transition-all z-50 border border-cyber-cyan-bright/50 group">
        <Plus className="group-hover:rotate-90 transition-transform" />
      </button>

      <style>{`
        .neon-text-green { text-shadow: 0 0 10px rgba(42, 229, 0, 0.4); }
      `}</style>
    </div>
  );
}
