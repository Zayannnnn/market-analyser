import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  Briefcase, 
  History, 
  BookOpen, 
  Play, 
  RotateCcw, 
  AlertCircle, 
  CheckCircle2, 
  DollarSign, 
  Percent, 
  Award,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

interface OpenPosition {
  ticker: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  stop_loss: number;
  target: number;
  highest_price: number;
  lowest_price: number;
  entry_date: string;
  ai_reasoning: string;
  confidence: number;
  risk_score: number;
  market_regime: string;
  news_sentiment: string;
  strategy_votes: Record<string, string>;
}

interface CompletedTrade {
  ticker: string;
  quantity: number;
  entry_price: number;
  exit_price: number;
  entry_date: string;
  exit_date: string;
  stop_loss: number;
  target: number;
  holding_period_days: number;
  pnl_val: number;
  pnl_pct: number;
  max_drawdown: number;
  mfe: number;
  mae: number;
  ai_reasoning: string;
  confidence: number;
  risk_score: number;
  market_regime: string;
  news_sentiment: string;
  strategy_votes: Record<string, string>;
}

interface PortfolioState {
  cash: number;
  portfolio_value: number;
  realized_pnl: number;
  unrealized_pnl: number;
  equity_curve: Array<{ date: string; value: number }>;
  daily_returns: Array<{ date: string; return_pct: number }>;
}

interface Analytics {
  win_rate: number;
  profit_factor: number;
  avg_winner: number;
  avg_loser: number;
  expectancy: number;
  max_drawdown: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  calmar_ratio: number;
  trades_count: number;
  best_strategy: string;
  worst_strategy: string;
}

interface PaperTradingDashboardProps {
  apiBase: string;
  onShowToast: (msg: string, isError?: boolean) => void;
}

