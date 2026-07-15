import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  RotateCcw,
  CheckCircle,
  AlertTriangle,
  ArrowRightLeft,
  DollarSign,
  PieChart,
  Shield,
  Layers,
  ArrowDownRight,
  ArrowUpRight
} from 'lucide-react';

interface OpportunityStock {
  ticker: string;
  company: string;
  sector: string;
  industry: string;
  market_cap: string;
  liquidity: string;
  avg_volume: number;
  risk_rating: string;
  historical_volatility: string;
  shariah_status: string;
  opportunity_score: number;
  technical_score: number;
  trend_score: number;
  volume_score: number;
  risk_score: number;
  expected_return: string;
  expected_drawdown: string;
  expected_holding_period: string;
}

interface SizingItem {
  max_capital_allocation: number;
  suggested_cash_reserve: number;
  max_suggested_qty: number;
}

interface RotationPlanItem {
  sell_ticker: string;
  buy_ticker: string;
  amount: number;
  justification: string;
}

interface RotationState {
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
  opportunity_universe: OpportunityStock[];
  rotation_checklist: Array<{
    holding_ticker: string;
    holding_score: number;
    opportunity_ticker: string;
    opportunity_score: number;
    action: string;
    justification: string;
  }>;
  sizing_matrix: Record<string, SizingItem>;
  rebalance_suggestions: string[];
  score: number;
  decision: {
    overall_decision: string;
    market_regime: string;
    cash_action: string;
    highest_priority_buy?: string;
    highest_priority_sell?: string;
    highest_priority_reduce?: string;
    highest_priority_increase?: string;
    top_10_opportunities?: Array<{
      ticker: string;
      score: number;
      sector: string;
      expected_return: string;
    }>;
    capital_rotation_plan?: RotationPlanItem[];
    reasoning?: string;
  };
}

interface OpportunityCenterProps {
  apiBase: string;
  onShowToast: (msg: string, isError?: boolean) => void;
}

