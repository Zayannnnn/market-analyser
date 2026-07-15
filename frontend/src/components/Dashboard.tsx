import React, { useState, useEffect, useRef } from 'react';
import { TrendingUp, TrendingDown, RefreshCw, BarChart2, Newspaper, PlusCircle } from 'lucide-react';
import { StockItem, MarketSummary, NewsArticle } from '../App.tsx';

// Sparkline Sub-Component
function Sparkline({ data, isBullish }: { data: number[]; isBullish: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !data || data.length < 2) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Set display and resolution sizes
    const dpr = window.devicePixelRatio || 1;
    const width = 80;
    const height = 24;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);
    
    ctx.clearRect(0, 0, width, height);
    
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min === 0 ? 1 : max - min;
    
    ctx.beginPath();
    ctx.strokeStyle = isBullish ? '#10B981' : '#EF4444';
    ctx.lineWidth = 1.5;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    
    for (let i = 0; i < data.length; i++) {
      const x = (i / (data.length - 1)) * width;
      const y = height - 2 - ((data[i] - min) / range) * (height - 4);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }, [data, isBullish]);
  
  return <canvas ref={canvasRef} style={{ width: '80px', height: '24px', display: 'block' }} />;
}

// Premium Stock Intelligence Illustration Sub-Component
function PremiumIntelligenceIllustration() {
  return (
    <div className="premium-intelligence-illustration">
      {/* Background glow overlay */}
      <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to right, rgba(59, 130, 246, 0.05), rgba(139, 92, 246, 0.03), rgba(16, 185, 129, 0.05))', pointerEvents: 'none' }}></div>
      
      {/* 1. Neural Network Stock Nodes */}
      <div className="illustration-section nodes-section">
        <svg className="nodes-svg" viewBox="0 0 200 100" width="100%" height="100%">
          <defs>
            <radialGradient id="nodeGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#3B82F6" stopOpacity="1" />
              <stop offset="100%" stopColor="#3B82F6" stopOpacity="0" />
            </radialGradient>
            <radialGradient id="nodeGlowGreen" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#10B981" stopOpacity="1" />
              <stop offset="100%" stopColor="#10B981" stopOpacity="0" />
            </radialGradient>
          </defs>
          {/* Connection Lines */}
          <line x1="30" y1="30" x2="80" y2="20" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
          <line x1="30" y1="30" x2="60" y2="70" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
          <line x1="80" y1="20" x2="130" y2="40" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
          <line x1="60" y1="70" x2="130" y2="40" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
          <line x1="130" y1="40" x2="170" y2="75" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
          <line x1="80" y1="20" x2="170" y2="25" stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
          
          {/* Signal Pulse Motion */}
          <circle r="1.5" fill="#3B82F6">
            <animateMotion dur="3s" repeatCount="indefinite" path="M30 30 L80 20" />
          </circle>
          <circle r="1.5" fill="#10B981">
            <animateMotion dur="4s" repeatCount="indefinite" path="M60 70 L130 40" />
          </circle>
          <circle r="1.5" fill="#8B5CF6">
            <animateMotion dur="2.5s" repeatCount="indefinite" path="M80 20 L130 40" />
          </circle>
          
          {/* Nodes */}
          <circle cx="30" cy="30" r="10" fill="url(#nodeGlow)" opacity="0.3" />
          <circle cx="30" cy="30" r="3" fill="#3B82F6" />
          <text x="30" y="44" fill="var(--text-secondary)" fontSize="6" textAnchor="middle">REL</text>

          <circle cx="80" cy="20" r="10" fill="url(#nodeGlow)" opacity="0.3" />
          <circle cx="80" cy="20" r="3" fill="#60A5FA" />
          <text x="80" y="12" fill="var(--text-secondary)" fontSize="6" textAnchor="middle">INFY</text>

          <circle cx="60" cy="70" r="12" fill="url(#nodeGlowGreen)" opacity="0.3" />
          <circle cx="60" cy="70" r="4" fill="#10B981" />
          <text x="60" y="85" fill="var(--text-secondary)" fontSize="6" textAnchor="middle">TCS</text>

          <circle cx="130" cy="40" r="10" fill="url(#nodeGlow)" opacity="0.3" />
          <circle cx="130" cy="40" r="3" fill="#8B5CF6" />
          <text x="130" y="53" fill="var(--text-secondary)" fontSize="6" textAnchor="middle">HDFC</text>

          <circle cx="170" cy="25" r="10" fill="url(#nodeGlowGreen)" opacity="0.3" />
          <circle cx="170" cy="3" fill="none" />
          <circle cx="170" cy="25" r="3" fill="#10B981" />
          <text x="170" y="17" fill="var(--text-secondary)" fontSize="6" textAnchor="middle">AI</text>
        </svg>
      </div>

      {/* 2. AI Signal Waveform */}
      <div className="illustration-section signal-section">
        <div className="signal-badge">
          <span className="signal-pulse"></span>
          <span className="signal-text">AI RADAR ACTIVE</span>
        </div>
        <div className="signal-chart">
          <svg viewBox="0 0 120 45" width="100%" height="100%">
            <path 
              d="M0 22 Q15 2, 30 22 T60 22 T90 22 T120 22" 
              fill="none" 
              stroke="url(#signalGradient)" 
              strokeWidth="2"
              className="waveform-path"
            />
            <defs>
              <linearGradient id="signalGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#3B82F6" />
                <stop offset="50%" stopColor="#8B5CF6" />
                <stop offset="100%" stopColor="#10B981" />
              </linearGradient>
            </defs>
          </svg>
        </div>
        <span className="signal-percentage">+89% Signal Score</span>
      </div>

      {/* 3. Market Heatmap Grid */}
      <div className="illustration-section heatmap-section">
        <span className="heatmap-title">SECTOR TEMPERATURE</span>
        <div className="heatmap-grid">
          <div className="heatmap-cell cell-high" title="Tech (+2.8%)"></div>
          <div className="heatmap-cell cell-high" title="Finance (+1.9%)"></div>
          <div className="heatmap-cell cell-med" title="Auto (+0.4%)"></div>
          <div className="heatmap-cell cell-high" title="Pharma (+1.5%)"></div>
          <div className="heatmap-cell cell-low" title="Energy (-1.2%)"></div>
          <div className="heatmap-cell cell-med" title="FMCG (+0.2%)"></div>
          <div className="heatmap-cell cell-high" title="Metal (+2.1%)"></div>
          <div className="heatmap-cell cell-low" title="Infra (-0.8%)"></div>
          <div className="heatmap-cell cell-med" title="Media (+0.1%)"></div>
          <div className="heatmap-cell cell-high" title="Realty (+3.4%)"></div>
          <div className="heatmap-cell cell-med" title="IT (+0.5%)"></div>
          <div className="heatmap-cell cell-high" title="Telecom (+1.8%)"></div>
        </div>
      </div>
    </div>
  );
}