export default function PaperTradingDashboard({ apiBase, onShowToast }: PaperTradingDashboardProps) {
  const [portfolio, setPortfolio] = useState<PortfolioState | null>(null);
  const [positions, setPositions] = useState<OpenPosition[]>([]);
  const [trades, setTrades] = useState<CompletedTrade[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);
  const [learnings, setLearnings] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isScanning, setIsScanning] = useState<boolean>(false);
  const [isResetting, setIsResetting] = useState<boolean>(false);
  const [expandedJournal, setExpandedJournal] = useState<Record<string, boolean>>({});

  const fetchData = async () => {
    try {
      setIsLoading(true);
      // Fetch portfolio
      const resPort = await fetch(`${apiBase}/api/paper/portfolio`);
      const dataPort = await resPort.json();
      setPortfolio(dataPort);

      // Fetch positions
      const resPos = await fetch(`${apiBase}/api/paper/positions`);
      const dataPos = await resPos.json();
      setPositions(dataPos);

      // Fetch trades
      const resTrades = await fetch(`${apiBase}/api/paper/trades`);
      const dataTrades = await resTrades.json();
      // Sort trades newest exit first
      const sortedTrades = (dataTrades as CompletedTrade[]).sort(
        (a, b) => new Date(b.exit_date).getTime() - new Date(a.exit_date).getTime()
      );
      setTrades(sortedTrades);

      // Fetch analytics
      const resAnalytics = await fetch(`${apiBase}/api/paper/analytics`);
      const dataAnalytics = await resAnalytics.json();
      setAnalytics(dataAnalytics);

      // Fetch learnings
      const resLearnings = await fetch(`${apiBase}/api/paper/learnings`);
      const dataLearnings = await resLearnings.json();
      setLearnings(dataLearnings.lessons || 'No trade insights available yet.');
    } catch (e) {
      console.error(e);
      onShowToast('Failed to retrieve paper trading portfolio datasets.', true);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRunScan = async () => {
    try {
      setIsScanning(true);
      const res = await fetch(`${apiBase}/api/paper/scan`, { method: 'POST' });
      if (res.ok) {
        onShowToast('Daily market scanning simulation completed successfully!');
        fetchData();
      } else {
        onShowToast('Error executing daily paper trading scan.', true);
      }
    } catch (e) {
      onShowToast('Connection failed during daily scanning execution.', true);
    } finally {
      setIsScanning(false);
    }
  };

  const handleResetPortfolio = async () => {
    if (!window.confirm('Are you sure you want to reset your virtual portfolio? This will purge all trade logs, open positions, and restore capital to ₹10,00,000.')) {
      return;
    }
    try {
      setIsResetting(true);
      const res = await fetch(`${apiBase}/api/paper/reset`, { method: 'POST' });
      if (res.ok) {
        onShowToast('Paper trading portfolio reset completed.');
        fetchData();
      } else {
        onShowToast('Error resetting portfolio.', true);
      }
    } catch (e) {
      onShowToast('Reset connection failure.', true);
    } finally {
      setIsResetting(false);
    }
  };

  const toggleExpand = (id: string) => {
    setExpandedJournal(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  // Render SVG equity curve path
  const renderEquityCurve = () => {
    if (!portfolio || !portfolio.equity_curve || portfolio.equity_curve.length < 2) {
      return (
        <div style={{ height: '220px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
          Scan multiple trading days to construct equity curve logs.
        </div>
      );
    }

    const width = 600;
    const height = 200;
    const padding = 20;

    const values = portfolio.equity_curve.map(c => c.value);
    const maxVal = Math.max(...values, 1000000);
    const minVal = Math.min(...values, 1000000);
    const range = maxVal - minVal || 100;

    const points = portfolio.equity_curve.map((c, i) => {
      const x = padding + (i / (portfolio.equity_curve.length - 1)) * (width - padding * 2);
      const y = height - padding - ((c.value - minVal) / range) * (height - padding * 2);
      return { x, y };
    });

    const pathData = `M ${points.map(p => `${p.x} ${p.y}`).join(' L ')}`;
    const areaData = `${pathData} L ${points[points.length - 1].x} ${height - padding} L ${points[0].x} ${height - padding} Z`;

    return (
      <div style={{ width: '100%', overflowX: 'auto' }}>
        <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} style={{ display: 'block', background: 'rgba(255,255,255,0.01)' }}>
          {/* Fill Area */}
          <path d={areaData} fill="url(#equityGrad)" opacity="0.15" />
          {/* Line Path */}
          <path d={pathData} fill="none" stroke="var(--info)" strokeWidth="2.5" />
          
          {/* Grid lines */}
          <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="var(--border-color)" strokeWidth="1" />
          
          {/* Gradient Definition */}
          <defs>
            <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--info)" />
              <stop offset="100%" stopColor="transparent" />
            </linearGradient>
          </defs>

          {/* Dots */}
          {points.map((p, idx) => (
            <circle 
              key={idx} 
              cx={p.x} 
              cy={p.y} 
              r="3.5" 
              fill="var(--info)" 
              stroke="#FFFFFF" 
              strokeWidth="0.75" 
              title={`₹${portfolio.equity_curve[idx].value.toLocaleString('en-IN')}`}
            />
          ))}
        </svg>
        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem 1rem', fontSize: '0.65rem', color: 'var(--text-muted)' }}>
          <span>Start: {portfolio.equity_curve[0].date}</span>
          <span>Latest Valuation: ₹{portfolio.portfolio_value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
          <span>End: {portfolio.equity_curve[portfolio.equity_curve.length - 1].date}</span>
        </div>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="empty-state" style={{ height: '350px' }}>
        <div className="skeleton-line" style={{ width: '180px', height: '2rem', marginBottom: '1rem' }}></div>
        <div className="skeleton-line" style={{ height: '240px' }}></div>
      </div>
    );
  }

  const realized = portfolio?.realized_pnl || 0;
  const unrealized = portfolio?.unrealized_pnl || 0;
  const totalPnL = realized + unrealized;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', width: '100%', paddingBottom: '3rem' }}>
      
      {/* Header operations row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <TrendingUp className="text-bullish" /> AORA Paper Trading Simulator
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
            Test quantitative strategy consensus rules in real market constraints without financial risk.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button 
            className="flat-btn" 
            style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', height: '36px' }}
            onClick={handleRunScan}
            disabled={isScanning}
          >
            <Play size={14} /> {isScanning ? 'Scanning...' : 'Simulate Trading Day'}
          </button>
          <button 
            className="flat-btn flat-btn-outline" 
            style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', borderColor: 'var(--danger)', color: 'var(--danger)', height: '36px' }}
            onClick={handleResetPortfolio}
            disabled={isResetting}
          >
            <RotateCcw size={14} /> {isResetting ? 'Resetting...' : 'Reset Capital'}
          </button>
        </div>
      </div>

      {/* 1. Portfolio Metrics & Analytics Dashboard */}
      <section className="metrics-row" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
        <div className="info-card">
          <span className="info-card-label">Equity Valuation</span>
          <span className="info-card-value" style={{ color: 'var(--info)' }}>
            ₹{portfolio?.portfolio_value.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
          </span>
        </div>
        <div className="info-card">
          <span className="info-card-label">Virtual Cash Available</span>
          <span className="info-card-value">
            ₹{portfolio?.cash.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
          </span>
        </div>
        <div className="info-card">
          <span className="info-card-label">Realized Profit & Loss</span>
          <span className={`info-card-value ${realized >= 0 ? 'text-bullish' : 'text-bearish'}`}>
            {realized >= 0 ? '+' : ''}₹{realized.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
          </span>
        </div>
        <div className="info-card">
          <span className="info-card-label">Unrealized P&L</span>
          <span className={`info-card-value ${unrealized >= 0 ? 'text-bullish' : 'text-bearish'}`}>
            {unrealized >= 0 ? '+' : ''}₹{unrealized.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
          </span>
        </div>
      </section>

      {/* 2. Strategy Analytics Banners */}
      {analytics && (
        <div className="card-panel" style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)' }}>
          <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.85rem' }}>
            <Award size={16} className="text-info" /> Quant Risk & Performance Analytics
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
            <div style={{ padding: '0.65rem', background: 'rgba(255,255,255,0.01)', borderRadius: '6px', textAlign: 'center' }}>
              <div style={{ fontSize: '0.62rem', color: 'var(--text-secondary)' }}>Win Rate</div>
              <div style={{ fontSize: '1.05rem', fontWeight: 800, marginTop: '0.2rem', color: 'var(--success)' }}>
                {analytics.win_rate}%
              </div>
            </div>
            <div style={{ padding: '0.65rem', background: 'rgba(255,255,255,0.01)', borderRadius: '6px', textAlign: 'center' }}>
              <div style={{ fontSize: '0.62rem', color: 'var(--text-secondary)' }}>Profit Factor</div>
              <div style={{ fontSize: '1.05rem', fontWeight: 800, marginTop: '0.2rem' }}>
                {analytics.profit_factor}
              </div>
            </div>
            <div style={{ padding: '0.65rem', background: 'rgba(255,255,255,0.01)', borderRadius: '6px', textAlign: 'center' }}>
              <div style={{ fontSize: '0.62rem', color: 'var(--text-secondary)' }}>Avg Win/Loss %</div>
              <div style={{ fontSize: '1.05rem', fontWeight: 800, marginTop: '0.2rem' }}>
                {analytics.avg_winner}% / {analytics.avg_loser}%
              </div>
            </div>
            <div style={{ padding: '0.65rem', background: 'rgba(255,255,255,0.01)', borderRadius: '6px', textAlign: 'center' }}>
              <div style={{ fontSize: '0.62rem', color: 'var(--text-secondary)' }}>Expectancy</div>
              <div style={{ fontSize: '1.05rem', fontWeight: 800, marginTop: '0.2rem', color: analytics.expectancy >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                {analytics.expectancy}%
              </div>
            </div>
            <div style={{ padding: '0.65rem', background: 'rgba(255,255,255,0.01)', borderRadius: '6px', textAlign: 'center' }}>
              <div style={{ fontSize: '0.62rem', color: 'var(--text-secondary)' }}>Max Drawdown</div>
              <div style={{ fontSize: '1.05rem', fontWeight: 800, marginTop: '0.2rem', color: 'var(--danger)' }}>
                {analytics.max_drawdown}%
              </div>
            </div>
            <div style={{ padding: '0.65rem', background: 'rgba(255,255,255,0.01)', borderRadius: '6px', textAlign: 'center' }}>
              <div style={{ fontSize: '0.62rem', color: 'var(--text-secondary)' }}>Sharpe Ratio</div>
              <div style={{ fontSize: '1.05rem', fontWeight: 800, marginTop: '0.2rem', color: 'var(--info)' }}>
                {analytics.sharpe_ratio}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Grid: Chart & AI Learnings */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
        
        {/* Equity Curve SVG Panel */}
        <div className="card-panel">
          <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <TrendingUp size={16} /> Virtual Equity Progression Path
          </h3>
          <div style={{ marginTop: '1rem' }}>
            {renderEquityCurve()}
          </div>
        </div>

        {/* AI Self-Learning insights */}
        <div className="card-panel" style={{ borderLeft: '4px solid var(--success)' }}>
          <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <BookOpen size={16} className="text-success" /> AI Self-Learning Lessons
          </h3>
          <div style={{ marginTop: '0.85rem', fontSize: '0.82rem', lineHeight: '1.5', color: 'var(--text-secondary)' }}>
            <div 
              style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}
              dangerouslySetInnerHTML={{ 
                __html: learnings
                  .replace(/\n/g, '<br/>')
                  .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                  .replace(/\*(.*?)(<br\/>|$)/g, '<li>$1</li>')
              }}
            />
            {learnings.includes('No trade data') && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginTop: '1rem', padding: '0.5rem', background: 'rgba(255,255,255,0.01)', border: '1px dashed var(--border-color)', borderRadius: '4px' }}>
                <AlertCircle size={14} className="text-warning" />
                <span>Insights compile dynamically as simulated exits execute.</span>
              </div>
            )}
          </div>
        </div>

      </div>

      {/* 3. Open Positions Table */}
      <div className="card-panel">
        <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '1rem' }}>
          <Briefcase size={16} /> Open Sim Positions ({positions.length})
        </h3>
        {positions.length > 0 ? (
          <div className="table-responsive">
            <table className="holdings-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Quantity</th>
                  <th>Entry Price</th>
                  <th>Current Price</th>
                  <th>Unrealized P&L</th>
                  <th>Stop Loss</th>
                  <th>Target</th>
                  <th>Risk Rating</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((item, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid var(--border-color)' }}>
                    <td><strong style={{ color: 'var(--text-primary)' }}>{item.ticker}</strong></td>
                    <td>{item.quantity}</td>
                    <td>₹{item.entry_price.toFixed(2)}</td>
                    <td>₹{item.current_price.toFixed(2)}</td>
                    <td className={item.unrealized_pnl >= 0 ? 'text-bullish' : 'text-bearish'} style={{ fontWeight: 700 }}>
                      {item.unrealized_pnl >= 0 ? '+' : ''}₹{item.unrealized_pnl.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                    </td>
                    <td className="text-bearish">₹{item.stop_loss.toFixed(2)}</td>
                    <td className="text-bullish">₹{item.target.toFixed(2)}</td>
                    <td>
                      <span className={`badge ${item.risk_score > 60 ? 'badge-danger' : 'badge-success'}`}>
                        {item.risk_score}/100 Risk
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ height: '100px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)', fontStyle: 'italic', fontSize: '0.8rem' }}>
            No open paper positions found. Run daily scan to scanner.
          </div>
        )}
      </div>

      {/* 4. Trade Journal (Completed Trades History) */}
      <div className="card-panel">
        <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '1rem' }}>
          <History size={16} /> Trade Journal & Quant Logs ({trades.length})
        </h3>
        {trades.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {trades.map((t, idx) => {
              const tradeId = `${t.ticker}_${t.entry_date}`;
              const isExpanded = !!expandedJournal[tradeId];
              return (
                <div 
                  key={idx} 
                  style={{ 
                    border: '1px solid var(--border-color)', 
                    borderRadius: '8px', 
                    background: 'rgba(255,255,255,0.01)', 
                    overflow: 'hidden' 
                  }}
                >
                  {/* Header Row */}
                  <div 
                    onClick={() => toggleExpand(tradeId)}
                    style={{ 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center', 
                      padding: '0.75rem 1rem', 
                      cursor: 'pointer',
                      background: 'rgba(255,255,255,0.02)'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                      <strong style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>{t.ticker}</strong>
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                        {t.entry_date} → {t.exit_date} ({t.holding_period_days} days)
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
                      <span className={t.pnl_val >= 0 ? 'text-bullish' : 'text-bearish'} style={{ fontWeight: 700, fontSize: '0.9rem' }}>
                        {t.pnl_val >= 0 ? '+' : ''}₹{t.pnl_val.toLocaleString('en-IN', { maximumFractionDigits: 1 })} ({t.pnl_val >= 0 ? '+' : ''}{t.pnl_pct.toFixed(2)}%)
                      </span>
                      {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </div>
                  </div>

                  {/* Expanded Content Details */}
                  {isExpanded && (
                    <div style={{ padding: '1rem', borderTop: '1px solid var(--border-color)', fontSize: '0.78rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                      
                      {/* Grid metrics */}
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.75rem' }}>
                        <div>Qty Traded: <strong style={{ color: 'var(--text-primary)' }}>{t.quantity}</strong></div>
                        <div>Entry Price: <strong style={{ color: 'var(--text-primary)' }}>₹{t.entry_price.toFixed(2)}</strong></div>
                        <div>Exit Price: <strong style={{ color: 'var(--text-primary)' }}>₹{t.exit_price.toFixed(2)}</strong></div>
                        <div>Stop Loss: <strong className="text-bearish">₹{t.stop_loss.toFixed(2)}</strong></div>
                        <div>Target Price: <strong className="text-bullish">₹{t.target.toFixed(2)}</strong></div>
                      </div>

                      {/* Excursion limits */}
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '0.75rem', padding: '0.5rem', background: 'rgba(255,255,255,0.01)', borderRadius: '4px' }}>
                        <div>Max Favorable Excursion (MFE): <strong className="text-bullish">+{t.mfe.toFixed(2)}%</strong></div>
                        <div>Max Adverse Excursion (MAE): <strong className="text-bearish">{t.mae.toFixed(2)}%</strong></div>
                        <div>Max Drawdown Recorded: <strong className="text-bearish">{t.max_drawdown.toFixed(2)}%</strong></div>
                      </div>

                      {/* Rationale details */}
                      {t.ai_reasoning && (
                        <div style={{ marginTop: '0.35rem', padding: '0.65rem', background: 'rgba(255,255,255,0.01)', border: '1px dashed var(--border-color)', borderRadius: '6px' }}>
                          <span style={{ fontSize: '0.65rem', fontWeight: 700, color: 'var(--info)', display: 'block', marginBottom: '0.2rem' }}>AI DECISION BASIS</span>
                          <p style={{ lineHeight: '1.4', margin: 0 }}>{t.ai_reasoning}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ height: '100px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)', fontStyle: 'italic', fontSize: '0.8rem' }}>
            No journal entries matching completed trade metrics found.
          </div>
        )}
      </div>

    </div>
  );
}
