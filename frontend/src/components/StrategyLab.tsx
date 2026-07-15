import React, { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, HelpCircle, Activity, ShieldAlert, Award, RotateCw, Play, Calendar, DollarSign } from 'lucide-react';

interface StrategyLabProps {
  activeStocks: any[];
  apiBase: string;
}

export default function StrategyLab({ activeStocks, apiBase }: StrategyLabProps) {
  const [selectedTicker, setSelectedTicker] = useState('GREENPOWER');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);
  const [selectedStrategyIdx, setSelectedStrategyIdx] = useState(0);

  const runBacktest = () => {
    setLoading(true);
    fetch(`${apiBase}/backtest?ticker=${selectedTicker}`)
      .then(res => res.json())
      .then(resData => {
        if (resData.status === 'success') {
          setData(resData);
        }
        setLoading(false);
      })
      .catch(err => {
        console.error("Backtest failed:", err);
        setLoading(false);
      });
  };

  useEffect(() => {
    runBacktest();
  }, [selectedTicker]);

  const strategies = data?.strategies || [];
  const comparison = data?.comparison || {
    best_strategy: 'N/A',
    worst_strategy: 'N/A',
    confidence: 'Medium',
    risk: 'Moderate',
    market_suitability: 'Trending conditions',
    reasoning: 'Run calculations to compare strategies.'
  };

  const selectedStrat = strategies[selectedStrategyIdx] || null;
  const metrics = selectedStrat?.metrics || {};
  const mc = selectedStrat?.monte_carlo || {};
  const trades = selectedStrat?.trades || [];
  const equityCurve = metrics.equity_curve || [];

  // Generate SVG coordinates for equity curve
  const getSvgPoints = () => {
    if (equityCurve.length < 2) return "";
    const values = equityCurve.map((d: any) => d.value);
    const minVal = Math.min(...values);
    const maxVal = Math.max(...values);
    const range = maxVal - minVal || 1.0;
    
    const width = 500;
    const height = 150;
    
    return equityCurve.map((d: any, idx: number) => {
      const x = (idx / (equityCurve.length - 1)) * width;
      const y = height - ((d.value - minVal) / range) * (height - 20) - 10;
      return `${x},${y}`;
    }).join(" ");
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', width: '100%' }}>
      {/* Settings bar */}
      <div className="card-panel" style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', padding: '1rem 1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Select Asset Ticker:</span>
          <select 
            value={selectedTicker}
            onChange={(e) => setSelectedTicker(e.target.value)}
            style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)', color: 'var(--text-primary)', padding: '0.35rem 0.75rem', borderRadius: '4px', outline: 'none', fontSize: '0.8rem', fontWeight: 600 }}
          >
            <option value="GREENPOWER">GREENPOWER</option>
            <option value="BEL">BEL</option>
            <option value="RELIANCE">RELIANCE</option>
            <option value="TCS">TCS</option>
            <option value="INFY">INFY</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {data && (
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
              <Calendar size={11} style={{ display: 'inline', marginRight: '0.2rem' }} /> Date Range: {data.date_range.start} to {data.date_range.end} ({data.data_points} trading days)
            </span>
          )}
          <button 
            onClick={runBacktest} 
            disabled={loading}
            className="flat-btn" 
            style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', height: '32px', padding: '0 0.85rem' }}
          >
            <Play size={12} fill="currentColor" /> {loading ? 'Computing...' : 'Run Backtest'}
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '300px', gap: '1rem', color: 'var(--text-secondary)' }}>
          <div style={{ width: '40px', height: '40px', border: '3px solid rgba(255,255,255,0.05)', borderTopColor: 'var(--info)', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
          <span style={{ fontSize: '0.85rem' }}>Running 6 technical backtest models & Monte Carlo simulations...</span>
        </div>
      ) : (
        <>
          {/* AI Comparison Analysis */}
          <div className="card-panel" style={{ borderLeft: '4px solid var(--info)' }}>
            <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Award size={16} className="text-info" /> AI Strategy Lab Recommendation
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.5', margin: '0 0 1rem 0' }}>
              {comparison.reasoning}
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem', fontSize: '0.78rem' }}>
              <div>Best Strategy: <span className="text-bullish" style={{ fontWeight: 700 }}>{comparison.best_strategy}</span></div>
              <div>Worst Strategy: <span className="text-bearish" style={{ fontWeight: 700 }}>{comparison.worst_strategy}</span></div>
              <div>Confidence: <strong>{comparison.confidence}</strong></div>
              <div>Tail Risks: <strong>{comparison.risk}</strong></div>
              <div>Suitability: <strong>{comparison.market_suitability}</strong></div>
            </div>
          </div>

          {/* Strategy Leaderboard */}
          <div className="card-panel" style={{ padding: '1rem' }}>
            <h3 className="section-title" style={{ fontSize: '0.82rem', marginBottom: '0.75rem' }}><BarChart3 size={14} /> Backtest Leaderboard (5-Year Historicals)</h3>
            <div className="table-container">
              <table className="premium-table">
                <thead>
                  <tr>
                    <th>Strategy</th>
                    <th>Total Return</th>
                    <th>CAGR</th>
                    <th>Win Rate</th>
                    <th>Max DD</th>
                    <th>Sharpe</th>
                    <th>Expectancy</th>
                    <th>Trades</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {strategies.map((strat: any, idx: number) => (
                    <tr key={strat.strategy} style={{ background: selectedStrategyIdx === idx ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                      <td style={{ fontWeight: 600 }}>{strat.strategy}</td>
                      <td className={strat.metrics.total_return >= 0 ? 'text-bullish' : 'text-bearish'} style={{ fontWeight: 700 }}>
                        {strat.metrics.total_return >= 0 ? '+' : ''}{strat.metrics.total_return}%
                      </td>
                      <td>{strat.metrics.annual_return}%</td>
                      <td>{strat.metrics.win_rate}%</td>
                      <td className="text-bearish">{strat.metrics.max_drawdown}%</td>
                      <td>{strat.metrics.sharpe_ratio}</td>
                      <td>{strat.metrics.expectancy}%</td>
                      <td>{strat.metrics.trades_count}</td>
                      <td>
                        <button 
                          onClick={() => setSelectedStrategyIdx(idx)}
                          className="flat-btn flat-btn-outline" 
                          style={{ height: '24px', padding: '0 0.5rem', fontSize: '0.68rem' }}
                        >
                          Select
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {selectedStrat && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.25rem' }}>
              
              {/* Left Column: Equity curve and Monte Carlo */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                
                {/* Equity Curve */}
                <div className="card-panel" style={{ padding: '1.25rem' }}>
                  <h3 className="section-title" style={{ fontSize: '0.8rem', marginBottom: '0.75rem' }}><TrendingUp size={14} /> Equity Curve: {selectedStrat.strategy}</h3>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                    <span>Initial: ₹100,000.00</span>
                    <span>Ending: <strong>₹{equityCurve[equityCurve.length - 1]?.value.toLocaleString()}</strong></span>
                  </div>
                  
                  {equityCurve.length >= 2 ? (
                    <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)', borderRadius: '4px', overflow: 'hidden' }}>
                      <svg width="100%" height="150" viewBox="0 0 500 150" preserveAspectRatio="none">
                        <polyline
                          fill="none"
                          stroke="var(--info)"
                          strokeWidth="2.5"
                          points={getSvgPoints()}
                        />
                      </svg>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '150px', background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)', borderRadius: '4px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      No equity curve data available.
                    </div>
                  )}
                </div>

                {/* Monte Carlo Results */}
                <div className="card-panel" style={{ padding: '1.25rem' }}>
                  <h3 className="section-title" style={{ fontSize: '0.8rem', marginBottom: '0.75rem' }}><Activity size={14} /> Monte Carlo Simulations (1000 Runs)</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.78rem' }}>
                    
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '0.4rem' }}>
                      <span>Probability of Profit (PoP)</span>
                      <strong className="text-bullish" style={{ fontSize: '0.85rem' }}>{mc.probability_of_profit}%</strong>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '0.4rem' }}>
                      <span>Worst Case Simulated Drawdown</span>
                      <strong className="text-bearish">{mc.worst_case_drawdown}%</strong>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(255,255,255,0.03)', paddingBottom: '0.4rem' }}>
                      <span>Expected Value Range (10%-90%)</span>
                      <strong>₹{mc.expected_return_range?.[0]?.toLocaleString()} - ₹{mc.expected_return_range?.[1]?.toLocaleString()}</strong>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Risk of Ruin (Equity &lt; 20%)</span>
                      <strong className={mc.risk_of_ruin > 5.0 ? 'text-bearish' : 'text-bullish'}>{mc.risk_of_ruin}%</strong>
                    </div>
                    
                  </div>
                </div>

              </div>

              {/* Right Column: Recent Trade Log */}
              <div className="card-panel" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column' }}>
                <h3 className="section-title" style={{ fontSize: '0.8rem', marginBottom: '0.75rem' }}><DollarSign size={14} /> Strategy Trade Log</h3>
                <div style={{ flex: 1, overflowY: 'auto', maxHeight: '330px' }}>
                  {trades.length > 0 ? (
                    <div className="table-container">
                      <table className="premium-table" style={{ fontSize: '0.72rem' }}>
                        <thead>
                          <tr>
                            <th>Entry</th>
                            <th>Exit</th>
                            <th>Buy</th>
                            <th>Sell</th>
                            <th>Return</th>
                          </tr>
                        </thead>
                        <tbody>
                          {trades.slice().reverse().map((t: any, idx: number) => {
                            const isWin = t.profit_loss_pct > 0;
                            return (
                              <tr key={idx}>
                                <td>{t.buy_date}</td>
                                <td>{t.sell_date}</td>
                                <td>₹{t.buy_price}</td>
                                <td>₹{t.sell_price}</td>
                                <td className={isWin ? 'text-bullish' : 'text-bearish'} style={{ fontWeight: 700 }}>
                                  {isWin ? '+' : ''}{(t.profit_loss_pct * 100).toFixed(2)}%
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', minHeight: '200px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      No executed trades recorded.
                    </div>
                  )}
                </div>
              </div>

            </div>
          )}
        </>
      )}
      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