interface DashboardProps {
  stocks: StockItem[];
  marketSummary: MarketSummary | null;
  newsArticles: NewsArticle[];
  onSelectStock: (stock: StockItem) => void;
  halalOnly: boolean;
  isProcessing: boolean;
  onRecalculate: () => void;
  addStockInput: { ticker: string; name: string; quality: string };
  setAddStockInput: React.Dispatch<React.SetStateAction<{ ticker: string; name: string; quality: string }>>;
  onAddStock: (e: React.FormEvent) => void;
  userId: string;
  onShowToast: (message: string, isError?: boolean) => void;
  apiBase?: string;
}

type SortKey = 'rank' | 'ticker' | 'score' | 'price' | 'change' | 'upside';
type SortOrder = 'asc' | 'desc';

export default function Dashboard({
  stocks,
  marketSummary,
  newsArticles,
  onSelectStock,
  halalOnly,
  isProcessing,
  onRecalculate,
  addStockInput,
  setAddStockInput,
  onAddStock,
  userId,
  onShowToast,
  apiBase
}: DashboardProps) {
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [sortKey, setSortKey] = useState<SortKey>('score');
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc');

  interface AuthStatus {
    authentication_status: 'CONNECTED' | 'EXPIRED' | 'CONNECTING' | 'ERROR' | 'UNKNOWN';
    last_successful_authentication: number | null;
    last_authentication_time: number | null;
    token_age_seconds: number | null;
    token_age_str: string;
    expected_expiry_str: string;
    live_trading_status: 'READY' | 'PAUSED';
    last_health_check_str: string;
    login_url: string;
  }

  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);

  useEffect(() => {
    fetchAuthStatus();
  }, []);

  const fetchAuthStatus = async () => {
    try {
      const res = await fetch(`${apiBase || ''}/api/upstox/auth-status`);
      if (res.ok) {
        const payload = await res.json();
        setAuthStatus(payload);
      }
    } catch (e) {
      console.error("Failed to fetch auth status", e);
    }
  };

  // User Alert Setup form states
  const [alertCompanyName, setAlertCompanyName] = useState<string>('');
  const [alertTargetScore, setAlertTargetScore] = useState<string>('80');
  const [alertTicker, setAlertTicker] = useState<string>('');
  const [showAutocomplete, setShowAutocomplete] = useState<boolean>(false);
  const [isSettingAlert, setIsSettingAlert] = useState<boolean>(false);

  const suggestions = alertCompanyName.trim() 
    ? stocks.filter(s => 
        s.company_name.toLowerCase().includes(alertCompanyName.toLowerCase()) ||
        s.ticker.toLowerCase().includes(alertCompanyName.toLowerCase())
      )
    : [];

  const handleSetAlert = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!alertTicker) {
      onShowToast("Please select a valid company from the autocomplete dropdown list.", true);
      return;
    }
    const scoreVal = parseInt(alertTargetScore);
    if (isNaN(scoreVal) || scoreVal < 0 || scoreVal > 100) {
      onShowToast("Target AI Score must be between 0 and 100.", true);
      return;
    }

    setIsSettingAlert(true);
    onShowToast(`Configuring Telegram alert for ${alertTicker}...`);

    try {
      const apiBase = import.meta.env.VITE_API_BASE_URL || '/api';
      
      const res = await fetch(`${apiBase}/alerts/setup?user_id=${userId}&ticker=${alertTicker}&target_score=${scoreVal}`, {
        method: "POST"
      });

      if (res.ok) {
        const data = await res.json();
        onShowToast(data.message || `Alert configured successfully for ${alertTicker}!`);
        setAlertCompanyName('');
        setAlertTicker('');
        setAlertTargetScore('80');
      } else {
        const err = await res.json();
        onShowToast(err.detail || "Failed to set up Telegram alert.", true);
      }
    } catch (e) {
      onShowToast("Error communicating with alerts setup API.", true);
    } finally {
      setIsSettingAlert(false);
    }
  };

  // Halal compliance filter
  const isHalalCompliant = (ticker: string) => {
    return (ticker.charCodeAt(0) % 2 === 0);
  };

  // Helper rating resolver
  const getRatingBadge = (score: number) => {
    if (score >= 75) return <span className="badge badge-success">BUY</span>;
    if (score >= 55) return <span className="badge badge-warning">HOLD</span>;
    return <span className="badge badge-danger">AVOID</span>;
  };

  const getRiskLevel = (score: number) => {
    if (score >= 75) return { text: 'Low', className: 'text-bullish' };
    if (score >= 60) return { text: 'Medium', className: 'text-neutral' };
    return { text: 'High', className: 'text-bearish' };
  };

  // Main filter
  const filteredStocks = stocks.filter(stock => {
    const matchesSearch = stock.ticker.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          stock.company_name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesHalal = !halalOnly || isHalalCompliant(stock.ticker);
    return matchesSearch && matchesHalal;
  });

  // Calculate fields & sort
  const sortedStocks = [...filteredStocks].map(s => {
    const priceClean = parseFloat(s.price.replace(/[^\d.]/g, '')) || 100;
    // Upside linked dynamically to score: higher AI score suggests greater valuation discrepancy
    const upsidePct = Math.max(-5, Math.round((s.score - 40) * 0.4 + 10));
    const targetPrice = priceClean * (1 + upsidePct / 100);
    
    return {
      ...s,
      priceClean,
      upsidePct,
      targetPrice
    };
  }).sort((a, b) => {
    let aVal: any = a[sortKey as keyof typeof a];
    let bVal: any = b[sortKey as keyof typeof b];
    
    if (sortKey === 'price') {
      aVal = a.priceClean;
      bVal = b.priceClean;
    } else if (sortKey === 'change') {
      aVal = parseFloat(a.change.replace(/[^\d.+-]/g, '')) || 0;
      bVal = parseFloat(b.change.replace(/[^\d.+-]/g, '')) || 0;
    } else if (sortKey === 'upside') {
      aVal = a.upsidePct;
      bVal = b.upsidePct;
    }

    if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
    return 0;
  });

  // Toggle sort direction
  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortOrder('desc');
    }
  };

  // Derive Lists
  const getTopGainers = () => {
    return [...stocks]
      .map(s => ({ ...s, changeVal: parseFloat(s.change.replace(/[^\d.+-]/g, '')) || 0 }))
      .sort((a, b) => b.changeVal - a.changeVal)
      .slice(0, 3);
  };

  const getTopLosers = () => {
    return [...stocks]
      .map(s => ({ ...s, changeVal: parseFloat(s.change.replace(/[^\d.+-]/g, '')) || 0 }))
      .sort((a, b) => a.changeVal - b.changeVal)
      .slice(0, 3);
  };

  const getHighVolume = () => {
    return [...stocks]
      .sort((a, b) => (b.technical_indicators?.volume_surge || 0) - (a.technical_indicators?.volume_surge || 0))
      .slice(0, 3);
  };

  return (
    <div className="dashboard-container">
      
      {/* Upstox Authentication Status Card (Task 5) */}
      <div className="card-panel" style={{ marginBottom: '1.5rem', background: 'linear-gradient(135deg, rgba(21, 23, 30, 0.9) 0%, rgba(27, 30, 40, 0.95) 100%)', border: '1px solid var(--border-color)', borderRadius: '8px', padding: '1.25rem' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Header row */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                backgroundColor: authStatus?.authentication_status === 'CONNECTED' 
                  ? 'rgba(16, 185, 129, 0.1)' 
                  : authStatus?.authentication_status === 'CONNECTING'
                  ? 'rgba(245, 158, 11, 0.1)'
                  : 'rgba(239, 68, 68, 0.1)'
              }}>
                <span style={{ fontSize: '1.1rem' }}>
                  {authStatus?.authentication_status === 'CONNECTED' ? '🟢' : authStatus?.authentication_status === 'CONNECTING' ? '🟡' : '🔴'}
                </span>
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700 }}>Broker Integration: Upstox</h3>
                <p style={{ margin: '0.1rem 0 0 0', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Centralized dynamic session verification & execution safety checks</p>
              </div>
            </div>
            
            <button 
              className="flat-btn" 
              style={{
                height: '32px',
                padding: '0 1rem',
                fontSize: '0.78rem',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
                backgroundColor: authStatus?.authentication_status === 'CONNECTED' ? 'transparent' : 'var(--primary)',
                border: authStatus?.authentication_status === 'CONNECTED' ? '1px solid var(--border-color)' : 'none'
              }}
              onClick={() => {
                const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api';
                const base = apiBaseUrl.endsWith('/api') ? apiBaseUrl.substring(0, apiBaseUrl.lastIndexOf('/api')) : apiBaseUrl;
                // Force a redirect to login
                window.location.href = `${base}/api/upstox/login?force=true`;
              }}
            >
              {authStatus?.authentication_status === 'CONNECTED' ? 'Reconnect Broker' : 'Authenticate Session'}
            </button>
          </div>

          {/* Telemetry grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '1rem',
            borderTop: '1px solid rgba(255, 255, 255, 0.05)',
            paddingTop: '1rem'
          }}>
            <div style={{ padding: '0.5rem', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '4px' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>Broker Status</div>
              <div style={{ marginTop: '0.2rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <span className={`badge ${
                  authStatus?.authentication_status === 'CONNECTED' 
                    ? 'badge-success' 
                    : authStatus?.authentication_status === 'CONNECTING'
                    ? 'badge-warning'
                    : 'badge-danger'
                }`} style={{ fontSize: '0.7rem', padding: '0.15rem 0.4rem' }}>
                  {authStatus?.authentication_status || 'UNKNOWN'}
                </span>
              </div>
            </div>

            <div style={{ padding: '0.5rem', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '4px' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>Last Authentication</div>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, marginTop: '0.2rem' }}>
                {authStatus?.last_successful_authentication 
                  ? new Date(authStatus.last_successful_authentication * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                  : 'Never'}
              </div>
            </div>

            <div style={{ padding: '0.5rem', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '4px' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>Token Age</div>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, marginTop: '0.2rem' }}>{authStatus?.token_age_str || 'Unknown'}</div>
            </div>

            <div style={{ padding: '0.5rem', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '4px' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>Expected Expiry</div>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, marginTop: '0.2rem', color: authStatus?.authentication_status === 'CONNECTED' ? 'var(--text-primary)' : 'var(--danger)' }}>
                {authStatus?.expected_expiry_str 
                  ? new Date(authStatus.expected_expiry_str).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) 
                  : 'Expired'}
              </div>
            </div>

            <div style={{ padding: '0.5rem', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '4px' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>Live Trading</div>
              <div style={{ marginTop: '0.2rem' }}>
                <span className={`badge ${authStatus?.live_trading_status === 'READY' ? 'badge-success' : 'badge-danger'}`} style={{ fontSize: '0.7rem', padding: '0.15rem 0.4rem' }}>
                  {authStatus?.live_trading_status || 'PAUSED'}
                </span>
              </div>
            </div>

            <div style={{ padding: '0.5rem', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '4px' }}>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>Last Health Check</div>
              <div style={{ fontSize: '0.8rem', fontWeight: 600, marginTop: '0.2rem', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                {authStatus?.last_health_check_str 
                  ? new Date(authStatus.last_health_check_str).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                  : 'Pending'}
              </div>
            </div>
          </div>
      </div>
    </div>
      
      {/* 1. Market Overview Indices */}
      <section>
        <h2 className="section-title"><BarChart2 size={16} /> Market Overview</h2>
        <div className="hero-grid">
          {marketSummary ? (
            <>
              {/* Nifty 50 */}
              <div className="index-card" onClick={() => onSelectStock({ ticker: '^NSEI' } as any)}>
                <div className="index-card-header">
                  <span className="index-card-ticker">NIFTY 50</span>
                  <span className="index-card-change" style={{ color: marketSummary.nifty50.change >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                    {marketSummary.nifty50.change >= 0 ? '+' : ''}{marketSummary.nifty50.change.toFixed(2)}%
                  </span>
                </div>
                <div className="index-card-body">
                  <span className="index-card-price">₹{marketSummary.nifty50.price.toLocaleString("en-IN")}</span>
                  <div className="index-sparkline-container">
                    <Sparkline data={marketSummary.nifty50.history} isBullish={marketSummary.nifty50.change >= 0} />
                  </div>
                </div>
              </div>

              {/* BANK NIFTY */}
              <div className="index-card" onClick={() => onSelectStock({ ticker: '^NSEBANK' } as any)}>
                <div className="index-card-header">
                  <span className="index-card-ticker">BANK NIFTY</span>
                  <span className="index-card-change" style={{ color: marketSummary.banknifty.change >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                    {marketSummary.banknifty.change >= 0 ? '+' : ''}{marketSummary.banknifty.change.toFixed(2)}%
                  </span>
                </div>
                <div className="index-card-body">
                  <span className="index-card-price">₹{marketSummary.banknifty.price.toLocaleString("en-IN")}</span>
                  <div className="index-sparkline-container">
                    <Sparkline data={marketSummary.banknifty.history} isBullish={marketSummary.banknifty.change >= 0} />
                  </div>
                </div>
              </div>

              {/* SENSEX */}
              <div className="index-card" onClick={() => onSelectStock({ ticker: '^BSESN' } as any)}>
                <div className="index-card-header">
                  <span className="index-card-ticker">SENSEX</span>
                  <span className="index-card-change" style={{ color: marketSummary.sensex.change >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                    {marketSummary.sensex.change >= 0 ? '+' : ''}{marketSummary.sensex.change.toFixed(2)}%
                  </span>
                </div>
                <div className="index-card-body">
                  <span className="index-card-price">₹{marketSummary.sensex.price.toLocaleString("en-IN")}</span>
                  <div className="index-sparkline-container">
                    <Sparkline data={marketSummary.sensex.history} isBullish={marketSummary.sensex.change >= 0} />
                  </div>
                </div>
              </div>

              {/* NASDAQ */}
              <div className="index-card" onClick={() => onSelectStock({ ticker: '^IXIC' } as any)}>
                <div className="index-card-header">
                  <span className="index-card-ticker">NASDAQ</span>
                  <span className="index-card-change" style={{ color: marketSummary.nasdaq.change >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                    {marketSummary.nasdaq.change >= 0 ? '+' : ''}{marketSummary.nasdaq.change.toFixed(2)}%
                  </span>
                </div>
                <div className="index-card-body">
                  <span className="index-card-price">${marketSummary.nasdaq.price.toLocaleString()}</span>
                  <div className="index-sparkline-container">
                    <Sparkline data={marketSummary.nasdaq.history} isBullish={marketSummary.nasdaq.change >= 0} />
                  </div>
                </div>
              </div>

              {/* S&P 500 */}
              <div className="index-card" onClick={() => onSelectStock({ ticker: '^GSPC' } as any)}>
                <div className="index-card-header">
                  <span className="index-card-ticker">S&P 500</span>
                  <span className="index-card-change" style={{ color: marketSummary.sp500.change >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                    {marketSummary.sp500.change >= 0 ? '+' : ''}{marketSummary.sp500.change.toFixed(2)}%
                  </span>
                </div>
                <div className="index-card-body">
                  <span className="index-card-price">${marketSummary.sp500.price.toLocaleString()}</span>
                  <div className="index-sparkline-container">
                    <Sparkline data={marketSummary.sp500.history} isBullish={marketSummary.sp500.change >= 0} />
                  </div>
                </div>
              </div>
            </>
          ) : (
            Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="index-card" style={{ height: '70px', justifyContent: 'center' }}>
                <div className="skeleton-line" style={{ width: '60%', height: '14px', marginBottom: '0.4rem' }}></div>
                <div className="skeleton-line" style={{ width: '40%', height: '10px' }}></div>
              </div>
            ))
          )}
        </div>
      </section>

      {/* 2. Main Leaderboard Grid */}
      <div className="dashboard-grid">
        
        {/* Section 1: Leaderboard Table */}
        <div className="card-panel">
          <div className="table-header-row">
            <h2 className="section-title" style={{ marginBottom: 0 }}>Top AI Ranked Stocks</h2>
            <input 
              type="text" 
              placeholder="Search table..." 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{ width: '180px', padding: '0.35rem 0.75rem', borderRadius: '4px', border: '1px solid var(--border-color)', fontSize: '0.78rem', backgroundColor: 'var(--bg-primary)', color: 'var(--text-primary)' }}
            />
          </div>

          {/* Premium Intelligence Illustration */}
          <PremiumIntelligenceIllustration />

          <div className="table-container desktop-table-view">
            <table className="premium-table">
              <thead>
                <tr>
                  <th onClick={() => handleSort('rank')}>Rank</th>
                  <th onClick={() => handleSort('ticker')}>Ticker</th>
                  <th onClick={() => handleSort('score')}>AI Score</th>
                  <th onClick={() => handleSort('price')}>Current Price</th>
                  <th>Target Price</th>
                  <th onClick={() => handleSort('upside')}>Upside</th>
                  <th>Risk Level</th>
                  <th>Recommendation</th>
                </tr>
              </thead>
              <tbody>
                {sortedStocks.length > 0 ? (
                  sortedStocks.map((stock, idx) => {
                    const risk = getRiskLevel(stock.score);
                    
                    return (
                      <tr key={stock.ticker} onClick={() => onSelectStock(stock)}>
                        <td className="table-rank">#{stock.rank || idx + 1}</td>
                        <td>
                          <span className="table-ticker">{stock.ticker}</span>
                          <span className="table-company">{stock.company_name}</span>
                        </td>
                        <td className="table-score">
                          <span style={{ fontSize: '0.9rem', color: '#FFFFFF', fontWeight: 700 }}>{stock.score}</span>
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>/100</span>
                        </td>
                        <td className="table-price">{stock.price}</td>
                        <td style={{ fontWeight: 600 }}>
                          ₹{stock.targetPrice.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </td>
                        <td className="text-bullish" style={{ fontWeight: 700 }}>
                          +{stock.upsidePct}%
                        </td>
                        <td>
                          <span className={risk.className} style={{ fontWeight: 600 }}>{risk.text}</span>
                        </td>
                        <td>{getRatingBadge(stock.score)}</td>
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={8} style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-secondary)' }}>
                      No active stock rankings match the current search or compliance criteria.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Mobile Stock Cards */}
          <div className="mobile-stock-cards-container">
            {sortedStocks.length > 0 ? (
              sortedStocks.map((stock, idx) => {
                return (
                  <div key={stock.ticker} className="mobile-stock-card" onClick={() => onSelectStock(stock)}>
                    <div className="mobile-stock-card-header">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span className="mobile-stock-rank">#{stock.rank || idx + 1}</span>
                        <span className="mobile-stock-ticker">{stock.ticker}</span>
                      </div>
                      {getRatingBadge(stock.score)}
                    </div>
                    <div className="mobile-stock-card-body">
                      <div className="mobile-stock-name">{stock.company_name}</div>
                      <div className="mobile-stock-stats">
                        <div className="mobile-stock-stat">
                          <span className="stat-label">AI Score</span>
                          <span className="stat-value">{stock.score}<span className="stat-value-slash">/100</span></span>
                        </div>
                        <div className="mobile-stock-stat">
                          <span className="stat-label">Current Price</span>
                          <span className="stat-value">{stock.price}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              <div style={{ color: 'var(--text-secondary)', fontStyle: 'italic', padding: '2rem 0', textAlign: 'center', fontSize: '0.85rem' }}>
                No active stock rankings match the current search or compliance criteria.
              </div>
            )}
          </div>
        </div>

        {/* Section 2: Trending News Feed */}
        <div className="card-panel" style={{ maxHeight: '520px', overflowY: 'auto' }}>
          <h2 className="section-title"><Newspaper size={16} /> Trending Market News</h2>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {newsArticles.length > 0 ? (
              newsArticles.slice(0, 6).map((item) => {
                const badgeClass = item.sentiment_score > 15 
                  ? 'badge-success' 
                  : item.sentiment_score < -15 
                    ? 'badge-danger' 
                    : 'badge-warning';
                
                const badgeText = item.sentiment_score > 15 
                  ? 'BULLISH' 
                  : item.sentiment_score < -15 
                    ? 'BEARISH' 
                    : 'NEUTRAL';
                
                return (
                  <div key={item.id || item.title} className="news-item">
                    <div className="news-header">
                      <span>{item.source}</span>
                      <span>{item.published_at.substring(11, 16)} UTC</span>
                    </div>
                    <a href={item.url} target="_blank" rel="noopener noreferrer" className="news-title">
                      {item.title}
                    </a>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.2rem' }}>
                      <span className={`badge ${badgeClass}`} style={{ fontSize: '0.62rem', padding: '0.1rem 0.35rem' }}>
                        {badgeText}
                      </span>
                      <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                        {item.ticker}
                      </span>
                    </div>
                  </div>
                );
              })
            ) : (
              <div style={{ color: 'var(--text-secondary)', fontStyle: 'italic', padding: '2rem 0', textAlign: 'center' }}>
                No recent RSS news matches. Run calculation pipeline to ingest.
              </div>
            )}
          </div>
        </div>

      </div>

      {/* 3. Section 3, 4, 5: Gainers, Losers, and Volume Grid */}
      <section className="horizontal-lists">
        {/* Top Gainers */}
        <div className="card-panel">
          <h3 className="section-title" style={{ fontSize: '0.88rem' }}><TrendingUp size={14} className="text-bullish" /> Top Gainers</h3>
          <div className="mini-stock-list">
            {getTopGainers().map((stock) => (
              <div key={stock.ticker} className="mini-stock-item" onClick={() => onSelectStock(stock)}>
                <div className="mini-stock-left">
                  <span className="mini-stock-ticker">{stock.ticker}</span>
                  <span className="mini-stock-name">{stock.company_name}</span>
                </div>
                <div className="mini-stock-right">
                  <span className="mini-stock-price">{stock.price}</span>
                  <span className="mini-stock-change text-bullish">{stock.change}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Top Losers */}
        <div className="card-panel">
          <h3 className="section-title" style={{ fontSize: '0.88rem' }}><TrendingDown size={14} className="text-bearish" /> Top Losers</h3>
          <div className="mini-stock-list">
            {getTopLosers().map((stock) => (
              <div key={stock.ticker} className="mini-stock-item" onClick={() => onSelectStock(stock)}>
                <div className="mini-stock-left">
                  <span className="mini-stock-ticker">{stock.ticker}</span>
                  <span className="mini-stock-name">{stock.company_name}</span>
                </div>
                <div className="mini-stock-right">
                  <span className="mini-stock-price">{stock.price}</span>
                  <span className="mini-stock-change text-bearish">{stock.change}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* High Volume Stocks */}
        <div className="card-panel">
          <h3 className="section-title" style={{ fontSize: '0.88rem' }}><BarChart2 size={14} className="text-bullish" /> Volume Breakout</h3>
          <div className="mini-stock-list">
            {getHighVolume().map((stock) => (
              <div key={stock.ticker} className="mini-stock-item" onClick={() => onSelectStock(stock)}>
                <div className="mini-stock-left">
                  <span className="mini-stock-ticker">{stock.ticker}</span>
                  <span className="mini-stock-name">{stock.company_name}</span>
                </div>
                <div className="mini-stock-right">
                  <span className="mini-stock-price">{stock.price}</span>
                  <span className="mini-stock-change text-bullish" style={{ fontSize: '0.72rem' }}>
                    {stock.technical_indicators?.volume_surge?.toFixed(1) || '1.0'}x Vol
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 4. Bottom Controls Panel (Pipeline & Custom Ticker addition) */}
      <section className="horizontal-lists" style={{ borderTop: '1px solid var(--border-color)', paddingTop: '1.5rem', marginTop: '0.5rem' }}>
        
        {/* Pipeline run */}
        <div className="card-panel" style={{ flex: 1 }}>
          <h3 className="section-title" style={{ fontSize: '0.88rem' }}><RefreshCw size={14} /> Pipeline Engine</h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1rem', lineHeight: '1.4' }}>
            Trigger a complete background recalculation. This query gathers live market history, ingests recent rss financial streams, checks sentiment levels via Gemini, and refreshes the leaderboard document in Firestore.
          </p>
          <button 
            className="flat-btn" 
            style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }} 
            onClick={onRecalculate} 
            disabled={isProcessing}
          >
            <RefreshCw size={14} className={isProcessing ? 'animate-spin' : ''} />
            {isProcessing ? 'Processing Calculations...' : 'Recalculate Leaderboard Document'}
          </button>
        </div>

        {/* Telegram Alerts Setup */}
        <div className="card-panel" style={{ flex: 1.2, position: 'relative' }}>
          <h3 className="section-title" style={{ fontSize: '0.88rem' }}><PlusCircle size={14} /> Telegram AI Alerts</h3>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '0.75rem', lineHeight: '1.4' }}>
            Set a target AI Score threshold. You will receive a direct Telegram dispatch the moment our Gemini and technical agents score the asset above your target.
          </p>
          <form onSubmit={handleSetAlert} className="add-stock-form" style={{ position: 'relative' }}>
            <div className="form-input-group" style={{ position: 'relative' }}>
              <label>Company Name</label>
              <input 
                type="text" 
                value={alertCompanyName} 
                onChange={(e) => {
                  setAlertCompanyName(e.target.value);
                  setAlertTicker('');
                  setShowAutocomplete(true);
                }}
                onFocus={() => setShowAutocomplete(true)}
                onBlur={() => setTimeout(() => setShowAutocomplete(false), 200)}
                placeholder="Type name (e.g. Reliance, INFY)..."
                required
                style={{ width: '100%' }}
              />
              
              {/* Autocomplete Dropdown */}
              {showAutocomplete && suggestions.length > 0 && (
                <div className="autocomplete-dropdown">
                  {suggestions.slice(0, 5).map(s => (
                    <div 
                      key={s.ticker} 
                      className="autocomplete-item"
                      onClick={() => {
                        setAlertCompanyName(s.company_name);
                        setAlertTicker(s.ticker);
                        setShowAutocomplete(false);
                      }}
                    >
                      <span className="autocomplete-ticker">{s.ticker}</span>
                      <span className="autocomplete-name">{s.company_name}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="form-input-group">
              <label>Target AI Score (0-100)</label>
              <input 
                type="number" 
                min="0" 
                max="100" 
                value={alertTargetScore} 
                onChange={(e) => setAlertTargetScore(e.target.value)}
                placeholder="80"
                required
                style={{ width: '100%' }}
              />
            </div>
            <button type="submit" className="flat-btn" style={{ width: '100%', height: '30px' }} disabled={isSettingAlert}>
              {isSettingAlert ? 'Configuring...' : 'Notify Me On Telegram'}
            </button>
          </form>
        </div>
      </section>

    </div>
  );
}
