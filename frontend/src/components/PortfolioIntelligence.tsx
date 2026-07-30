import React, { useState, useEffect } from 'react';
import { Briefcase, Activity, AlertCircle, Award, TrendingUp, TrendingDown, Coins, BarChart3, RotateCw, ShieldAlert, ArrowRightLeft } from 'lucide-react';

interface PortfolioItem {
  ticker: string;
  quantity: number;
  entryPrice: number;
}

interface PortfolioIntelligenceProps {
  portfolio: PortfolioItem[];
  activeStocks: any[];
  apiBase: string;
}

export default function PortfolioIntelligence({ portfolio: parentPortfolio, activeStocks, apiBase }: PortfolioIntelligenceProps) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [holdingsAnalysis, setHoldingsAnalysis] = useState<any[]>([]);
  const [loadingAnalysis, setLoadingAnalysis] = useState<boolean>(false);

  const fetchHoldingsAnalysis = () => {
    setLoadingAnalysis(true);
    fetch(`${apiBase}/api/portfolio/holdings-analysis`)
      .then(res => res.json())
      .then(resData => {
        if (resData.status === 'success') {
          setHoldingsAnalysis(resData.holdings || []);
        }
        setLoadingAnalysis(false);
      })
      .catch(err => {
        console.error("Error fetching holdings analysis:", err);
        setLoadingAnalysis(false);
      });
  };

  const fetchPortfolioData = () => {
    setLoading(true);
    fetch(`${apiBase}/portfolio/intelligence`)
      .then(res => res.json())
      .then(resData => {
        if (resData.status === 'success') {
          setData(resData);
        } else {
          setData({
            status: "error",
            portfolio: {
              holdings: [],
              cash_available: 0.0,
              realized_pnl: 0.0,
              unrealized_pnl: 0.0,
              authenticated: false,
              error: "Broker authentication required."
            }
          });
        }
        setLoading(false);
      })
      .catch(err => {
        console.error("Error loading portfolio intelligence:", err);
        setData({
          status: "error",
          portfolio: {
            holdings: [],
            cash_available: 0.0,
            realized_pnl: 0.0,
            unrealized_pnl: 0.0,
            authenticated: false,
            error: "Connection to portfolio server failed."
          }
        });
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchPortfolioData();
    fetchHoldingsAnalysis();
  }, [refreshKey]);

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '300px', gap: '1rem', color: 'var(--text-secondary)' }}>
        <div style={{ width: '40px', height: '40px', border: '3px solid rgba(255,255,255,0.05)', borderTopColor: 'var(--info)', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
        <span style={{ fontSize: '0.85rem' }}>Analyzing entire portfolio risk and allocation matrices...</span>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  const portfolioData = data?.portfolio || {
    holdings: [],
    cash_available: 0.0,
    realized_pnl: 0.0,
    unrealized_pnl: 0.0,
    authenticated: false,
    error: "Broker authentication required."
  };

  // If unauthenticated, show broker authentication warning screen
  if (!portfolioData.authenticated) {
    return (
      <div className="card-panel" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '3rem 2rem', textAlign: 'center', minHeight: '350px', background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.02) 0%, rgba(21, 23, 30, 0.95) 100%)', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
        <ShieldAlert size={48} className="text-bearish" style={{ marginBottom: '1.25rem', filter: 'drop-shadow(0 0 8px rgba(239, 68, 68, 0.3))' }} />
        <h3 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>Broker Authentication Required</h3>
        <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', maxWidth: '460px', lineHeight: '1.5', marginBottom: '1.75rem' }}>
          Your Upstox live portfolio session is expired or invalid. Please connect your Upstox broker account to unlock real-time portfolio analytics, positions costing, risk exposures, and live execution features.
        </p>
        <button 
          onClick={() => { window.location.href = `${apiBase}/api/upstox/login`; }}
          className="flat-btn"
          style={{ height: '38px', padding: '0 1.5rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'linear-gradient(135deg, var(--info) 0%, #2563eb 100%)', border: 'none', boxShadow: '0 4px 12px rgba(37, 99, 235, 0.3)' }}
        >
          Reconnect Upstox Broker
        </button>
      </div>
    );
  }

  // Calculate live portfolio summary metrics
  const cash = portfolioData.cash_available;
  const buyingPower = portfolioData.buying_power || 0.0;
  const marginUsed = portfolioData.margin_used || 0.0;
  const totalCash = portfolioData.total_cash || 0.0;
  let holdingsValue = 0.0;
  let todayPnl = 0.0;
  let overallPnl = portfolioData.unrealized_pnl || 0.0;

  const holdingsList = portfolioData.holdings || [];
  holdingsList.forEach((h: any) => {
    const qty = floatVal(h.quantity || h.qty);
    const lastPrice = floatVal(h.last_price || h.ltp);
    const closePrice = floatVal(h.close_price || lastPrice);
    holdingsValue += qty * lastPrice;
    todayPnl += (lastPrice - closePrice) * qty;
  });

  const totalPortfolioValue = cash + holdingsValue;

  const health = data?.health || {
    overall_health_score: 75.0,
    diversification_score: 80.0,
    portfolio_beta: 1.0,
    portfolio_volatility: 15.0,
    cash_allocation_pct: totalPortfolioValue > 0 ? Math.round((cash / totalPortfolioValue) * 100) : 10.0,
    risk_rating: 'Medium',
    sector_concentration: {},
    stock_concentration: {},
    diversification_engine: { overweight_sectors: [], underweight_sectors: [], single_stock_concentration: [] }
  };

  const advice = data?.advice || {
    overall_outlook: "Balanced growth under current regime conditions.",
    top_risks: [],
    best_opportunities: [],
    recommended_cash_pct: 15.0,
    maximum_exposure_pct: 20.0,
    sector_advice: "Maintain diversified holdings.",
    rebalancing_suggestions: [],
    priority_actions: []
  };

  // Color mapping
  const healthColor = health.overall_health_score >= 80 ? 'var(--success)' : health.overall_health_score >= 50 ? 'var(--warning)' : 'var(--danger)';
  const riskColor = health.risk_rating === 'Low' ? 'var(--success)' : health.risk_rating === 'Medium' ? 'var(--info)' : health.risk_rating === 'High' ? 'var(--warning)' : 'var(--danger)';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', width: '100%' }}>
      
      {/* Header Controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 className="section-title" style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <Briefcase size={18} /> Portfolio Intelligence & Advisories
        </h2>
        <button 
          onClick={() => setRefreshKey(prev => prev + 1)}
          className="flat-btn flat-btn-outline" 
          style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', height: '28px', padding: '0 0.5rem', fontSize: '0.72rem' }}
        >
          <RotateCw size={12} /> Recalculate Health
        </button>
      </div>

      {/* Dynamic Broker Portfolio Summary Dials */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '1rem' }}>
        
        <div className="card-panel" style={{ padding: '0.85rem 1rem', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)' }}>
          <span style={{ fontSize: '0.62rem', color: 'var(--text-secondary)', textTransform: 'uppercase', display: 'block', letterSpacing: '0.05em' }}>Portfolio Value</span>
          <div style={{ fontSize: '1.2rem', fontWeight: 800, marginTop: '0.25rem', color: 'var(--text-primary)' }}>
            ₹{totalPortfolioValue.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>

        <div className="card-panel" style={{ padding: '0.85rem 1rem', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)' }}>
          <span style={{ fontSize: '0.62rem', color: 'var(--text-secondary)', textTransform: 'uppercase', display: 'block', letterSpacing: '0.05em' }}>Buying Power</span>
          <div style={{ fontSize: '1.2rem', fontWeight: 800, marginTop: '0.25rem', color: 'var(--info)' }}>
            ₹{buyingPower.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>

        <div className="card-panel" style={{ padding: '0.85rem 1rem', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)' }}>
          <span style={{ fontSize: '0.62rem', color: 'var(--text-secondary)', textTransform: 'uppercase', display: 'block', letterSpacing: '0.05em' }}>Margin Used</span>
          <div style={{ fontSize: '1.2rem', fontWeight: 800, marginTop: '0.25rem', color: 'var(--warning)' }}>
            ₹{marginUsed.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>

        <div className="card-panel" style={{ padding: '0.85rem 1rem', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)' }}>
          <span style={{ fontSize: '0.62rem', color: 'var(--text-secondary)', textTransform: 'uppercase', display: 'block', letterSpacing: '0.05em' }}>Total Cash</span>
          <div style={{ fontSize: '1.2rem', fontWeight: 800, marginTop: '0.25rem', color: 'var(--text-primary)' }}>
            ₹{totalCash.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>

        <div className="card-panel" style={{ padding: '0.85rem 1rem', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)' }}>
          <span style={{ fontSize: '0.62rem', color: 'var(--text-secondary)', textTransform: 'uppercase', display: 'block', letterSpacing: '0.05em' }}>Holdings Value</span>
          <div style={{ fontSize: '1.2rem', fontWeight: 800, marginTop: '0.25rem', color: 'var(--text-primary)' }}>
            ₹{holdingsValue.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>

        <div className="card-panel" style={{ padding: '0.85rem 1rem', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)' }}>
          <span style={{ fontSize: '0.62rem', color: 'var(--text-secondary)', textTransform: 'uppercase', display: 'block', letterSpacing: '0.05em' }}>Today's Return</span>
          <div style={{ fontSize: '1.2rem', fontWeight: 800, marginTop: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.25rem', color: todayPnl >= 0 ? 'var(--success)' : 'var(--danger)' }}>
            {todayPnl >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            ₹{todayPnl.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>

        <div className="card-panel" style={{ padding: '0.85rem 1rem', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)' }}>
          <span style={{ fontSize: '0.62rem', color: 'var(--text-secondary)', textTransform: 'uppercase', display: 'block', letterSpacing: '0.05em' }}>Overall Return</span>
          <div style={{ fontSize: '1.2rem', fontWeight: 800, marginTop: '0.25rem', display: 'flex', alignItems: 'center', gap: '0.25rem', color: overallPnl >= 0 ? 'var(--success)' : 'var(--danger)' }}>
            {overallPnl >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            ₹{overallPnl.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
        </div>

      </div>

      {/* Concentration Risk Alert Banner */}
      {(health.diversification_engine?.overweight_sectors?.length > 0 || health.diversification_engine?.single_stock_concentration?.length > 0) && (
        <div className="card-panel" style={{ display: 'flex', alignItems: 'center', gap: '1rem', borderLeft: '4px solid var(--danger)', padding: '1rem', background: 'rgba(239, 68, 68, 0.02)', borderColor: 'rgba(239, 68, 68, 0.15)' }}>
          <ShieldAlert className="text-bearish" size={24} style={{ filter: 'drop-shadow(0 0 4px rgba(239, 68, 68, 0.3))' }} />
          <div>
            <h4 style={{ margin: 0, fontSize: '0.85rem', fontWeight: 800, color: 'var(--text-primary)' }}>Portfolio Concentration Alert</h4>
            <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
              {health.diversification_engine.overweight_sectors.length > 0 && `Overweight Sectors: ${health.diversification_engine.overweight_sectors.join(', ')} (>35% limit). `}
              {health.diversification_engine.single_stock_concentration.length > 0 && `High Stock Concentration: ${health.diversification_engine.single_stock_concentration.join(', ')} (>25% limit). `}
              Consider rebalancing allocations to reduce correlation risk.
            </p>
          </div>
        </div>
      )}

      {/* Grid containing gauges & allocations */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
        
        {/* Overall Health Card */}
        <div className="card-panel" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '1.5rem 1rem', position: 'relative' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: '1rem' }}>Overall Health Score</span>
          <div style={{ position: 'relative', width: '120px', height: '120px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="100%" height="100%" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,0.02)" strokeWidth="8" />
              <circle 
                cx="50" cy="50" r="40" 
                fill="none" 
                stroke={healthColor} 
                strokeWidth="8" 
                strokeDasharray={2 * Math.PI * 40}
                strokeDashoffset={(2 * Math.PI * 40) * (1 - health.overall_health_score / 100)}
                strokeLinecap="round"
                transform="rotate(-90 50 50)"
              />
            </svg>
            <div style={{ position: 'absolute', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <span style={{ fontSize: '1.8rem', fontWeight: 900, color: 'var(--text-primary)' }}>{health.overall_health_score}</span>
              <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)' }}>HEALTHY</span>
            </div>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '1rem', textAlign: 'center' }}>
            Diversification rating: <strong>{health.diversification_score}/100</strong>
          </span>
        </div>

        {/* Risk Profile Card */}
        <div className="card-panel" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '1.5rem 1rem' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: '1rem' }}>Risk Rating</span>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '120px' }}>
            <span style={{ fontSize: '2.2rem', fontWeight: 900, color: riskColor, textTransform: 'uppercase' }}>{health.risk_rating}</span>
            <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.75rem', fontSize: '0.75rem' }}>
              <span>Beta: <strong>{health.portfolio_beta}</strong></span>
              <span>Volatility: <strong>{health.portfolio_volatility}%</strong></span>
            </div>
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '1rem', textAlign: 'center' }}>
            Target single position cap limit: <strong>{advice.maximum_exposure_pct}%</strong>
          </span>
        </div>

        {/* Capital Exposures cash buffer */}
        <div className="card-panel" style={{ padding: '1.25rem' }}>
          <h3 className="section-title" style={{ fontSize: '0.8rem', marginBottom: '0.75rem' }}><Coins size={14} className="text-warning" /> Capital Exposures</h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.25rem', fontWeight: 600 }}>
                <span>Holdings ({(100 - health.cash_allocation_pct).toFixed(1)}%)</span>
                <span>Cash Buffer ({health.cash_allocation_pct}%)</span>
              </div>
              <div style={{ display: 'flex', height: '8px', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{ width: `${100 - health.cash_allocation_pct}%`, backgroundColor: 'var(--info)' }}></div>
                <div style={{ width: `${health.cash_allocation_pct}%`, backgroundColor: 'var(--warning)' }}></div>
              </div>
            </div>

            <div style={{ marginTop: '0.4rem' }}>
              <span style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.5rem', textTransform: 'uppercase' }}>Sector Concentration</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {Object.entries(health.sector_concentration).slice(0, 3).map(([sector, pct]: any) => (
                  <div key={sector}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-primary)', marginBottom: '0.15rem' }}>
                      <span>{sector}</span>
                      <span>{pct}%</span>
                    </div>
                    <div style={{ background: 'rgba(255,255,255,0.02)', height: '4px', borderRadius: '2px', overflow: 'hidden' }}>
                      <div style={{ width: `${pct}%`, backgroundColor: 'var(--success)' }}></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* Asset Cost Basis Table */}
      <div className="card-panel">
        <h3 className="section-title" style={{ margin: '0 0 1rem 0' }}><Briefcase size={15} /> Asset Cost Basis & Performance (Single Source of Truth)</h3>
        {holdingsList.length > 0 ? (
          <div className="table-container">
            <table className="premium-table">
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Shares Held</th>
                  <th>Avg Entry Cost</th>
                  <th>Market Price</th>
                  <th>Invested Capital</th>
                  <th>Current Value</th>
                  <th>Today's Return</th>
                  <th>Overall Return</th>
                </tr>
              </thead>
              <tbody>
                {holdingsList.map((item: any, idx: number) => {
                  const ticker = item.trading_symbol || item.ticker || item.tradingsymbol || 'Unknown';
                  const qty = floatVal(item.quantity || item.qty);
                  const entryPrice = floatVal(item.average_price);
                  const marketPriceVal = floatVal(item.last_price || item.ltp);
                  const closePrice = floatVal(item.close_price || marketPriceVal);

                  const totalCost = qty * entryPrice;
                  const currentValue = qty * marketPriceVal;
                  
                  const holdingTodayPnl = (marketPriceVal - closePrice) * qty;
                  const overallHoldingPnl = floatVal(item.pnl);
                  
                  const profitPct = totalCost > 0 ? (overallHoldingPnl / totalCost) * 100 : 0.0;

                  return (
                    <tr key={idx}>
                      <td className="table-ticker">{ticker}</td>
                      <td>{qty}</td>
                      <td>₹{entryPrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                      <td className="table-price">₹{marketPriceVal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                      <td>₹{totalCost.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                      <td className="table-price">₹{currentValue.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                      <td className={holdingTodayPnl >= 0 ? 'text-bullish' : 'text-bearish'} style={{ fontWeight: 600 }}>
                        {holdingTodayPnl >= 0 ? '+' : ''}₹{holdingTodayPnl.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className={overallHoldingPnl >= 0 ? 'text-bullish' : 'text-bearish'} style={{ fontWeight: 700 }}>
                        {overallHoldingPnl >= 0 ? '+' : ''}₹{overallHoldingPnl.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ({overallHoldingPnl >= 0 ? '+' : ''}{profitPct.toFixed(2)}%)
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state" style={{ padding: '2rem 1rem' }}>
            <Briefcase size={36} className="empty-state-icon" style={{ opacity: 0.3 }} />
            <h3>No Active Broker Holdings</h3>
            <p style={{ fontSize: '0.82rem', marginTop: '0.4rem', color: 'var(--text-secondary)' }}>
              No open long-term holdings detected in your Upstox broker account. Place order bids on ranked Shariah-compliant equities to start building your portfolio.
            </p>
          </div>
        )}
      </div>

      {/* Holdings AI Advisory & Ratings */}
      <div className="card-panel" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h3 className="section-title" style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Award size={16} className="text-info" /> Holdings AI Recommendations & Safety Ratings
          </h3>
          <button 
            onClick={fetchHoldingsAnalysis}
            disabled={loadingAnalysis}
            className="flat-btn flat-btn-outline" 
            style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', height: '26px', padding: '0 0.5rem', fontSize: '0.7rem' }}
          >
            {loadingAnalysis ? 'Running Engine...' : 'Re-Run AI Review'}
          </button>
        </div>

        {loadingAnalysis ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '2rem', gap: '0.5rem' }}>
            <div style={{ width: '24px', height: '24px', border: '2px solid rgba(255,255,255,0.05)', borderTopColor: 'var(--info)', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>Gemini is analyzing technicals, sentiment, and sizing for each holding...</span>
          </div>
        ) : holdingsAnalysis.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {holdingsAnalysis.map((item: any, idx: number) => {
              const recommendation = item.analysis?.decision || 'HOLD';
              const confidence = item.analysis?.confidence || 60;
              const risk = item.analysis?.risk_score || 50;
              const reward = item.analysis?.expected_reward || 'N/A';
              const reasoning = item.analysis?.reasoning || [];
              const suggestedQty = item.analysis?.suggested_quantity || 0;

              let recColor = 'var(--text-secondary)';
              if (recommendation === 'BUY') recColor = 'var(--success)';
              else if (recommendation === 'ACCUMULATE') recColor = 'var(--info)';
              else if (recommendation === 'REDUCE') recColor = 'var(--warning)';
              else if (recommendation === 'SELL') recColor = 'var(--danger)';

              return (
                <div key={idx} className="card-panel" style={{ background: 'rgba(255,255,255,0.005)', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '1rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', alignItems: 'center', gap: '0.5rem', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '0.5rem', marginBottom: '0.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                      <span style={{ fontWeight: 800, fontSize: '1rem', color: 'var(--text-primary)' }}>{item.ticker}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{item.sector}</span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Alloc: {item.allocation_pct}% ({item.shares_held} shrs)</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{
                        fontSize: '0.7rem',
                        fontWeight: 800,
                        padding: '0.15rem 0.5rem',
                        borderRadius: '4px',
                        background: `${recColor}15`,
                        color: recColor,
                        border: `1px solid ${recColor}30`,
                        letterSpacing: '0.05em'
                      }}>
                        {recommendation}
                      </span>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', fontSize: '0.8rem' }}>
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                        <span style={{ color: 'var(--text-secondary)' }}>AI Confidence:</span>
                        <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{confidence}%</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                        <span style={{ color: 'var(--text-secondary)' }}>Position Risk Rating:</span>
                        <span style={{ fontWeight: 700, color: risk > 60 ? 'var(--danger)' : risk > 40 ? 'var(--warning)' : 'var(--success)' }}>{risk}/100</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                        <span style={{ color: 'var(--text-secondary)' }}>Expected Target:</span>
                        <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{reward}</span>
                      </div>
                      {suggestedQty > 0 && suggestedQty !== item.shares_held && (
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.4rem', borderTop: '1px dashed rgba(255,255,255,0.05)', paddingTop: '0.4rem' }}>
                          <span style={{ color: 'var(--text-secondary)' }}>Suggested Qty:</span>
                          <span style={{ fontWeight: 700, color: recColor }}>{suggestedQty} shares</span>
                        </div>
                      )}
                    </div>
                    <div>
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontWeight: 700, display: 'block', marginBottom: '0.25rem', letterSpacing: '0.05em' }}>REASONING MATRIX</span>
                      <ul style={{ margin: 0, paddingLeft: '1rem', color: 'var(--text-secondary)', fontSize: '0.75rem', lineHeight: '1.4' }}>
                        {reasoning.map((r: string, rIdx: number) => (
                          <li key={rIdx} style={{ marginBottom: '0.2rem' }}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="empty-state" style={{ padding: '1.5rem 1rem' }}>
            <Award size={28} className="empty-state-icon" style={{ opacity: 0.3 }} />
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: 0 }}>
              AI analysis not yet loaded. Re-run review to fetch holdings ratings.
            </p>
          </div>
        )}
      </div>

      {/* AI Advisory Panel */}
      <div className="card-panel" style={{ borderLeft: '4px solid var(--info)' }}>
        <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
          <Award size={16} className="text-info" /> AI Portfolio Advisor Outlook
        </h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.5', marginBottom: '1.25rem' }}>
          {advice.overall_outlook}
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
          <div className="factor-box" style={{ background: 'rgba(255,255,255,0.01)', margin: 0 }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--success)', letterSpacing: '0.05em', display: 'block', marginBottom: '0.4rem' }}>BEST OPPORTUNITIES</span>
            <ul style={{ margin: 0, paddingLeft: '1.1rem', color: 'var(--text-secondary)', fontSize: '0.78rem', lineHeight: '1.4' }}>
              {advice.best_opportunities.map((item: string, idx: number) => <li key={idx} style={{ marginBottom: '0.2rem' }}>{item}</li>)}
            </ul>
          </div>

          <div className="factor-box" style={{ background: 'rgba(255,255,255,0.01)', margin: 0 }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--danger)', letterSpacing: '0.05em', display: 'block', marginBottom: '0.4rem' }}>PORTFOLIO RISKS</span>
            <ul style={{ margin: 0, paddingLeft: '1.1rem', color: 'var(--text-secondary)', fontSize: '0.78rem', lineHeight: '1.4' }}>
              {advice.top_risks.map((item: string, idx: number) => <li key={idx} style={{ marginBottom: '0.2rem' }}>{item}</li>)}
            </ul>
          </div>
        </div>
      </div>

      {/* Rebalancing and Strategic Actions */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
        
        {/* Diversification warnings & rebalancing */}
        <div className="card-panel">
          <h3 className="section-title"><BarChart3 size={15} /> Diversification Engine</h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.78rem', marginTop: '0.5rem' }}>
            {health.diversification_engine.overweight_sectors.length > 0 && (
              <div style={{ padding: '0.5rem', background: 'rgba(239,68,68,0.03)', border: '1px solid rgba(239,68,68,0.1)', borderRadius: '4px', color: 'var(--danger)' }}>
                <strong>Overweight Sectors:</strong> {health.diversification_engine.overweight_sectors.join(', ')}
              </div>
            )}

            {health.diversification_engine.single_stock_concentration.length > 0 && (
              <div style={{ padding: '0.5rem', background: 'rgba(245,158,11,0.03)', border: '1px solid rgba(245,158,11,0.1)', borderRadius: '4px', color: 'var(--warning)' }}>
                <strong>Single Stock Cap Alerts:</strong> {health.diversification_engine.single_stock_concentration.map((t: string) => `${t} (>25%)`).join(', ')}
              </div>
            )}

            <div>
              <span style={{ fontWeight: 700, color: 'var(--info)', display: 'block', marginBottom: '0.25rem', fontSize: '0.68rem' }}>REBALANCING STEPS</span>
              <ul style={{ margin: 0, paddingLeft: '1rem', color: 'var(--text-secondary)' }}>
                {advice.rebalancing_suggestions.map((item: string, idx: number) => <li key={idx} style={{ marginBottom: '0.2rem' }}>{item}</li>)}
              </ul>
            </div>
          </div>
        </div>

        {/* Priority Actions */}
        <div className="card-panel">
          <h3 className="section-title"><Activity size={15} /> Priority Action Guidelines</h3>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            <ul style={{ margin: 0, paddingLeft: '1rem' }}>
              {advice.priority_actions.map((item: string, idx: number) => (
                <li key={idx} style={{ marginBottom: '0.35rem' }}>
                  <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

      </div>

    </div>
  );
}

// Utility to parse numbers safely
function floatVal(val: any): number {
  if (val === undefined || val === null) return 0.0;
  const num = parseFloat(val);
  return isNaN(num) ? 0.0 : num;
}
