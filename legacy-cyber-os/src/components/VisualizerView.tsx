import React, { useState, useEffect, useRef } from 'react';
import { 
  Radar, 
  Activity, 
  Cpu, 
  Wifi, 
  Terminal
} from 'lucide-react';
import { motion } from 'motion/react';
import { cn } from '../lib/utils';

export default function VisualizerView() {
  const [intercepts, setIntercepts] = useState(84291);
  const [throughput, setThroughput] = useState(12.4);
  const [barData, setBarData] = useState([30, 45, 20, 60, 80, 50, 90, 100]);
  const [lineData, setLineData] = useState([5, 15, 10, 30, 25, 35, 20, 10]);
  
  const [logs, setLogs] = useState([
    { id: 1, type: 'SYS', color: 'text-cyber-cyan', text: 'Initializing neural pathways...' },
    { id: 2, type: 'SYS', color: 'text-cyber-cyan', text: 'Handshake established with Node-Alpha.' },
    { id: 3, type: 'NET', color: 'text-cyber-purple', text: 'Rerouting packet flow through proxy-7...' },
    { id: 4, type: 'OK', color: 'text-cyber-green', text: 'Encryption keys verified. Tunnel secure.' },
    { id: 5, type: 'WARN', color: 'text-cyber-red font-bold', text: 'Latency spike detected on link 90-B.' }
  ]);

  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const interval = setInterval(() => {
      // Simulate intercepts
      setIntercepts(prev => prev + Math.floor(Math.random() * 85) + 12);
      
      // Simulate throughput
      setThroughput(prev => {
        const change = (Math.random() - 0.5) * 2.5;
        return Number(Math.max(8.0, Math.min(28.0, prev + change)).toFixed(1));
      });

      // Update charts
      setBarData(prev => [...prev.slice(1), Math.floor(Math.random() * 80) + 20]);
      setLineData(prev => [...prev.slice(1), Math.floor(Math.random() * 35) + 5]);

      // Random logs
      if (Math.random() > 0.6) {
        const events = [
          { type: 'SYS', color: 'text-cyber-cyan', text: 'Calibrating temporal variance in Sector 4G.' },
          { type: 'NET', color: 'text-cyber-purple', text: 'Anomaly detected in packet header. Dropping.' },
          { type: 'OK', color: 'text-cyber-green', text: 'Data block hash matching successful.' },
          { type: 'AI', color: 'text-slate-300', text: 'Model weights updated.' },
        ];
        const evt = events[Math.floor(Math.random() * events.length)];
        setLogs(prev => [...prev.slice(-9), { id: Date.now(), ...evt }]);
      }
    }, 1200);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const pathD = lineData.map((val, idx) => `${idx === 0 ? 'M' : 'L'}${idx * (100 / (lineData.length - 1))} ${40 - val}`).join(' ');

  return (
    <div className="p-6 grid grid-cols-12 gap-6 content-start h-full pb-20">
      {/* Left Column */}
      <div className="col-span-3 flex flex-col gap-6">
        {/* Metric Card 1 */}
        <div className="glass-panel p-5 relative overflow-hidden group">
          <motion.div 
            animate={{ top: ['0%', '100%', '0%'] }}
            transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
            className="absolute left-0 w-full h-[1px] bg-cyber-cyan/40 shadow-[0_0_8px_#00dbe7] z-0"
          />
          <div className="flex justify-between items-start mb-4 relative z-10">
            <div className="flex items-center gap-2">
              <Radar size={14} className="text-cyber-cyan" />
              <span className="font-display font-bold text-[10px] tracking-widest text-slate-400 uppercase">Global Intercepts</span>
            </div>
            <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-cyber-green/10 border border-cyber-green/30 text-cyber-green text-[9px] font-bold">
              <div className="w-1 h-1 rounded-full bg-cyber-green animate-pulse shadow-[0_0_5px_#2ae500]" />
              LIVE
            </span>
          </div>
          <div className="text-4xl font-display font-bold text-cyber-cyan-bright tracking-tight mb-4 relative z-10 font-mono">
            {intercepts.toLocaleString()}
          </div>
          <div className="h-10 flex items-end gap-1 relative z-10">
            {barData.map((h, i) => (
              <div 
                key={i} 
                className="flex-1 bg-cyber-cyan-bright/30 transition-all duration-500 ease-out" 
                style={{ height: `${h}%` }} 
              />
            ))}
          </div>
        </div>

        {/* Metric Card 2 */}
        <div className="glass-panel p-5 relative overflow-hidden">
          <div className="absolute right-0 top-0 w-32 h-32 bg-cyber-purple/10 blur-[50px] -mr-10 -mt-10" />
          <div className="flex items-center gap-2 mb-4">
            <Activity size={14} className="text-cyber-purple" />
            <span className="font-display font-bold text-[10px] tracking-widest text-slate-400 uppercase">Node Throughput</span>
          </div>
          <div className="text-3xl font-display font-bold text-cyber-purple-bright mb-4 font-mono">
            {throughput.toFixed(1)} <span className="text-xs text-slate-500 font-sans tracking-normal ml-1">TB/s</span>
          </div>
          <div className="h-12 border-b border-l border-slate-700/50 relative">
            <svg className="w-full h-full overflow-visible" preserveAspectRatio="none" viewBox="0 0 100 40">
              <path 
                d={pathD}
                fill="none" 
                stroke="currentColor" 
                strokeWidth="1.5"
                className="text-cyber-purple transition-all duration-500 ease-linear"
              />
              <circle cx="100" cy={40 - lineData[lineData.length - 1]} r="3" fill="white" className="shadow-[0_0_10px_white] transition-all duration-500 ease-linear" />
            </svg>
          </div>
        </div>

        {/* Active Entities List */}
        <div className="glass-panel p-5 flex flex-col gap-4 flex-1 overflow-hidden">
          <div className="flex items-center gap-2 pb-2 border-b border-slate-800">
            <Cpu size={14} className="text-cyber-cyan" />
            <span className="font-display font-bold text-[10px] tracking-widest text-slate-400 uppercase">Active Entities</span>
          </div>
          <div className="flex flex-col gap-4 overflow-y-auto pr-2">
            {[
              { id: 'AX-1', name: 'Crawler Alpha', zone: 'EU-West', stat: '99.8%', status: 'ok' },
              { id: 'BT-9', name: 'Deep Miner', zone: 'US-East', stat: '84.2%', status: 'active' },
              { id: 'XR-0', name: 'Node Sync', zone: 'AP-South', stat: 'WARN', status: 'error' },
              { id: 'KV-2', name: 'Shell Probe', zone: 'CA-Central', stat: '12.1%', status: 'idle' },
            ].map((node) => (
              <div key={node.id} className="flex items-center justify-between group">
                <div className="flex items-center gap-3">
                  <div className={cn(
                    "w-8 h-8 rounded border flex items-center justify-center text-[9px] font-mono",
                    node.status === 'ok' && "border-cyber-green/50 text-cyber-green bg-cyber-green/5",
                    node.status === 'error' && "border-cyber-red/50 text-cyber-red bg-cyber-red/5",
                    node.status === 'active' && "border-cyber-cyan/50 text-cyber-cyan bg-cyber-cyan/5",
                    node.status === 'idle' && "border-slate-700 text-slate-500 bg-slate-900",
                  )}>
                    {node.id}
                  </div>
                  <div className="flex flex-col">
                    <span className="text-xs font-bold text-slate-200 uppercase tracking-tight">{node.name}</span>
                    <span className="text-[9px] text-slate-500 font-mono tracking-widest uppercase">{node.zone}</span>
                  </div>
                </div>
                <div className={cn(
                  "text-[11px] font-mono font-bold",
                  node.status === 'error' ? "text-cyber-red animate-pulse" : "text-slate-400"
                )}>
                  {node.stat}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Center Column: Globe Visualizer */}
      <div className="col-span-6 flex flex-col relative h-[calc(100vh-12rem)]">
        <div className="flex-1 glass-panel relative overflow-hidden flex items-center justify-center group cursor-crosshair">
          {/* Decorative HUD Elements */}
          <div className="absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 border-cyber-cyan m-6 opacity-40 group-hover:opacity-100 transition-opacity" />
          <div className="absolute top-0 right-0 w-8 h-8 border-t-2 border-r-2 border-cyber-cyan m-6 opacity-40 group-hover:opacity-100 transition-opacity" />
          <div className="absolute bottom-0 left-0 w-8 h-8 border-b-2 border-l-2 border-cyber-cyan m-6 opacity-40 group-hover:opacity-100 transition-opacity" />
          <div className="absolute bottom-0 right-0 w-8 h-8 border-b-2 border-r-2 border-cyber-cyan m-6 opacity-40 group-hover:opacity-100 transition-opacity" />

          {/* HUD Badge */}
          <div className="absolute top-6 left-1/2 -translate-x-1/2 flex gap-2 z-20">
            <span className="font-mono text-[9px] text-cyber-cyan border border-cyber-cyan/40 bg-cyber-cyan/10 px-3 py-1 rounded tracking-[0.2em] uppercase">Global Mesh</span>
            <span className="font-mono text-[9px] text-cyber-purple border border-cyber-purple/40 bg-cyber-purple/10 px-3 py-1 rounded tracking-[0.2em] uppercase">Deep Core</span>
          </div>

          <div className="absolute bottom-6 left-6 font-mono text-[9px] text-slate-500 flex flex-col gap-1 opacity-60 z-20">
            <span>LAT: 45.9128 N</span>
            <span>LNG: 12.0834 E</span>
            <span className="text-cyber-cyan">ALT: 40,291M</span>
          </div>

          {/* Globe Image - Now rotating */}
          <motion.div 
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 0.7, rotate: 360 }}
            transition={{ 
              scale: { duration: 1 }, 
              opacity: { duration: 1 },
              rotate: { duration: 120, repeat: Infinity, ease: 'linear' }
            }}
            className="relative w-[85%] h-[85%]"
          >
            <img 
              alt="Global Intelligence" 
              className="w-full h-full object-contain mix-blend-screen contrast-125 saturate-150 rounded-full"
              src="https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=1024&auto=format&fit=crop" 
            />
            {/* Center Glow */}
            <div className="absolute inset-0 m-auto w-48 h-48 bg-cyber-cyan/20 rounded-full blur-[80px]" />
            
            {/* Interactive Points that remain fixed relative to the rotating globe container */}
            <motion.div 
              animate={{ opacity: [0.4, 1, 0.4] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="absolute top-[30%] left-[20%] w-3 h-3 bg-cyber-purple rounded-full shadow-[0_0_15px_#7701d0] z-20"
            >
              <div className="absolute top-4 left-4 whitespace-nowrap bg-bg-deep/80 border border-cyber-purple/50 px-2 py-1 text-[8px] font-mono text-cyber-purple drop-shadow-md">
                ANOMALY_DETECTED
              </div>
            </motion.div>

            <motion.div 
              animate={{ opacity: [1, 0.4, 1] }}
              transition={{ duration: 3, repeat: Infinity }}
              className="absolute top-[60%] right-[25%] w-3 h-3 bg-cyber-cyan rounded-full shadow-[0_0_15px_#00dbe7] z-20"
            >
              <div className="absolute top-4 left-4 whitespace-nowrap bg-bg-deep/80 border border-cyber-cyan/50 px-2 py-1 text-[8px] font-mono text-cyber-cyan">
                SECURE_UPLINK
              </div>
            </motion.div>
          </motion.div>

          {/* Scrolling Scanning Line */}
          <motion.div 
            animate={{ top: ['20%', '80%', '20%'] }}
            transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
            className="absolute left-0 w-full h-[2px] bg-cyber-cyan/40 shadow-[0_0_20px_rgba(0,219,231,0.8)] z-10"
          />
        </div>
      </div>

      {/* Right Column */}
      <div className="col-span-3 flex flex-col gap-6">
        {/* Radar Widget */}
        <div className="glass-panel p-5 flex flex-col items-center">
          <div className="w-full flex justify-between items-center mb-6">
            <div className="flex items-center gap-2">
              <Wifi size={14} className="text-cyber-cyan" />
              <span className="font-display font-bold text-[10px] tracking-widest text-slate-400 uppercase">System Radar</span>
            </div>
            <span className="text-[9px] px-1.5 py-0.5 border border-cyber-green/50 text-cyber-green font-bold">OPTIMAL</span>
          </div>

          <div className="relative w-48 h-48 border border-slate-700/30 rounded-full flex items-center justify-center">
            {[1, 2, 3].map(i => (
              <div 
                key={i} 
                className="absolute inset-0 rounded-full border border-slate-700/20" 
                style={{ margin: `${i * 1.5}rem` }} 
              />
            ))}
            
            <motion.div 
              animate={{ rotate: 360 }}
              transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
              className="absolute inset-0 rounded-full bg-[conic-gradient(from_0deg,transparent_0%,rgba(0,219,231,0.1)_100%)] border-r-2 border-cyber-cyan/30"
            />

            <div className="w-4 h-4 bg-cyber-cyan rounded-full shadow-[0_0_15px_rgba(0,219,231,0.6)] z-20 flex items-center justify-center">
              <div className="w-1.5 h-1.5 bg-bg-deep rounded-full" />
            </div>

            {/* Pings */}
            <div className="absolute top-[25%] right-[20%] w-2 h-2 bg-cyber-purple rounded-full shadow-[0_0_8px_#7701d0]" />
            <div className="absolute bottom-[30%] left-[15%] w-1.5 h-1.5 bg-cyber-cyan rounded-full shadow-[0_0_5px_#00dbe7]" />
          </div>
        </div>

        {/* Console Logs */}
        <div className="glass-panel p-5 flex-1 flex flex-col overflow-hidden bg-slate-950/60">
          <div className="flex items-center gap-2 pb-3 mb-3 border-b border-slate-800 shrink-0">
            <Terminal size={14} className="text-slate-400" />
            <span className="font-display font-bold text-[10px] tracking-widest text-slate-200 uppercase">Live Kernel Logs</span>
          </div>
          
          <div className="flex-1 overflow-y-auto font-mono text-[10px] leading-relaxed flex flex-col gap-1.5 pr-2">
            {logs.map((log) => (
              <motion.p 
                key={log.id} 
                initial={{ opacity: 0, x: -10 }} 
                animate={{ opacity: 1, x: 0 }}
              >
                <span className={log.color}>[{log.type}]</span> {log.text}
              </motion.p>
            ))}
            <div ref={logsEndRef} />
            
            <div className="mt-2 flex items-center gap-2 text-cyber-cyan">
              <span>&gt;</span>
              <motion.div 
                animate={{ opacity: [1, 0, 1] }} 
                transition={{ duration: 0.8, repeat: Infinity }}
                className="w-1.5 h-3 bg-cyber-cyan" 
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
