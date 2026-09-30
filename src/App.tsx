/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { 
  LayoutGrid, 
  Layers, 
  Database, 
  BrainCircuit, 
  Microscope, 
  FileText, 
  Terminal, 
  Activity, 
  Plus, 
  Search, 
  Bell, 
  Settings,
  User
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { cn } from './lib/utils';
import ParticleNetwork from './components/ParticleNetwork';

// Views
import VisualizerView from './components/VisualizerView';
import DataNodesView from './components/DataNodesView';
import ReportsView from './components/ReportsView';
import DeepMiningView from './components/DeepMiningView';

type ViewType = 'dashboard' | 'visualizer' | 'data-nodes' | 'intelligence' | 'deep-mining' | 'reports';

export default function App() {
  const [activeView, setActiveView] = useState<ViewType>('visualizer');
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutGrid },
    { id: 'visualizer', label: 'Visualizer', icon: Layers },
    { id: 'data-nodes', label: 'Data Nodes', icon: Database },
    { id: 'intelligence', label: 'Intelligence', icon: BrainCircuit },
    { id: 'deep-mining', label: 'Deep Mining', icon: Microscope },
    { id: 'reports', label: 'Reports', icon: FileText },
  ] as const;

  return (
    <div className="flex h-screen w-full bg-bg-deep text-slate-300 font-sans selection:bg-cyber-cyan/30">
      {/* Particle Effect Layer */}
      <ParticleNetwork />
      
      {/* Ambient Grid Pattern */}
      <div className="fixed inset-0 z-0 bg-[linear-gradient(to_right,#84949515_1px,transparent_1px),linear-gradient(to_bottom,#84949515_1px,transparent_1px)] bg-[size:24px_24px] pointer-events-none" />
      <div className="fixed inset-0 z-0 bg-[radial-gradient(ellipse_at_center,rgba(0,219,231,0.03)_0%,rgba(13,19,33,1)_70%)] pointer-events-none" />

      {/* Sidebar */}
      <nav className="fixed left-0 top-0 h-full w-64 glass-panel flex flex-col py-8 z-40">
        <div className="px-6 mb-10 flex flex-col gap-1">
          <h1 className="text-cyber-cyan font-display font-black tracking-widest text-2xl drop-shadow-[0_0_8px_rgba(0,242,255,0.4)]">
            CYBER_OS
          </h1>
          <span className="text-slate-500 font-mono text-[10px] tracking-widest uppercase">KERNEL v4.2</span>
        </div>

        <div className="px-5 mb-8">
          <button className="w-full py-3 bg-cyber-cyan/10 border border-cyber-cyan/50 text-cyber-cyan font-display font-bold text-xs tracking-widest hover:bg-cyber-cyan/20 transition-all rounded flex items-center justify-center gap-2 group">
            <Plus size={16} className="group-hover:scale-125 transition-transform" />
            NEW ANALYSIS
          </button>
        </div>

        <ul className="flex-1 flex flex-col gap-1 font-display font-bold tracking-tighter text-sm">
          {navItems.map(({ id, label, icon: Icon }) => (
            <li key={id}>
              <button
                onClick={() => setActiveView(id)}
                className={cn(
                  "w-full flex items-center gap-4 px-6 py-3 transition-all relative group",
                  activeView === id 
                    ? "bg-cyber-cyan/10 text-cyber-cyan border-r-2 border-cyber-cyan shadow-[0_0_20px_rgba(0,242,255,0.1)]" 
                    : "text-slate-400 opacity-70 hover:bg-cyber-cyan/5 hover:opacity-100"
                )}
              >
                <Icon size={18} className={cn(activeView === id && "fill-current")} />
                <span className="uppercase tracking-widest text-[11px]">{label}</span>
                {activeView === id && (
                  <motion.div 
                    layoutId="nav-glow"
                    className="absolute inset-0 bg-cyber-cyan/5 pointer-events-none"
                  />
                )}
              </button>
            </li>
          ))}
        </ul>

        <div className="mt-auto pt-6 border-t border-cyan-500/10 flex flex-col gap-1 font-display text-xs font-bold tracking-tighter">
          <button className="flex items-center gap-4 px-6 py-3 text-slate-400 opacity-70 hover:bg-cyan-500/5 hover:opacity-100 transition-all">
            <Terminal size={16} />
            <span className="uppercase tracking-widest text-[10px]">Terminal</span>
          </button>
          <button className="flex items-center gap-4 px-6 py-3 text-slate-400 opacity-70 hover:bg-cyan-500/5 hover:opacity-100 transition-all">
            <Activity size={16} />
            <span className="uppercase tracking-widest text-[10px]">System Status</span>
          </button>
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-1 ml-64 flex flex-col h-full relative z-10 transition-all duration-500">
        {/* Header */}
        <header className="flex justify-between items-center w-full px-8 h-16 bg-slate-950/60 backdrop-blur-md border-b border-cyan-500/20 shadow-[0_4px_20px_rgba(0,0,0,0.5)] z-30 shrink-0">
          <div className="flex items-center gap-6">
            <div className="text-xl font-display font-black text-cyber-cyan drop-shadow-[0_0_10px_rgba(0,242,255,0.6)] tracking-widest uppercase">
              NEURAL_CORE
            </div>
            {/* Real-time Clock */}
            <div className="hidden md:flex items-center gap-2 px-3 py-1 bg-cyber-cyan/5 border border-cyber-cyan/20 rounded font-mono text-[10px] text-cyber-cyan">
              <Activity size={12} className="animate-pulse opacity-70" />
              <span>{time.toISOString().replace('T', ' ').substring(0, 19)} UTC</span>
            </div>
          </div>

          <div className="flex items-center gap-6">
            <div className="relative group">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 group-hover:text-cyber-cyan transition-colors" size={14} />
              <input 
                className="bg-slate-900/50 border-b border-slate-700 text-slate-300 pl-10 pr-4 py-1.5 text-[11px] font-mono tracking-widest focus:outline-none focus:border-cyber-cyan focus:bg-cyber-cyan/5 transition-all w-64"
                placeholder="QUERY INDEX..."
                type="text"
              />
              <div className="absolute right-0 bottom-0 w-2 h-2 bg-cyber-cyan opacity-0 group-focus-within:opacity-100 transition-opacity" />
            </div>

            <div className="flex items-center gap-2 border-l border-cyan-500/20 pl-6">
              <button className="text-slate-500 hover:text-cyber-cyan hover:bg-cyber-cyan/5 p-2 rounded-full transition-all relative">
                <Bell size={20} />
                <span className="absolute top-2 right-2 w-2 h-2 bg-cyber-purple rounded-full shadow-[0_0_8px_#7701d0]" />
              </button>
              <button className="text-slate-500 hover:text-cyber-cyan hover:bg-cyber-cyan/5 p-2 rounded-full transition-all">
                <Settings size={20} />
              </button>
              <div className="w-9 h-9 rounded-full border border-cyber-cyan/40 overflow-hidden ml-2 relative group cursor-pointer">
                <div className="absolute inset-0 bg-cyber-cyan/20 group-hover:bg-cyber-cyan/40 transition-colors z-10" />
                <User className="absolute inset-0 m-auto text-cyber-cyan z-0" size={20} />
                <img 
                  alt="Analyst" 
                  className="w-full h-full object-cover mix-blend-luminosity opacity-80"
                  src="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=100&auto=format&fit=crop" 
                />
              </div>
            </div>
          </div>
        </header>

        {/* View Switcher */}
        <div className="flex-1 relative overflow-hidden">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeView}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.4, ease: "easeOut" }}
              className="h-full w-full overflow-y-auto"
            >
              {activeView === 'visualizer' && <VisualizerView />}
              {activeView === 'data-nodes' && <DataNodesView />}
              {activeView === 'reports' && <ReportsView />}
              {activeView === 'deep-mining' && <DeepMiningView />}
              {(activeView === 'dashboard' || activeView === 'intelligence') && (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center p-10 glass-panel max-w-md">
                    <h2 className="text-2xl font-display font-bold text-cyber-cyan mb-4 uppercase tracking-tighter">Access restricted</h2>
                    <p className="text-slate-400 text-sm italic">User authentication insufficient for this sector. Please re-verify kernel credentials.</p>
                  </div>
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Footer Ticker */}
        <footer className="h-10 bg-slate-950/90 backdrop-blur-md border-t border-cyan-500/20 z-40 flex items-center px-6 overflow-hidden">
          <div className="flex items-center gap-2 text-cyber-cyan border-r border-cyan-500/30 pr-4 shrink-0">
            <Activity size={14} className="animate-pulse" />
            <span className="font-display font-bold text-[10px] tracking-widest uppercase">LIVE FEED</span>
          </div>
          
          <div className="flex-1 overflow-hidden relative">
            <div className="animate-marquee whitespace-nowrap flex items-center gap-10 font-mono text-[10px] text-slate-400 tracking-wider">
              <span><span className="text-cyber-cyan">[SYS]</span> Handshake established with Node-Alpha.</span>
              <span><span className="text-cyber-purple">[NET]</span> Rerouting packet flow through proxy-7...</span>
              <span><span className="text-cyber-green">[OK]</span> Encryption keys verified. Tunnel secure.</span>
              <span><span className="text-cyber-cyan">0x8F2A</span>: Packet injection successful.</span>
              <span><span className="text-cyber-red">WARN</span>: Latency spike detected on link 90-B.</span>
              <span><span className="text-cyber-cyan">TRX-9</span>: Data payload extracted (4.2GB).</span>
            </div>
          </div>
        </footer>
      </main>

      <style>{`
        @keyframes marquee {
          0% { transform: translateX(100%); }
          100% { transform: translateX(-100%); }
        }
        .animate-marquee {
          animation: marquee 30s linear infinite;
        }
      `}</style>
    </div>
  );
}
