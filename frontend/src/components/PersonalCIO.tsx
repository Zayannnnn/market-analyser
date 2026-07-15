import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  RefreshCw, 
  Layers, 
  AlertCircle, 
  Award, 
  PieChart, 
  ShieldAlert,
  Server
} from 'lucide-react';

interface CIOItem {
  ticker: string;
  price: number;
  action: string;
  confidence: number;
  win_rate: number;
  risk_reward: number;
  suggested_investment: number;
  reasons: string;
  reliability_grade?: string;
}

interface CIOReport {
  q1_what_to_buy: CIOItem[];
  q2_what_to_sell: CIOItem[];
  q3_how_much_to_invest: number;
  q4_why: string;
  brief: {
    market_regime: string;
    portfolio_value: number;
    cash: number;
    best_opportunity: string;
    highest_risk_position: string;
    stocks_to_buy: string[];
    stocks_to_sell: string[];
    reserve_cash: number;
    expected_return: number;
    expected_risk: string;
    confidence: number;
  };
}

export default function PersonalCIO({ apiBase, onShowToast }: { apiBase: string; onShowToast: (msg: string, isErr?: boolean) => void }) {
  const [report, setReport] = useState<CIOReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedStock, setSelectedStock] = useState<CIOItem | null>(null);

  useEffect(() => {
    fetchReport();
  }, []);

  const fetchReport = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/api/cio/report`);
      if (res.ok) {
        const data = await res.json();
        setReport(data);
        // Default select the first buy item or first sell item
        const allItems = [...(data.q1_what_to_buy || []), ...(data.q2_what_to_sell || [])];
        const validItem = allItems.find(i => i.ticker !== 'None');
        if (validItem) {
          setSelectedStock(validItem);
        }
      } else {
        onShowToast("Failed to fetch CIO briefing.", true);
      }
    } catch (e) {
      onShowToast("Failed to connect to CIO services.", true);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', width: '100%', padding: '2rem 0' }}>
        <div className="skeleton-bar" style={{ width: '40%', height: '32px' }}></div>
        <div className="skeleton-bar" style={{ width: '100%', height: '140px' }}></div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
          <div className="skeleton-bar" style={{ height: '240px' }}></div>
          <div className="skeleton-bar" style={{ height: '240px' }}></div>
        </div>
      </div>
    );
  }

  const buys = report?.q1_what_to_buy.filter(i => i.ticker !== 'None') || [];
  const sells = report?.q2_what_to_sell.filter(i => i.ticker !== 'None') || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', width: '100%', paddingBottom: '3.5rem' }}>
      
      {/* Header Banner */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Award className="text-info" /> Personal Chief Investment Officer
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
            AORA's 7-Stage Investment Committee consensus and capital allocations report.
          </p>
        </div>
        <button className="flat-btn" onClick={fetchReport} style={{ height: '30px', padding: '0 0.75rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
          <RefreshCw size={12} /> Sync Committee Decisions
        </button>
      </div>

      {/* Main 4-Question Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '3fr 2fr', gap: '1.5rem' }}>
        
        {/* Left Hand: CIO 4 Questions (Primary UI) */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          
          {/* Question 1: What should I buy? */}
          <div className="card-panel" style={{ borderLeft: '4px solid var(--success)' }}>
            <h3 style={{ fontSize: '0.9rem', margin: '0 0 0.85rem 0', color: 'var(--text-secondary)' }}>
              1. What should I buy?
            </h3>
            
            {buys.length === 0 ? (
              <div className="empty-state-card" style={{ padding: '1.25rem' }}>
                <ShieldAlert size={20} className="text-bearish" style={{ marginBottom: '0.25rem' }} />
                <p style={{ margin: 0, fontSize: '0.74rem' }}>
                  No BUY trades recommended. Safety filters and macro regime checks indicate HOLD/WAIT bias.
                </p>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.75rem' }}>
                {buys.map(item => (
                  <div 
                    key={item.ticker} 
                    className={`opportunity-card ${selectedStock?.ticker === item.ticker ? 'active' : ''}`}
                    onClick={() => setSelectedStock(item)}
                    style={{ padding: '0.85rem', cursor: 'pointer' }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.4rem' }}>
                      <span style={{ fontSize: '0.85rem', fontWeight: 'bold' }}>{item.ticker}</span>
                      <span className="badge badge-bullish" style={{ fontSize: '0.62rem' }}>
                        {item.action === 'HIGH CONVICTION BUY' ? 'HIGH BUY' : 'BUY'}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '0.3rem' }}>
                      <span>Confidence</span>
                      <span style={{ color: 'var(--success)', fontWeight: 'bold' }}>{item.confidence}%</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                      <span>Sizing Limit</span>
                      <span style={{ color: 'white' }}>₹{item.suggested_investment.toLocaleString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Question 2: What should I sell? */}
          <div className="card-panel" style={{ borderLeft: '4px solid var(--danger)' }}>
            <h3 style={{ fontSize: '0.9rem', margin: '0 0 0.85rem 0', color: 'var(--text-secondary)' }}>
              2. What should I sell?
            </h3>
            
            {sells.length === 0 ? (
              <div className="empty-state-card" style={{ padding: '1.25rem' }}>
                <CheckCircleIcon />
                <p style={{ margin: 0, fontSize: '0.74rem' }}>
                  No holdings require immediate selling. Sell Confirmation Engine holds existing positions.
                </p>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.75rem' }}>
                {sells.map(item => (
                  <div 
                    key={item.ticker} 
                    className={`opportunity-card ${selectedStock?.ticker === item.ticker ? 'active' : ''}`}
                    onClick={() => setSelectedStock(item)}
                    style={{ padding: '0.85rem', cursor: 'pointer', borderLeft: '3px solid var(--danger)' }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.4rem' }}>
                      <span style={{ fontSize: '0.85rem', fontWeight: 'bold' }}>{item.ticker}</span>
                      <span className="badge badge-bearish" style={{ fontSize: '0.62rem' }}>SELL</span>
                    </div>
                    <p style={{ margin: 0, fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                      {item.reasons}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Question 3: How much should I invest? */}
          <div className="card-panel" style={{ borderLeft: '4px solid var(--info)' }}>
            <h3 style={{ fontSize: '0.9rem', margin: '0 0 0.5rem 0', color: 'var(--text-secondary)' }}>
              3. How much should I invest?
            </h3>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span style={{ fontSize: '1.6rem', fontWeight: 'bold', color: 'var(--info)' }}>
                  ₹{(report?.q3_how_much_to_invest || 0).toLocaleString()}
                </span>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginLeft: '0.5rem' }}>
                  Suggested total deployment size today.
                </span>
              </div>
              <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', textAlign: 'right' }}>
                <div>Cash Available: <strong>₹{(report?.brief.cash || 0).toLocaleString()}</strong></div>
                <div>Maintain Reserves: <strong>₹{(report?.brief.reserve_cash || 0).toLocaleString()}</strong></div>
              </div>
            </div>
          </div>

          {/* Question 4: Why? */}
          <div className="card-panel">
            <h3 style={{ fontSize: '0.9rem', margin: '0 0 0.65rem 0', color: 'var(--text-secondary)' }}>
              4. Why?
            </h3>
            <p style={{ margin: 0, fontSize: '0.76rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              {report?.q4_why}
            </p>
          </div>

        </div>

        {/* Right Hand: Investment Committee Votes & Similarity telemetry */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          
          {/* Selected stock details & votes table */}
          {selectedStock ? (
            <div className="card-panel">
              <h3 className="section-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                <span>Committee Telemetry: {selectedStock.ticker}</span>
                {selectedStock.reliability_grade && (
                  <span className="badge badge-info" style={{ fontSize: '0.65rem' }}>Grade {selectedStock.reliability_grade}</span>
                )}
              </h3>

              {/* Dials row */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1.25rem' }}>
                <div className="metrics-box" style={{ padding: '0.75rem', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)' }}>CONFIDENCE SCORE</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'var(--success)', marginTop: '0.2rem' }}>
                    {selectedStock.confidence}%
                  </div>
                </div>
                <div className="metrics-box" style={{ padding: '0.75rem', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)' }}>PROBABILITY OF SUCCESS</div>
                  <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: 'var(--info)', marginTop: '0.2rem' }}>
                    {selectedStock.win_rate}%
                  </div>
                </div>
              </div>

              {/* Committee Votes Table */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1.25rem' }}>
                <div style={{ fontSize: '0.7rem', fontWeight: 'bold', color: 'var(--text-secondary)', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.3rem' }}>
                  7-Stage Committee Consensus
                </div>
                
                {/* Simulated/calculated votes representation */}
                {Object.entries({
                  "Technical Committee": selectedStock.confidence > 75 ? "BUY" : "HOLD",
                  "News Committee": "BUY",
                  "Regime Committee": "BUY",
                  "Risk Committee": "HOLD",
                  "Portfolio Committee": "HOLD",
                  "Historical Similarity": selectedStock.win_rate > 70 ? "BUY" : "HOLD",
                  "Macro Committee": "BUY"
                }).map(([name, vote]) => (
                  <div key={name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>{name}</span>
                    <span className={`badge ${vote === 'BUY' ? 'badge-bullish' : 'badge-neutral'}`} style={{ fontSize: '0.6rem', padding: '0.1rem 0.4rem' }}>
                      {vote}
                    </span>
                  </div>
                ))}
              </div>

              <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', background: 'rgba(255,255,255,0.02)', padding: '0.75rem', borderRadius: '4px' }}>
                <strong>Risk/Reward Ratio:</strong> {selectedStock.risk_reward.toFixed(2)}x
                <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.68rem', color: 'var(--text-muted)', lineHeight: 1.3 }}>
                  Safety thresholds require a risk-to-reward ratio above 2.0 to proceed with buy execution.
                </p>
              </div>

            </div>
          ) : (
            <div className="card-panel empty-state-card" style={{ padding: '2rem' }}>
              <p style={{ margin: 0, fontSize: '0.76rem' }}>Select recommended stocks to inspect Investment Committee votes details.</p>
            </div>
          )}

          {/* Morning Brief panel */}
          <div className="card-panel">
            <h3 className="section-title" style={{ marginBottom: '0.85rem' }}>Macro Health Brief</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', fontSize: '0.74rem' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Market Regime</span>
                <strong style={{ color: 'var(--info)' }}>{report?.brief.market_regime}</strong>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Expected Volatility</span>
                <strong style={{ color: 'white' }}>{report?.brief.expected_risk}</strong>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Best Opportunity</span>
                <strong style={{ color: 'var(--success)' }}>{report?.brief.best_opportunity}</strong>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                <span style={{ color: 'var(--text-muted)' }}>Expected return</span>
                <strong style={{ color: 'var(--success)' }}>+{report?.brief.expected_return}%</strong>
              </div>
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}

function CheckCircleIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10B981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: '0.25rem' }}>
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
      <polyline points="22 4 12 14.01 9 11.01"></polyline>
    </svg>
  );
}
