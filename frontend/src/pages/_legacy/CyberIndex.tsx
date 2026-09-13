import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutGrid, Layers, Database, BrainCircuit, Microscope, FileText,
  Terminal, Activity, Plus, Search, Bell, Settings, User, Download, TrendingUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import ParticleNetwork from '@/components/ParticleNetwork';
import DashboardView from '@/components/cyber/DashboardView';
import VisualizerView from '@/components/cyber/VisualizerView';
import DataNodesView from '@/components/cyber/DataNodesView';
import DeepMiningView from '@/components/cyber/DeepMiningView';
import CrawlerView from '@/components/cyber/CrawlerView';
import IntelligenceView from '@/components/cyber/IntelligenceView';
import ReportsView from '@/components/cyber/ReportsView';
import StockAnalysisView from '@/components/cyber/StockAnalysisView';

type ViewType = 'dashboard' | 'crawler' | 'stock-analysis' | 'visualizer' | 'data-nodes' | 'intelligence' | 'deep-mining' | 'reports';

// 本地 API 数据类型
interface StatsData {
  totalData: number;
  stockCount: number;
  energyCount: number;
  newsCount: number;
  ecomCount: number;
}

const CyberIndex = () => {
  const [activeView, setActiveView] = useState<ViewType>('dashboard');
  const [time, setTime] = useState(new Date());
  const [stats, setStats] = useState<StatsData>({
    totalData: 0,
    stockCount: 0,
    energyCount: 0,
    newsCount: 0,
    ecomCount: 0,
  });

  // 获取数据库统计
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch('/api/v1/analysis/overview');
        const data = await res.json();
        setStats({
          totalData: data.total_records || 0,
          stockCount: data.stock_records || 0,
          energyCount: data.energy_records || 0,
          newsCount: data.news_records || 0,
          ecomCount: data.ecom_products || 0,
        });
      } catch (e) {
        console.error('Failed to fetch stats:', e);
      }
    };
    fetchStats();
  }, []);

  // 时钟更新
  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // 页面标题
  useEffect(() => {
    document.title = '智能数据分析平台 - CYBER_OS';
  }, []);

  const navItems = [
    { id: 'dashboard', label: '仪表盘', icon: LayoutGrid },
    { id: 'crawler', label: '数据爬取', icon: Download },
    { id: 'stock-analysis', label: '股票分析', icon: TrendingUp },
    { id: 'visualizer', label: '可视化', icon: Layers },
    { id: 'data-nodes', label: '数据节点', icon: Database },
    { id: 'intelligence', label: '智能分析', icon: BrainCircuit },
    { id: 'deep-mining', label: '深度挖掘', icon: Microscope },
    { id: 'reports', label: '报告中心', icon: FileText },
  ] as const;

  // 格式化本地时间为北京时区
  const localTime = new Date(time.getTime() + 8 * 60 * 60 * 1000);
  const timeStr = localTime.toISOString().replace('T', ' ').substring(0, 19);

  const tickerItems = [
    { tag: 'SYS', color: 'text-cyber-cyan', text: `数据库连接正常 - ${stats.totalData} 条数据` },
    { tag: 'NET', color: 'text-cyber-purple-bright', text: `股票数据: ${stats.stockCount} 条` },
    { tag: 'OK', color: 'text-cyber-green', text: `能源数据: ${stats.energyCount} 条` },
    { tag: 'DATA', color: 'text-cyber-cyan', text: `新闻数据: ${stats.newsCount} 条` },
    { tag: 'ECOM', color: 'text-cyber-red', text: `电商数据: ${stats.ecomCount} 条` },
    { tag: 'TRX', color: 'text-cyber-cyan', text: '系统运行正常' },
  ];

  return (
    <div className="flex h-screen w-full bg-bg-deep text-slate-300 font-sans selection:bg-cyber-cyan/30 overflow-hidden">
      <ParticleNetwork />

      {/* Ambient backdrops */}
      <div className="fixed inset-0 z-0 grid-bg pointer-events-none" />
      <div className="fixed inset-0 z-0 bg-[radial-gradient(ellipse_at_center,hsl(184_100%_45%_/_0.04)_0%,hsl(var(--bg-deep))_70%)] pointer-events-none" />

      {/* SIDEBAR */}
      <motion.nav
        initial={{ x: -50, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="fixed left-0 top-0 h-full w-64 glass-panel rounded-none flex-col py-8 z-40 hidden lg:flex border-r border-cyan-500/15"
      >
        <div className="px-6 mb-10 flex flex-col gap-1">
          <h1 className="text-cyber-cyan font-display font-black tracking-widest text-2xl drop-shadow-[0_0_8px_hsl(var(--cyber-cyan)/0.5)]">
            CYBER_OS
          </h1>
          <span className="text-slate-500 font-mono text-[10px] tracking-widest uppercase">智能数据分析 v1.0</span>
        </div>

        <div className="px-5 mb-8">
          <motion.button
            whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}
            className="w-full py-3 bg-cyber-cyan/10 border border-cyber-cyan/50 text-cyber-cyan font-display font-bold text-xs tracking-widest hover:bg-cyber-cyan/20 transition-all rounded flex items-center justify-center gap-2 group relative overflow-hidden"
          >
            <span className="absolute inset-0 bg-gradient-to-r from-transparent via-cyber-cyan/30 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
            <Plus size={16} className="group-hover:rotate-90 transition-transform" />
            新建分析
          </motion.button>
        </div>

        <ul className="flex-1 flex flex-col gap-1 font-display font-bold tracking-tighter text-sm">
          {navItems.map(({ id, label, icon: Icon }) => (
            <li key={id}>
              <button
                onClick={() => setActiveView(id)}
                className={cn(
                  'w-full flex items-center gap-4 px-6 py-3 transition-all relative group',
                  activeView === id
                    ? 'text-cyber-cyan'
                    : 'text-slate-400 opacity-70 hover:opacity-100 hover:bg-cyber-cyan/5',
                )}
              >
                {activeView === id && (
                  <motion.div
                    layoutId="nav-indicator"
                    className="absolute inset-0 bg-cyber-cyan/10 border-r-2 border-cyber-cyan shadow-[0_0_20px_hsl(var(--cyber-cyan)/0.2)]"
                    transition={{ type: 'spring', stiffness: 350, damping: 30 }}
                  />
                )}
                <Icon size={18} className="relative z-10" />
                <span className="uppercase tracking-widest text-[11px] relative z-10">{label}</span>
              </button>
            </li>
          ))}
        </ul>

        <div className="mt-auto pt-6 border-t border-cyan-500/10 flex flex-col gap-1 font-display text-xs font-bold tracking-tighter">
          <button className="flex items-center gap-4 px-6 py-3 text-slate-400 opacity-70 hover:bg-cyan-500/5 hover:opacity-100 transition-all">
            <Terminal size={16} />
            <span className="uppercase tracking-widest text-[10px]">终端</span>
          </button>
          <button className="flex items-center gap-4 px-6 py-3 text-slate-400 opacity-70 hover:bg-cyan-500/5 hover:opacity-100 transition-all">
            <Activity size={16} />
            <span className="uppercase tracking-widest text-[10px]">系统状态</span>
          </button>
        </div>
      </motion.nav>

      {/* MAIN */}
      <main className="flex-1 lg:ml-64 flex flex-col h-full relative z-10">
        {/* HEADER */}
        <motion.header
          initial={{ y: -30, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ duration: 0.5, delay: 0.1 }}
          className="flex justify-between items-center w-full px-4 md:px-8 h-16 bg-slate-950/60 backdrop-blur-md border-b border-cyan-500/20 shadow-[0_4px_20px_rgba(0,0,0,0.5)] z-30 shrink-0"
        >
          <div className="flex items-center gap-6">
            <div className="text-xl font-display font-black text-cyber-cyan drop-shadow-[0_0_10px_hsl(var(--cyber-cyan)/0.6)] tracking-widest uppercase">
              NEURAL_CORE
            </div>
            <div className="hidden md:flex items-center gap-2 px-3 py-1 bg-cyber-cyan/5 border border-cyber-cyan/20 rounded font-mono text-[10px] text-cyber-cyan">
              <Activity size={12} className="animate-pulse opacity-70" />
              <span>{timeStr} CST</span>
            </div>
          </div>

          <div className="flex items-center gap-4 md:gap-6">
            <div className="relative group hidden md:block">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 group-hover:text-cyber-cyan transition-colors" size={14} />
              <input
                className="bg-slate-900/50 border-b border-slate-700 text-slate-300 pl-10 pr-4 py-1.5 text-[11px] font-mono tracking-widest focus:outline-none focus:border-cyber-cyan focus:bg-cyber-cyan/5 transition-all w-56 lg:w-64"
                placeholder="搜索数据..."
                type="text"
              />
            </div>

            <div className="flex items-center gap-2 border-l border-cyan-500/20 pl-4 md:pl-6">
              <button className="text-slate-500 hover:text-cyber-cyan hover:bg-cyber-cyan/5 p-2 rounded-full transition-all relative">
                <Bell size={18} />
                <span className="absolute top-2 right-2 w-2 h-2 bg-cyber-purple rounded-full shadow-[0_0_8px_hsl(var(--cyber-purple))] animate-pulse" />
              </button>
              <button className="text-slate-500 hover:text-cyber-cyan hover:bg-cyber-cyan/5 p-2 rounded-full transition-all">
                <Settings size={18} />
              </button>
              <div className="w-9 h-9 rounded-full border border-cyber-cyan/40 overflow-hidden ml-2 relative group cursor-pointer bg-cyber-cyan/10 flex items-center justify-center">
                <User className="text-cyber-cyan" size={18} />
              </div>
            </div>
          </div>
        </motion.header>

        {/* VIEW SWITCHER */}
        <div className="flex-1 relative overflow-hidden">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeView}
              initial={{ opacity: 0, y: 12, filter: 'blur(8px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              exit={{ opacity: 0, y: -8, filter: 'blur(4px)' }}
              transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
              className="h-full w-full overflow-y-auto"
            >
              {activeView === 'dashboard' && <DashboardView stats={stats} onNavigate={(v) => setActiveView(v as ViewType)} />}
              {activeView === 'crawler' && <CrawlerView />}
              {activeView === 'stock-analysis' && <StockAnalysisView />}
              {activeView === 'visualizer' && <VisualizerView stats={stats} />}
              {activeView === 'data-nodes' && <DataNodesView stats={stats} />}
              {activeView === 'intelligence' && <IntelligenceView />}
              {activeView === 'deep-mining' && <DeepMiningView />}
              {activeView === 'reports' && <ReportsView />}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* FOOTER TICKER */}
        <footer className="h-10 bg-slate-950/90 backdrop-blur-md border-t border-cyan-500/20 z-40 flex items-center px-6 overflow-hidden shrink-0">
          <div className="flex items-center gap-2 text-cyber-cyan border-r border-cyan-500/30 pr-4 shrink-0">
            <Activity size={14} className="animate-pulse" />
            <span className="font-display font-bold text-[10px] tracking-widest uppercase">实时数据</span>
          </div>
          <div className="flex-1 overflow-hidden relative">
            <div className="flex items-center whitespace-nowrap font-mono text-[10px] text-slate-400 tracking-wider animate-marquee">
              {[...tickerItems, ...tickerItems].map((it, i) => (
                <span key={i} className="px-6">
                  <span className={it.color}>[{it.tag}]</span> {it.text}
                </span>
              ))}
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
};

export default CyberIndex;