export default function OpportunityCenter({ apiBase, onShowToast }: OpportunityCenterProps) {
  const [data, setData] = useState<RotationState | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [selectedStock, setSelectedStock] = useState<OpportunityStock | null>(null);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      const res = await fetch(`${apiBase}/api/portfolio/rotation`);
      const rotationData = await res.json();
      setData(rotationData);
      
      // Default select top stock
      if (rotationData.opportunity_universe && rotationData.opportunity_universe.length > 0) {
        setSelectedStock(rotationData.opportunity_universe[0]);
      }
    } catch (e) {
      console.error(e);
      onShowToast("Failed to retrieve Opportunity Center analytics.", true);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (isLoading || !data) {
    return (
      <div className="empty-state" style={{ height: '350px' }}>
        <div className="skeleton-line" style={{ width: '200px', height: '2rem', marginBottom: '1.25rem' }}></div>
        <div className="skeleton-line" style={{ height: '260px' }}></div>
      </div>
    );
  }

  // Sizing and cash allocations
  const cash = data.portfolio.cash_available;
  let holdingsValue = 0;
  data.portfolio.holdings.forEach(h => {
    const qty = h.quantity;
    const price = h.last_price;
    holdingsValue += qty * price;
  });
  const portfolioValue = cash + holdingsValue;
  const cashPct = portfolioValue > 0 ? (cash / portfolioValue) * 100.0 : 0.0;

  // Rotation lists
  const rotationPlan = data.decision.capital_rotation_plan || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', width: '100%', paddingBottom: '3.5rem' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Layers className="text-bullish" /> Opportunity Ranking & Rotation
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
            Continuous comparison of active portfolio holdings against the Halal Universe for optimal capital deployment.
          </p>
        </div>
        <button className="flat-btn" onClick={fetchData} style={{ height: '36px' }}>
          <RotateCcw size={14} /> Refresh Universe
        </button>
      </div>

      {/* Grid: Overview Summary Banners */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem' }}>
        <div className="card-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Overall Committee Decision</span>
          <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--success)' }}>
            {data.decision.overall_decision}
          </div>
        </div>
        <div className="card-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Market Regime Status</span>
          <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--info)' }}>
            {data.decision.market_regime}
          </div>
        </div>
        <div className="card-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Highest Priority Buy</span>
          <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--text-primary)' }}>
            {data.decision.highest_priority_buy || "None"}
          </div>
        </div>
        <div className="card-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Highest Priority Sell</span>
          <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--danger)' }}>
            {data.decision.highest_priority_sell || "None"}
          </div>
        </div>
      </div>

      {/* Main Content Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '3fr 2fr', gap: '1.5rem' }}>
        
        {/* Left Side: Universe Opportunity Scoring */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Top Opportunities List */}
          <div className="card-panel">
            <h3 className="section-title" style={{ marginBottom: '1rem' }}>Scored Halal Universe Rankings</h3>
            
            <div className="table-responsive">
              <table className="orders-table">
                <thead>
                  <tr>
                    <th>Ticker</th>
                    <th>Sector</th>
                    <th style={{ textAlign: 'center' }}>Score</th>
                    <th>Expected Return</th>
                    <th>Volatility Risk</th>
                    <th>Holding Period</th>
                  </tr>
                </thead>
                <tbody>
                  {data.opportunity_universe.map((stock, idx) => (
                    <tr 
                      key={idx} 
                      onClick={() => setSelectedStock(stock)}
                      style={{ 
                        cursor: 'pointer',
                        background: selectedStock?.ticker === stock.ticker ? 'rgba(255,255,255,0.02)' : 'transparent',
                        borderLeft: selectedStock?.ticker === stock.ticker ? '3px solid var(--info)' : '3px solid transparent'
                      }}
                    >
                      <td>
                        <div style={{ fontWeight: 800 }}>{stock.ticker}</div>
                        <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)' }}>{stock.company}</div>
                      </td>
                      <td>{stock.sector}</td>
                      <td style={{ textAlign: 'center', fontWeight: 800, color: 'var(--info)' }}>
                        {stock.opportunity_score}
                      </td>
                      <td className="text-bullish">{stock.expected_return}</td>
                      <td>
                        <span className={`badge ${stock.risk_rating === 'Low' ? 'badge-success' : stock.risk_rating === 'Medium' ? 'badge-warning' : 'badge-danger'}`} style={{ fontSize: '0.6rem' }}>
                          {stock.risk_rating}
                        </span>
                      </td>
                      <td>{stock.expected_holding_period}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Capital Rotation Plan Panel */}
          <div className="card-panel">
            <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '1.25rem' }}>
              <ArrowRightLeft size={16} className="text-bullish" /> Capital Rotation Plan
            </h3>
            
            {rotationPlan.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                {rotationPlan.map((plan, idx) => (
                  <div 
                    key={idx} 
                    style={{ 
                      padding: '0.85rem', 
                      background: 'rgba(255,255,255,0.01)', 
                      border: '1px solid var(--border-color)', 
                      borderRadius: '6px', 
                      display: 'flex', 
                      flexDirection: 'column', 
                      gap: '0.5rem' 
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.85rem', fontWeight: 800 }}>
                        <span style={{ color: 'var(--danger)' }}>Exit {plan.sell_ticker}</span>
                        <ArrowRightLeft size={14} className="text-muted" />
                        <span style={{ color: 'var(--success)' }}>Buy {plan.buy_ticker}</span>
                      </div>
                      <span className="badge badge-success">₹{plan.amount.toLocaleString('en-IN')} Suggested</span>
                    </div>
                    <p style={{ margin: 0, fontSize: '0.74rem', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                      <strong>Justification:</strong> {plan.justification}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.8rem', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', borderRadius: '6px' }}>
                ✅ Current holdings outperform the universe opportunities. No rotations needed today.
              </div>
            )}
          </div>

        </div>

        {/* Right Side: Details & Allocation Checks */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Selected Opportunity Details */}
          {selectedStock && (
            <div className="card-panel">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem' }}>
                <div>
                  <h3 className="section-title" style={{ fontSize: '1.15rem' }}>{selectedStock.ticker} Details</h3>
                  <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{selectedStock.company}</span>
                </div>
                <div style={{ background: 'var(--border-color)', padding: '0.4rem 0.75rem', borderRadius: '4px', textAlign: 'center' }}>
                  <span style={{ fontSize: '0.6rem', color: 'var(--text-secondary)', display: 'block' }}>OPP SCORE</span>
                  <strong style={{ fontSize: '1.2rem', color: 'var(--info)' }}>{selectedStock.opportunity_score}</strong>
                </div>
              </div>

              {/* Progress bars of components */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', marginBottom: '1.5rem' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem' }}>
                    <span>Technicals & Momentum</span>
                    <strong>{selectedStock.technical_score}/100</strong>
                  </div>
                  <div style={{ height: '6px', background: 'var(--border-color)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${selectedStock.technical_score}%`, background: 'var(--success)' }}></div>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem' }}>
                    <span>Trend Strength</span>
                    <strong>{selectedStock.trend_score}/100</strong>
                  </div>
                  <div style={{ height: '6px', background: 'var(--border-color)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${selectedStock.trend_score}%`, background: 'var(--info)' }}></div>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem' }}>
                    <span>Volume Confirmation</span>
                    <strong>{selectedStock.volume_score}/100</strong>
                  </div>
                  <div style={{ height: '6px', background: 'var(--border-color)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${selectedStock.volume_score}%`, background: 'var(--warning)' }}></div>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem' }}>
                    <span>Risk-adjusted Safety</span>
                    <strong>{selectedStock.risk_score}/100</strong>
                  </div>
                  <div style={{ height: '6px', background: 'var(--border-color)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ height: '100%', width: `${selectedStock.risk_score}%`, background: 'var(--success)' }}></div>
                  </div>
                </div>
              </div>

              {/* Dynamic Position Sizing Info (Task 4) */}
              <div style={{ padding: '0.75rem', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', borderRadius: '6px' }}>
                <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.75rem', fontWeight: 800, color: 'var(--info)' }}>
                  Dynamic Position Sizing (Task 4)
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Max Capital Cap:</span>
                    <strong>₹{(data.sizing_matrix[selectedStock.ticker]?.max_capital_allocation || 20000).toLocaleString('en-IN')}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Suggested Cash Reserve:</span>
                    <strong>₹{(data.sizing_matrix[selectedStock.ticker]?.suggested_cash_reserve || 15000).toLocaleString('en-IN')}</strong>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Max suggested Qty:</span>
                    <strong>{data.sizing_matrix[selectedStock.ticker]?.max_suggested_qty || 250} shares</strong>
                  </div>
                </div>
              </div>

            </div>
          )}

          {/* Risk Heatmap (Color-coded assets) */}
          <div className="card-panel">
            <h3 className="section-title" style={{ marginBottom: '1rem' }}>Active Exposure Risk Heatmap</h3>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {data.portfolio.holdings.length > 0 ? data.portfolio.holdings.map((h, idx) => {
                const ticker = h.ticker || h.tradingsymbol || "Unknown";
                const pnl = h.pnl;
                const isBullish = pnl >= 0;
                
                return (
                  <div 
                    key={idx} 
                    style={{ 
                      padding: '0.65rem', 
                      background: isBullish ? 'rgba(34,197,94,0.04)' : 'rgba(239,68,68,0.04)', 
                      border: isBullish ? '1px solid rgba(34,197,94,0.15)' : '1px solid rgba(239,68,68,0.15)', 
                      borderRadius: '6px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      fontSize: '0.75rem'
                    }}
                  >
                    <div>
                      <strong>{ticker}</strong>
                      <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginLeft: '0.5rem' }}>
                        Qty: {h.quantity}
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontWeight: 800, color: isBullish ? 'var(--success)' : 'var(--danger)' }}>
                      {isBullish ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                      ₹{pnl.toLocaleString('en-IN', { maximumFractionDigits: 2 })}
                    </div>
                  </div>
                );
              }) : (
                <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontStyle: 'italic', padding: '0.5rem' }}>
                  No open positions to calculate risk exposure.
                </div>
              )}
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}
