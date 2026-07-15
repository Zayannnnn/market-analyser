import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  ShieldAlert, 
  HelpCircle, 
  Info, 
  Plus, 
  Settings, 
  RotateCcw,
  CheckCircle,
  AlertTriangle,
  ArrowRightLeft,
  DollarSign,
  PieChart,
  Percent,
  Bookmark
} from 'lucide-react';

interface BuyCandidate {
  ticker: string;
  amount: number;
  reason: string;
}

interface SellCandidate {
  ticker: string;
  amount: number;
  reason: string;
}

interface RebalanceCandidate {
  ticker: string;
  amount: number;
  reason: string;
}

interface HalalWatchlistItem {
  ticker: string;
  sector: string;
  market_cap: string;
  liquidity: string;
  shariah_status: string;
  industry: string;
  risk_rating: string;
  historical_performance: string;
}

interface ManagerState {
  portfolio: {
    cash_available: number;
    holdings: Array<{
      ticker?: string;
      tradingsymbol?: string;
      quantity: number;
      last_price: number;
      average_price: number;
      pnl: number;
    }>;
  };
  health: {
    portfolio_beta: number;
    portfolio_volatility: number;
    sector_exposures: Record<string, number>;
  };
  rebalance_suggestions: string[];
  score: number;
  decision: {
    overall_decision: string;
    cash_action: string;
    buy_candidates?: BuyCandidate[];
    sell_candidates?: SellCandidate[];
    increase_positions?: RebalanceCandidate[];
    reduce_positions?: RebalanceCandidate[];
    risk_summary?: string;
    expected_monthly_return?: string;
    expected_volatility?: string;
    reasoning?: string;
  };
}

interface PortfolioManagerProps {
  apiBase: string;
  onShowToast: (msg: string, isError?: boolean) => void;
}

