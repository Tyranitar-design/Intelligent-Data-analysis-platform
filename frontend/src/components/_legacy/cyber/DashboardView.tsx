import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Shield, Zap, Activity, Cpu, Box, Database, Radar, ArrowRight, TrendingUp, Newspaper, ShoppingCart } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ScrambleText, SplitWords } from '../Typography';

interface StatsData {
  totalData: number;
  stockCount: number;
  energyCount: number;
  newsCount: number;
  ecomCount: number;
}

interface Props {
  onNavigate?: (view: string) => void;
  stats?: StatsData;
}

export default function DashboardView({ onNavigate, stats }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let w = (canvas.width = canvas.offsetWidth);
    let h = (canvas.height = canvas.offsetHeight);
    let time = 0;
    let raf = 0;

    const resize = () => {
      w = canvas.width = canvas.offsetWidth;
      h = canvas.height = canvas.offsetHeight;
    };
    window.addEventListener('resize', resize);

    const draw = () => {
      ctx.fillStyle = 'rgba(8, 14, 28, 0.22)';
      ctx.fillRect(0, 0, w, h);

      const lines = 50;
      for (let i = 0; i < lines; i++) {
        const persp = i / lines;
        ctx.beginPath();
        for (let x = 0; x <= w; x += 24) {
          const yOff =
            Math.sin(x * 0.003 + time + i * 0.15) * 80 +
            Math.sin(x * 0.008 - time * 0.8 + i * 0.05) * 30 +
            Math.cos(x * 0.005 + time * 1.2) * 40;
          const y = h * 0.6 + yOff * persp + (i - lines / 2) * 22 * persp;
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        const hue = 185 + Math.sin(time * 0.4 + i * 0.1) * 80;
        const light = 45 + Math.sin(time + i * 0.2) * 18;
        const alpha = 0.18 + (i / lines) * 0.55;
        ctx.strokeStyle = `hsla(${hue}, 95%, ${light}, ${alpha})`;
        ctx.lineWidth = 0.6 + persp * 1.6;
        ctx.stroke();
      }
      time += 0.014;
      raf = requestAnimationFrame(draw);
    };
    draw();
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
    };
  }, []);

  // 使用真实数据或默认数据
  const displayStats = [
    { name: '数据总量', val: stats?.totalData?.toLocaleString() || '0', icon: Database, color: 'text-cyber-cyan' },
    { name: '股票数据', val: stats?.stockCount?.toLocaleString() || '0', icon: TrendingUp, color: 'text-cyber-green' },
    { name: '能源数据', val: stats?.energyCount?.toLocaleString() || '0', icon: Zap, color: 'text-cyber-purple-bright' },
    { name: '新闻数据', val: stats?.newsCount?.toLocaleString() || '0', icon: Newspaper, color: 'text-slate-200' },
  ];

  return (
    <div className="relative w-full h-full p-8 overflow-hidden flex flex-col">
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full z-0 opacity-90" />

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6 }}
        className="relative z-10 w-full flex flex-col gap-8 h-full"
      >
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-3">
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 }}
              className="px-3 py-1 bg-cyber-cyan/10 border border-cyber-cyan/30 rounded text-cyber-cyan font-mono text-[10px] tracking-widest uppercase flex items-center gap-2"
            >
              <span className="w-1.5 h-1.5 bg-cyber-cyan rounded-full animate-pulse shadow-[0_0_8px_hsl(var(--cyber-cyan))]" />
              <ScrambleText text="系统启动完成" delay={300} />
            </motion.div>
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 }}
              className="px-3 py-1 bg-cyber-purple/10 border border-cyber-purple/40 rounded text-cyber-purple-bright font-mono text-[10px] tracking-widest uppercase flex items-center gap-2"
            >
              <Zap size={12} />
              <ScrambleText text="性能最优" delay={500} />
            </motion.div>
          </div>

          <h1 className="text-6xl font-display font-black mt-4 uppercase tracking-tighter drop-shadow-lg leading-[0.95]">
            <SplitWords text="智能数据" className="text-aurora" delay={0.1} />
            <br />
            <SplitWords text="分析中心" className="text-aurora" delay={0.35} />
          </h1>

          <motion.p
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7, duration: 0.6 }}
            className="text-slate-400 font-mono text-sm max-w-xl leading-relaxed"
          >
            实时数据可视化分析平台。支持股票、能源、新闻、电商等多维度数据分析与深度挖掘。
          </motion.p>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-5 mt-4">
          {displayStats.map((stat, i) => (
            <motion.div
              key={stat.name}
              initial={{ opacity: 0, y: 30, filter: 'blur(8px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              transition={{ duration: 0.6, delay: 0.6 + i * 0.08, ease: [0.16, 1, 0.3, 1] }}
              whileHover={{ y: -4, transition: { duration: 0.2 } }}
              className="glass-panel p-6 group cursor-default relative overflow-hidden"
            >
              <div className="absolute inset-0 bg-gradient-to-br from-cyber-cyan/0 to-cyber-cyan/0 group-hover:from-cyber-cyan/10 group-hover:to-cyber-purple/10 transition-all duration-500" />
              <div className="absolute -top-20 -right-20 w-40 h-40 bg-cyber-cyan/10 blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              <div className="relative">
                <div className="flex items-center justify-between mb-4">
                  <span className="font-display font-bold text-[10px] tracking-widest text-slate-400 uppercase">
                    {stat.name}
                  </span>
                  <stat.icon size={16} className={cn('opacity-70 group-hover:opacity-100 transition-opacity', stat.color)} />
                </div>
                <div className={cn('text-3xl font-display font-bold tracking-tight font-mono', stat.color)}>
                  {stat.val}
                </div>
                <div className="mt-3 h-0.5 w-0 group-hover:w-full bg-gradient-to-r from-cyber-cyan to-cyber-purple transition-all duration-500" />
              </div>
            </motion.div>
          ))}
        </div>

        <div className="mt-auto grid grid-cols-1 md:grid-cols-2 gap-6 w-full max-w-3xl">
          <motion.button
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.1 }}
            whileHover={{ scale: 1.02, x: 4 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onNavigate?.('visualizer')}
            className="glass-panel p-4 flex items-center justify-between group hover:border-cyber-cyan/60 transition-all bg-slate-950/60 hud-corner relative"
          >
            <div className="flex items-center gap-4">
              <div className="w-11 h-11 rounded bg-cyber-cyan/10 border border-cyber-cyan/40 flex items-center justify-center group-hover:bg-cyber-cyan/20 transition-colors">
                <Radar className="text-cyber-cyan" size={18} />
              </div>
              <div className="flex flex-col text-left">
                <span className="font-display font-bold text-sm text-slate-200 group-hover:text-cyber-cyan transition-colors">
                  数据可视化
                </span>
                <span className="font-mono text-[9px] text-slate-500 uppercase tracking-widest">
                  图表与可视化分析
                </span>
              </div>
            </div>
            <ArrowRight className="text-cyber-cyan group-hover:translate-x-1 transition-transform" size={16} />
          </motion.button>

          <motion.button
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.2 }}
            whileHover={{ scale: 1.02, x: 4 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onNavigate?.('deep-mining')}
            className="glass-panel p-4 flex items-center justify-between group hover:border-cyber-purple/60 transition-all bg-slate-950/60 hud-corner relative"
          >
            <div className="flex items-center gap-4">
              <div className="w-11 h-11 rounded bg-cyber-purple/10 border border-cyber-purple/40 flex items-center justify-center group-hover:bg-cyber-purple/20 transition-colors">
                <Box className="text-cyber-purple-bright" size={18} />
              </div>
              <div className="flex flex-col text-left">
                <span className="font-display font-bold text-sm text-slate-200 group-hover:text-cyber-purple-bright transition-colors">
                  深度挖掘
                </span>
                <span className="font-mono text-[9px] text-slate-500 uppercase tracking-widest">
                  关联规则与异常检测
                </span>
              </div>
            </div>
            <ArrowRight className="text-cyber-purple-bright group-hover:translate-x-1 transition-transform" size={16} />
          </motion.button>
        </div>
      </motion.div>
    </div>
  );
}