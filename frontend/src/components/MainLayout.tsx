import { useState, useEffect } from 'react'
import { Layout, Menu, Button, Tooltip, Badge } from 'antd'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  DashboardOutlined,
  DatabaseOutlined,
  CloudDownloadOutlined,
  BarChartOutlined,
  RobotOutlined,
  ExperimentOutlined,
  FileTextOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  SearchOutlined,
  BellOutlined,
  SettingOutlined,
  UserOutlined,
  CodeOutlined,
  HeartOutlined,
} from '@ant-design/icons'
import ParticleNetwork from './ParticleNetwork'

const { Header, Sider, Content } = Layout

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '仪表盘' },
  { key: '/data', icon: <DatabaseOutlined />, label: '数据源' },
  { key: '/crawl', icon: <CloudDownloadOutlined />, label: '爬虫管理' },
  { key: '/analysis', icon: <BarChartOutlined />, label: '数据分析' },
  { key: '/ml', icon: <RobotOutlined />, label: '机器学习' },
  { key: '/dl', icon: <ExperimentOutlined />, label: '深度学习' },
  { key: '/mining', icon: <ExperimentOutlined />, label: '数据挖掘' },
  { key: '/reports', icon: <FileTextOutlined />, label: '报告中心' },
]

// 页面标题映射
const pageTitles: Record<string, string> = {
  '/': '仪表盘',
  '/data': '数据源管理',
  '/crawl': '爬虫管理',
  '/analysis': '数据分析',
  '/ml': '机器学习',
  '/dl': '深度学习',
  '/mining': '数据挖掘',
  '/reports': '报告中心',
}

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const [time, setTime] = useState(new Date())
  const navigate = useNavigate()
  const location = useLocation()

  const pageTitle = pageTitles[location.pathname] || '智能数据分析平台'

  // 实时时钟 - 北京时间 (UTC+8)
  useEffect(() => {
    const updateTime = () => {
      const now = new Date()
      const beijingTime = new Date(now.getTime() + (8 * 60 * 60 * 1000) - now.getTimezoneOffset() * 60 * 1000)
      setTime(beijingTime)
    }
    updateTime()
    const timer = setInterval(updateTime, 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <Layout style={{ minHeight: '100vh', overflow: 'hidden' }}>
      {/* 粒子网络背景 */}
      <ParticleNetwork />

      {/* 网格背景 */}
      <div
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 0,
          background: `linear-gradient(to right, rgba(132, 148, 149, 0.08) 1px, transparent 1px),
                       linear-gradient(to bottom, rgba(132, 148, 149, 0.08) 1px, transparent 1px)`,
          backgroundSize: '24px 24px',
          pointerEvents: 'none',
        }}
      />

      {/* 径向渐变 */}
      <div
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 0,
          background: 'radial-gradient(ellipse at center, rgba(0, 219, 231, 0.03) 0%, rgba(13, 19, 33, 1) 70%)',
          pointerEvents: 'none',
        }}
      />

      {/* 侧边栏 */}
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        width={260}
        collapsedWidth={72}
        style={{
          background: 'rgba(15, 23, 42, 0.8)',
          backdropFilter: 'blur(16px)',
          borderRight: '1px solid rgba(148, 163, 184, 0.1)',
          position: 'fixed',
          height: '100vh',
          left: 0,
          top: 0,
          zIndex: 40,
        }}
      >
        {/* Logo 区域 */}
        <div
          style={{
            height: 64,
            padding: collapsed ? '0' : '0 24px',
            borderBottom: '1px solid rgba(148, 163, 184, 0.1)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
          }}
        >
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 4,
              background: 'linear-gradient(135deg, #00dbe7 0%, #7701d0 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#080e1c',
              fontWeight: 'bold',
              fontSize: 12,
              flexShrink: 0,
              boxShadow: '0 0 15px rgba(0, 219, 231, 0.5)',
            }}
          >
            AI
          </div>
          {!collapsed && (
            <div style={{ marginLeft: 12 }}>
              <div
                style={{
                  color: '#00dbe7',
                  fontWeight: 700,
                  fontSize: 16,
                  fontFamily: "'Space Grotesk', sans-serif",
                  letterSpacing: '0.05em',
                  textShadow: '0 0 8px rgba(0, 219, 231, 0.4)',
                }}
              >
                智能数据分析平台
              </div>
              <div
                style={{
                  color: '#64748b',
                  fontSize: 9,
                  fontFamily: "'JetBrains Mono', monospace",
                  letterSpacing: '0.1em',
                }}
              >
                v2.0 内核
              </div>
            </div>
          )}
        </div>

        {/* 新建分析按钮 */}
        {!collapsed && (
          <div style={{ padding: '16px 20px' }}>
            <Button
              type="primary"
              icon={<CodeOutlined />}
              style={{
                width: '100%',
                height: 40,
                background: 'rgba(0, 219, 231, 0.1)',
                border: '1px solid rgba(0, 219, 231, 0.5)',
                color: '#00dbe7',
                borderRadius: 0,
                fontFamily: "'Space Grotesk', sans-serif",
                fontWeight: 600,
                fontSize: 10,
                letterSpacing: '0.1em',
              }}
            >
              新建分析
            </Button>
          </div>
        )}

        {/* 菜单 */}
        <div style={{ padding: '8px 0', overflowY: 'auto', height: 'calc(100vh - 200px)' }}>
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            style={{
              background: 'transparent',
              border: 'none',
            }}
          />
        </div>

        {/* 底部系统选项 */}
        <div
          style={{
            position: 'absolute',
            bottom: 0,
            width: '100%',
            borderTop: '1px solid rgba(148, 163, 184, 0.1)',
            padding: '8px 0',
          }}
        >
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[]}
            items={[
              { key: 'terminal', icon: <CodeOutlined />, label: '终端' },
              { key: 'status', icon: <HeartOutlined />, label: '状态' },
            ]}
            style={{ background: 'transparent', border: 'none' }}
          />
        </div>
      </Sider>

      {/* 主内容区 */}
      <Layout
        style={{
          marginLeft: collapsed ? 72 : 260,
          transition: 'margin-left 0.3s ease',
          position: 'relative',
          zIndex: 10,
        }}
      >
        {/* 顶部导航 */}
        <Header
          style={{
            background: 'rgba(15, 23, 42, 0.6)',
            backdropFilter: 'blur(16px)',
            borderBottom: '1px solid rgba(148, 163, 184, 0.1)',
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            position: 'sticky',
            top: 0,
            zIndex: 30,
            height: 64,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
            {/* 标题 */}
            <div
              style={{
                color: '#00dbe7',
                fontFamily: "'Space Grotesk', sans-serif",
                fontWeight: 700,
                fontSize: 18,
                letterSpacing: '0.05em',
                textShadow: '0 0 10px rgba(0, 219, 231, 0.6)',
              }}
            >
              {pageTitle}
            </div>

            {/* 实时时钟 */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '4px 12px',
                background: 'rgba(0, 219, 231, 0.05)',
                border: '1px solid rgba(0, 219, 231, 0.2)',
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 10,
                color: '#00dbe7',
              }}
            >
              <HeartOutlined style={{ fontSize: 10, opacity: 0.7 }} />
              <span>{time.toLocaleString('zh-CN', { hour12: false })} 北京时间</span>
            </div>
          </div>

          {/* 右侧工具栏 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            {/* 搜索框 */}
            <div style={{ position: 'relative' }}>
              <SearchOutlined
                style={{
                  position: 'absolute',
                  left: 12,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: '#64748b',
                  fontSize: 12,
                }}
              />
              <input
                placeholder="搜索..."
                style={{
                  width: 200,
                  height: 32,
                  padding: '0 12px 0 36px',
                  background: 'rgba(15, 23, 42, 0.5)',
                  border: 'none',
                  borderBottom: '1px solid #334155',
                  color: '#f1f5f9',
                  fontFamily: "'JetBrains Mono', monospace",
                  fontSize: 10,
                  outline: 'none',
                }}
              />
            </div>

            {/* 通知 */}
            <Tooltip title="通知">
              <Badge count={3} size="small" style={{ backgroundColor: '#7701d0' }}>
                <Button
                  type="text"
                  icon={<BellOutlined />}
                  style={{ color: '#64748b', fontSize: 16 }}
                />
              </Badge>
            </Tooltip>

            {/* 设置 */}
            <Tooltip title="设置">
              <Button
                type="text"
                icon={<SettingOutlined />}
                style={{ color: '#64748b', fontSize: 16 }}
              />
            </Tooltip>

            {/* 用户头像 */}
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: '50%',
                border: '1px solid rgba(0, 219, 231, 0.4)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                background: 'linear-gradient(135deg, rgba(0, 219, 231, 0.2) 0%, rgba(119, 1, 208, 0.2) 100%)',
              }}
            >
              <UserOutlined style={{ color: '#00dbe7', fontSize: 14 }} />
            </div>
          </div>
        </Header>

        {/* 内容区域 */}
        <Content
          style={{
            margin: 0,
            padding: 24,
            minHeight: 'calc(100vh - 64px - 40px)',
            overflow: 'auto',
          }}
        >
          <Outlet />
        </Content>

        {/* 底部滚动信息条 */}
        <div
          style={{
            height: 40,
            background: 'rgba(15, 23, 42, 0.9)',
            backdropFilter: 'blur(16px)',
            borderTop: '1px solid rgba(148, 163, 184, 0.1)',
            display: 'flex',
            alignItems: 'center',
            padding: '0 16px',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              color: '#00dbe7',
              borderRight: '1px solid rgba(148, 163, 184, 0.2)',
              paddingRight: 16,
              marginRight: 16,
              flexShrink: 0,
            }}
          >
            <HeartOutlined style={{ fontSize: 12 }} />
            <span
              style={{
                fontFamily: "'Space Grotesk', sans-serif",
                fontWeight: 600,
                fontSize: 9,
                letterSpacing: '0.15em',
              }}
            >
              实时数据流
            </span>
          </div>

          <div
            style={{
              flex: 1,
              overflow: 'hidden',
              whiteSpace: 'nowrap',
            }}
          >
            <div
              style={{
                display: 'inline-block',
                animation: 'marquee 30s linear infinite',
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 10,
                color: '#94a3b8',
                letterSpacing: '0.05em',
              }}
            >
              <span style={{ color: '#00dbe7', marginRight: 24 }}>[系统]</span> 与 Node-Alpha 握手成功。
              <span style={{ marginLeft: 40 }} />
              <span style={{ color: '#7701d0', marginRight: 24 }}>[网络]</span> 通过 proxy-7 重新路由数据包...
              <span style={{ marginLeft: 40 }} />
              <span style={{ color: '#2ae500', marginRight: 24 }}>[成功]</span> 加密密钥验证通过，隧道安全。
              <span style={{ marginLeft: 40 }} />
              <span style={{ color: '#00dbe7', marginRight: 24 }}>0x8F2A</span>: 数据包注入成功。
              <span style={{ marginLeft: 40 }} />
              <span style={{ color: '#ffb4ab', marginRight: 24 }}>[警告]</span> 链路 90-B 检测到延迟峰值。
            </div>
          </div>
        </div>
      </Layout>

      {/* Marquee 动画样式 */}
      <style>{`
        @keyframes marquee {
          0% { transform: translateX(100%); }
          100% { transform: translateX(-100%); }
        }
      `}</style>
    </Layout>
  )
}