export default function PortfolioManager({ apiBase, onShowToast }: PortfolioManagerProps) {
  const [data, setData] = useState<ManagerState | null>(null);
  const [halalList, setHalalList] = useState<HalalWatchlistItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSavingStock, setIsSavingStock] = useState<boolean>(false);
  
  // Halal Watchlist editor form states
  const [formTicker, setFormTicker] = useState<string>('');
  const [formSector, setFormSector] = useState<string>('Technology');
  const [formMCap, setFormMCap] = useState<string>('Large Cap');
  const [formLiq, setFormLiq] = useState<string>('High');
  const [formShariah, setFormShariah] = useState<string>('Compliant');
  const [formInd, setFormInd] = useState<string>('');
  const [formRisk, setFormRisk] = useState<string>('Low');
  const [formPerf, setFormPerf] = useState<string>('');

  const fetchData = async () => {
    try {
      setIsLoading(true);
      const res = await fetch(`${apiBase}/api/portfolio/manager`);
      const managerData = await res.json();
      setData(managerData);

      const resList = await fetch(`${apiBase}/api/portfolio/halal-watchlist`);
      const watchlistData = await resList.json();
      setHalalList(watchlistData);
    } catch (e) {
      console.error(e);
      onShowToast("Failed to fetch AI portfolio manager insights.", true);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleAddHalalStock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formTicker.trim() || !formInd.trim() || !formPerf.trim()) {
      onShowToast("Please fill in all stock editor fields.", true);
      return;
    }
    
    try {
      setIsSavingStock(true);
      const queryParams = new URLSearchParams({
        ticker: formTicker.toUpperCase().strip(),
        sector: formSector,
        market_cap: formMCap,
        liquidity: formLiq,
        shariah_status: formShariah,
        industry: formInd,
        risk_rating: formRisk,
        historical_performance: formPerf
      });
      
      const res = await fetch(`${apiBase}/api/portfolio/halal-watchlist?${queryParams.toString()}`, {
        method: "POST"
      });
      
      if (res.ok) {
        onShowToast(`Stock ${formTicker.toUpperCase()} added to compliant watchlist.`);
        // Reset form
        setFormTicker('');
        setFormInd('');
        setFormPerf('');
        fetchData();
      } else {
        onShowToast("Failed to save compliant watchlist asset.", true);
      }
    } catch (e) {
      onShowToast("Connection failed during watchlist update.", true);
    } finally {
      setIsSavingStock(false);
    }
  };

  if (isLoading || !data) {
    return (
      <div className="empty-state" style={{ height: '350px' }}>
        <div className="skeleton-line" style={{ width: '180px', height: '2rem', marginBottom: '1rem' }}></div>
        <div className="skeleton-line" style={{ height: '240px' }}></div>
      </div>
    );
  }

  // Cash maths
  const cash = data.portfolio.cash_available;
  let holdingsValue = 0;
  data.portfolio.holdings.forEach(h => {
    const qty = h.quantity;
    const price = h.last_price;
    holdingsValue += qty * price;
  });
  const portfolioValue = cash + holdingsValue;
  const cashPct = portfolioValue > 0 ? (cash / portfolioValue) * 100.0 : 0.0;

  // Decision Queues
  const buys = data.decision.buy_candidates || [];
  const sells = data.decision.sell_candidates || [];
  const increases = data.decision.increase_positions || [];
  const reduces = data.decision.reduce_positions || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', width: '100%', paddingBottom: '3rem' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <PieChart className="text-bullish" /> AI Portfolio Manager
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
            Professional portfolio rotation, cash reserves management, and Shariah-compliant asset rebalancing suggestions.
          </p>
        </div>
        <button className="flat-btn" onClick={fetchData} style={{ height: '36px' }}>
          <RotateCcw size={14} /> Refresh Advice
        </button>
      </div>

      {/* Grid: Quality Score & Expected Performance */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
        
        {/* Quality Score Dial Card */}
        <div className="card-panel" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', minHeight: '220px' }}>
          <h3 className="info-card-label" style={{ fontSize: '0.85rem', marginBottom: '1rem', width: '100%' }}>Portfolio Quality Score</h3>
          
          <div style={{ position: 'relative', width: '110px', height: '110px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {/* SVG Arc Progress */}
            <svg width="110" height="110" style={{ transform: 'rotate(-90deg)' }}>
              <circle cx="55" cy="55" r="46" fill="transparent" stroke="var(--border-color)" strokeWidth="6" />
              <circle 
                cx="55" 
                cy="55" 
                r="46" 
                fill="transparent" 
                stroke="var(--info)" 
                strokeWidth="7" 
                strokeDasharray={`${2 * Math.PI * 46}`}
                strokeDashoffset={`${2 * Math.PI * 46 * (1 - data.score / 100)}`}
                strokeLinecap="round"
              />
            </svg>
            <div style={{ position: 'absolute', fontSize: '1.85rem', fontWeight: 800, color: 'var(--text-primary)' }}>
              {data.score}
            </div>
          </div>
          
          <div style={{ display: 'flex', gap: '1rem', marginTop: '1.25rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            <div>Beta: <strong>{data.health.portfolio_beta.toFixed(2)}</strong></div>
            <div>Volatility: <strong>{data.health.portfolio_volatility.toFixed(1)}%</strong></div>
          </div>
        </div>

        {/* Expected returns & allocations */}
        <div className="card-panel" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <h3 className="section-title">Institutional Forecasts</h3>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div style={{ padding: '0.75rem', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', borderRadius: '6px' }}>
              <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Expected Monthly Return</span>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, marginTop: '0.2rem', color: 'var(--success)' }}>
                {data.decision.expected_monthly_return || "+1.5%"}
              </div>
            </div>
            <div style={{ padding: '0.75rem', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', borderRadius: '6px' }}>
              <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Expected Portfolio Risk</span>
              <div style={{ fontSize: '1.25rem', fontWeight: 800, marginTop: '0.2rem', color: 'var(--info)' }}>
                {data.decision.expected_volatility || "Medium"}
              </div>
            </div>
          </div>

          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', lineHeight: '1.4', background: 'rgba(255,255,255,0.01)', padding: '0.65rem', borderLeft: '3px solid var(--info)', borderRadius: '4px' }}>
            <strong>Risk Committee Outlook:</strong> {data.decision.risk_summary}
          </div>
        </div>

      </div>

      {/* Sector & Cash Allocation Progress panel */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
        
        {/* Cash Allocation */}
        <div className="card-panel">
          <h3 className="section-title" style={{ marginBottom: '1.25rem' }}>Portfolio Capital Sizing</h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
              <span>Cash reserve: ₹{cash.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
              <strong>{cashPct.toFixed(1)}%</strong>
            </div>
            <div style={{ height: '8px', background: 'var(--border-color)', borderRadius: '4px', overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${cashPct}%`, background: 'var(--success)' }}></div>
            </div>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Target Cash Reserve: 15.0% - 20.0%</span>
          </div>
        </div>

        {/* Sector Allocation */}
        <div className="card-panel">
          <h3 className="section-title" style={{ marginBottom: '1rem' }}>Sector Exposures</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
            {Object.entries(data.health.sector_exposures).map(([sec, exp], idx) => (
              <div key={idx} style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem' }}>
                  <span>{sec}</span>
                  <strong>{exp.toFixed(1)}%</strong>
                </div>
                <div style={{ height: '6px', background: 'var(--border-color)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${exp}%`, background: 'var(--info)' }}></div>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>

      {/* Rebalance Plan checklist */}
      <div className="card-panel" style={{ borderLeft: '4px solid var(--warning)' }}>
        <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.85rem' }}>
          <ArrowRightLeft size={16} className="text-warning" /> AI Rebalancing Recommendations
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {data.rebalance_suggestions.map((suggestion, idx) => (
            <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              {suggestion.startsWith("✅") ? <CheckCircle size={14} className="text-success" /> : <AlertTriangle size={14} className="text-warning" />}
              <span>{suggestion}</span>
            </div>
          ))}
        </div>
      </div>

      {/* AI Decision Queues Panels */}
      <div className="card-panel">
        <h3 className="section-title" style={{ marginBottom: '1.25rem' }}>Investment Committee Execution Queues</h3>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem' }}>
          
          {/* BUY queue */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <h4 style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--success)', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.25rem', margin: 0 }}>
              📥 Buy Queue ({buys.length})
            </h4>
            {buys.length > 0 ? buys.map((b, idx) => (
              <div key={idx} style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', borderRadius: '6px', fontSize: '0.72rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                  <strong>{b.ticker}</strong>
                  <span className="text-success">₹{b.amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
                </div>
                <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.65rem' }}>{b.reason}</p>
              </div>
            )) : <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontStyle: 'italic', padding: '0.5rem' }}>No buy recommendations.</div>}
          </div>

          {/* INCREASE queue */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <h4 style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--info)', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.25rem', margin: 0 }}>
              📈 Increase Queue ({increases.length})
            </h4>
            {increases.length > 0 ? increases.map((i, idx) => (
              <div key={idx} style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', borderRadius: '6px', fontSize: '0.72rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                  <strong>{i.ticker}</strong>
                  <span className="text-info">+₹{i.amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
                </div>
                <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.65rem' }}>{i.reason}</p>
              </div>
            )) : <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontStyle: 'italic', padding: '0.5rem' }}>No top-up suggestions.</div>}
          </div>

          {/* REDUCE queue */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <h4 style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--warning)', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.25rem', margin: 0 }}>
              📉 Trim Queue ({reduces.length})
            </h4>
            {reduces.length > 0 ? reduces.map((r, idx) => (
              <div key={idx} style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', borderRadius: '6px', fontSize: '0.72rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                  <strong>{r.ticker}</strong>
                  <span className="text-warning">-₹{r.amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
                </div>
                <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.65rem' }}>{r.reason}</p>
              </div>
            )) : <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontStyle: 'italic', padding: '0.5rem' }}>No trimming suggestions.</div>}
          </div>

          {/* SELL queue */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <h4 style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--danger)', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.25rem', margin: 0 }}>
              📤 Sell Queue ({sells.length})
            </h4>
            {sells.length > 0 ? sells.map((s, idx) => (
              <div key={idx} style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', borderRadius: '6px', fontSize: '0.72rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                  <strong>{s.ticker}</strong>
                  <span className="text-danger">₹{s.amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
                </div>
                <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.65rem' }}>{s.reason}</p>
              </div>
            )) : <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontStyle: 'italic', padding: '0.5rem' }}>No liquidation recommendations.</div>}
          </div>

        </div>
      </div>

      {/* Shariah watchlist editor and List */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
        
        {/* Watchlist Manager list */}
        <div className="card-panel">
          <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '1rem' }}>
            <Bookmark size={16} /> Shariah Compliant Watchlist ({halalList.length})
          </h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem', maxHeight: '350px', overflowY: 'auto' }}>
            {halalList.map((item, idx) => (
              <div 
                key={idx} 
                style={{ 
                  display: 'flex', 
                  justifyContent: 'space-between', 
                  alignItems: 'center', 
                  padding: '0.65rem', 
                  background: 'rgba(255,255,255,0.01)', 
                  border: '1px solid var(--border-color)', 
                  borderRadius: '6px', 
                  fontSize: '0.75rem' 
                }}
              >
                <div>
                  <strong style={{ color: 'var(--text-primary)' }}>{item.ticker}</strong>
                  <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)', marginLeft: '0.5rem' }}>{item.industry}</span>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <span className="badge badge-success" style={{ fontSize: '0.6rem' }}>Compliant</span>
                  <span style={{ color: 'var(--text-secondary)' }}>{item.historical_performance}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Watchlist adder Form */}
        <div className="card-panel">
          <h3 className="section-title" style={{ marginBottom: '1rem' }}>Register Compliant Stock</h3>
          
          <form onSubmit={handleAddHalalStock} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.78rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
              <div>
                <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Ticker</label>
                <input 
                  type="text" 
                  value={formTicker} 
                  onChange={e => setFormTicker(e.target.value)}
                  className="search-input"
                  style={{ width: '100%', height: '32px' }}
                  placeholder="e.g. INFY"
                />
              </div>
              <div>
                <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Sector</label>
                <select 
                  value={formSector} 
                  onChange={e => setFormSector(e.target.value)}
                  className="search-input"
                  style={{ width: '100%', height: '32px' }}
                >
                  <option>Technology</option>
                  <option>Defence</option>
                  <option>Energy</option>
                  <option>Utilities</option>
                  <option>Healthcare</option>
                </select>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
              <div>
                <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Market Cap</label>
                <select 
                  value={formMCap} 
                  onChange={e => setFormMCap(e.target.value)}
                  className="search-input"
                  style={{ width: '100%', height: '32px' }}
                >
                  <option>Mega Cap</option>
                  <option>Large Cap</option>
                  <option>Mid Cap</option>
                  <option>Small Cap</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Liquidity</label>
                <select 
                  value={formLiq} 
                  onChange={e => setFormLiq(e.target.value)}
                  className="search-input"
                  style={{ width: '100%', height: '32px' }}
                >
                  <option>Very High</option>
                  <option>High</option>
                  <option>Medium</option>
                </select>
              </div>
            </div>

            <div>
              <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Industry Description</label>
              <input 
                type="text" 
                value={formInd} 
                onChange={e => setFormInd(e.target.value)}
                className="search-input"
                style={{ width: '100%', height: '32px' }}
                placeholder="e.g. Software Services"
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
              <div>
                <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Risk Rating</label>
                <select 
                  value={formRisk} 
                  onChange={e => setFormRisk(e.target.value)}
                  className="search-input"
                  style={{ width: '100%', height: '32px' }}
                >
                  <option>Low</option>
                  <option>Medium</option>
                  <option>High</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>1Y Returns performance</label>
                <input 
                  type="text" 
                  value={formPerf} 
                  onChange={e => setFormPerf(e.target.value)}
                  className="search-input"
                  style={{ width: '100%', height: '32px' }}
                  placeholder="e.g. +22.5%"
                />
              </div>
            </div>

            <button 
              type="submit" 
              className="flat-btn" 
              style={{ width: '100%', height: '34px', marginTop: '0.5rem' }}
              disabled={isSavingStock}
            >
              <Plus size={14} /> {isSavingStock ? 'Registering...' : 'Add Shariah Compliant Asset'}
            </button>
          </form>
        </div>

      </div>

    </div>
  );
}
