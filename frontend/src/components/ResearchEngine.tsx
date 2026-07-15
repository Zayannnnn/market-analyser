import React, { useState, useEffect } from 'react';
import { Search, TrendingUp, AlertTriangle, CheckCircle, BarChart2, ShieldAlert, Award, FileText, Info, BookOpen, Globe, Brain } from 'lucide-react';

interface ResearchData {
  ticker: string;
  company_name: string;
  fundamental_analysis: {
    revenue_growth_yoy: number;
    profit_growth_yoy: number;
    roe: number;
    roce: number;
    debt_to_equity: number;
    operating_margin: number;
    net_margin: number;
    free_cash_flow_cr: number;
    promoter_holding: number;
    fii_holding: number;
    dii_holding: number;
    pe_ratio: number;
    peg_ratio: number;
    pb_ratio: number;
    dividend_yield: number;
    fundamental_score: number;
  };
  earnings_performance: {
    latest_quarter: string;
    quarterly_revenue_cr: number;
    quarterly_profit_cr: number;
    revenue_surprise_pct: number;
    earnings_surprise_pct: number;
    margin_expansion_bps: number;
    guidance: string;
    conf_call_sentiment: 'Positive' | 'Neutral' | 'Negative';
    overall_earnings_view: 'Positive' | 'Neutral' | 'Negative';
  };
  news_intelligence: Array<{
    category: string;
    headline: string;
    importance: 'HIGH' | 'MEDIUM' | 'LOW';
    sentiment: 'BULLISH' | 'NEUTRAL' | 'BEARISH';
    confidence: number;
    expected_duration: string;
  }>;
  catalyst_analysis: Array<{
    type: string;
    description: string;
    impact: 'HIGH' | 'MEDIUM' | 'LOW';
  }>;
  fair_value_valuation: {
    intrinsic_value: number;
    current_price: number;
    upside_pct: number;
    margin_of_safety: number;
    valuation_grade: 'UNDERVALUED' | 'FAIR' | 'OVERVALUED';
  };
  investment_memo: {
    business_summary: string;
    competitive_advantages: string;
    key_risks: string;
    growth_drivers: string;
    technical_view: string;
    macro_view: string;
    ai_recommendation: 'BUY' | 'HOLD' | 'SELL' | 'WAIT' | 'AVOID';
    confidence_score: number;
  };
  updated_at_str?: string;
}

interface ResearchEngineProps {
  activeStocks: any[];
  apiBase?: string;
}

export default function ResearchEngine({ activeStocks, apiBase }: ResearchEngineProps) {
  const [selectedTicker, setSelectedTicker] = useState<string>('BEL');
  const [research, setResearch] = useState<ResearchData | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState<boolean>(false);

  const fetchResearch = async (ticker: string, forceRefresh = false) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase || ''}/api/stocks/${ticker}/research?refresh=${forceRefresh}`);
      if (res.ok) {
        const payload = await res.json();
        if (payload.status === 'success' && payload.research) {
          setResearch(payload.research);
        } else {
          setError(payload.message || 'Failed to fetch research memo.');
        }
      } else {
        setError('Server responded with an error while compiling research.');
      }
    } catch (e: any) {
      setError(e.message || 'Network error communicating with Research API.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResearch(selectedTicker);
  }, [selectedTicker]);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchResearch(selectedTicker, true);
    setRefreshing(false);
  };

  const stockRef = activeStocks.find(s => s.ticker === selectedTicker);
  const shariahCompliant = stockRef?.shariah_status === 'Halal' || stockRef?.shariah_status === 'Compliant';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', width: '100%' }}>
      {/* Search Header Panel */}
      <div className="card-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem', background: 'linear-gradient(135deg, rgba(21, 23, 30, 0.95) 0%, rgba(27, 30, 40, 0.98) 100%)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '42px',
            height: '42px',
            borderRadius: '50%',
            backgroundColor: 'rgba(59, 130, 246, 0.1)'
          }}>
            <Award size={22} className="text-bullish" />
          </div>
          <div>
            <h2 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 800 }}>Institutional Research Engine</h2>
            <p style={{ margin: '0.15rem 0 0 0', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              Quantitative valuations, consensus catalysts logs, and AI equity memos
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ position: 'relative' }}>
            <select
              value={selectedTicker}
              onChange={(e) => setSelectedTicker(e.target.value)}
              className="flat-input"
              style={{
                padding: '0.4rem 2rem 0.4rem 0.75rem',
                fontSize: '0.85rem',
                fontWeight: 700,
                cursor: 'pointer',
                appearance: 'none',
                minWidth: '140px',
                textAlign: 'left'
              }}
            >
              {activeStocks.filter(s => s.ticker !== '^NSEI' && s.ticker !== '^NSEBANK').map(stock => (
                <option key={stock.ticker} value={stock.ticker}>
                  {stock.ticker} - {stock.company_name}
                </option>
              ))}
            </select>
            <div style={{
              position: 'absolute',
              right: '0.75rem',
              top: '50%',
              transform: 'translateY(-50%)',
              pointerEvents: 'none',
              fontSize: '0.65rem',
              color: 'var(--text-secondary)'
            }}>▼</div>
          </div>

          <button
            className="flat-btn"
            disabled={loading || refreshing}
            onClick={handleRefresh}
            style={{
              height: '32px',
              padding: '0 0.85rem',
              fontSize: '0.78rem',
              fontWeight: 600,
              backgroundColor: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-primary)'
            }}
          >
            {refreshing ? 'Researching...' : 'Force Refresh'}
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '240px',
          backgroundColor: 'rgba(21, 23, 30, 0.4)',
          borderRadius: '8px',
          border: '1px solid var(--border-color)',
          gap: '1rem'
        }}>
          <div className="pulse-dot" style={{ width: '16px', height: '16px' }}></div>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>Compiling fundamental metrics and scanning catalyst calendars...</p>
        </div>
      ) : error ? (
        <div className="card-panel" style={{ textAlign: 'center', padding: '2rem', border: '1px solid var(--danger-border)' }}>
          <ShieldAlert size={40} style={{ color: 'var(--danger)', margin: '0 auto 0.75rem' }} />
          <h3 style={{ fontSize: '1rem', fontWeight: 700 }}>Research Retrieval Stalled</h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>{error}</p>
        </div>
      ) : research ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Executive Valuation & Compliance banner */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: '1rem'
          }}>
            {/* Intrinsic value dial */}
            <div className="card-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.01)' }}>
              <div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>VALUATION GRADE</div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.4rem', marginTop: '0.25rem' }}>
                  <span style={{ fontSize: '1.4rem', fontWeight: 800 }}>
                    {research.fair_value_valuation.valuation_grade}
                  </span>
                  <span className={research.fair_value_valuation.upside_pct >= 0 ? 'text-bullish' : 'text-bearish'} style={{ fontSize: '0.85rem', fontWeight: 700 }}>
                    ({research.fair_value_valuation.upside_pct >= 0 ? '+' : ''}{research.fair_value_valuation.upside_pct}%)
                  </span>
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>INTRINSIC VALUE</div>
                <div style={{ fontSize: '1.15rem', fontWeight: 700, marginTop: '0.25rem' }}>
                  ₹{research.fair_value_valuation.intrinsic_value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </div>
              </div>
            </div>

            {/* Fundamental Composite Score */}
            <div className="card-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.01)' }}>
              <div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>FUNDAMENTAL HEALTH</div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.4rem', marginTop: '0.25rem' }}>
                  <span style={{ fontSize: '1.4rem', fontWeight: 800 }}>{research.fundamental_analysis.fundamental_score}/100</span>
                </div>
              </div>
              <span className={`badge ${research.fundamental_analysis.fundamental_score >= 75 ? 'badge-success' : research.fundamental_analysis.fundamental_score >= 50 ? 'badge-warning' : 'badge-danger'}`} style={{ fontSize: '0.75rem', padding: '0.25rem 0.5rem' }}>
                {research.fundamental_analysis.fundamental_score >= 75 ? 'EXCELLENT' : research.fundamental_analysis.fundamental_score >= 50 ? 'STABLE' : 'RISKY'}
              </span>
            </div>

            {/* Shariah compliance badge */}
            <div className="card-panel" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.01)' }}>
              <div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>SHARIAH COMPLIANCE STATUS</div>
                <div style={{ fontSize: '1.1rem', fontWeight: 800, marginTop: '0.25rem', color: shariahCompliant ? 'var(--success)' : 'var(--danger)' }}>
                  {shariahCompliant ? 'SHARIAH COMPLIANT' : 'NON-COMPLIANT'}
                </div>
              </div>
              <span style={{ fontSize: '1.5rem' }}>
                {shariahCompliant ? '🟢' : '🔴'}
              </span>
            </div>
          </div>

          {/* Ratios and Fundamentals Matrix */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '2fr 1fr',
            gap: '1.5rem',
            alignItems: 'stretch'
          }}>
            {/* Ratios Table */}
            <div className="card-panel">
              <h3 className="section-title" style={{ margin: '0 0 1rem 0' }}><BarChart2 size={15} /> Institutional Ratios & Health metrics</h3>
              <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '1.25rem'
              }}>
                <div>
                  <h4 style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', borderBottom: '1px solid rgba(255, 255, 255, 0.05)', paddingBottom: '0.25rem', marginBottom: '0.5rem' }}>Efficiency & Growth</h4>
                  <table style={{ width: '100%', fontSize: '0.78rem', borderCollapse: 'collapse' }}>
                    <tbody>
                      <tr style={{ height: '26px' }}>
                        <td style={{ color: 'var(--text-secondary)' }}>Revenue Growth (YoY)</td>
                        <td style={{ textAlign: 'right', fontWeight: 600 }} className="text-bullish">+{research.fundamental_analysis.revenue_growth_yoy}%</td>
                      </tr>
                      <tr style={{ height: '26px' }}>
                        <td style={{ color: 'var(--text-secondary)' }}>Profit Growth (YoY)</td>
                        <td style={{ textAlign: 'right', fontWeight: 600 }} className="text-bullish">+{research.fundamental_analysis.profit_growth_yoy}%</td>
                      </tr>
                      <tr style={{ height: '26px' }}>
                        <td style={{ color: 'var(--text-secondary)' }}>ROE</td>
                        <td style={{ textAlign: 'right', fontWeight: 600 }}>{research.fundamental_analysis.roe}%</td>
                      </tr>
                      <tr style={{ height: '26px' }}>
                        <td style={{ color: 'var(--text-secondary)' }}>ROCE</td>
                        <td style={{ textAlign: 'right', fontWeight: 600 }}>{research.fundamental_analysis.roce}%</td>
                      </tr>
                      <tr style={{ height: '26px' }}>
                        <td style={{ color: 'var(--text-secondary)' }}>Free Cash Flow (FCF)</td>
                        <td style={{ textAlign: 'right', fontWeight: 600 }}>₹{research.fundamental_analysis.free_cash_flow_cr} Cr</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div>
                  <h4 style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', borderBottom: '1px solid rgba(255, 255, 255, 0.05)', paddingBottom: '0.25rem', marginBottom: '0.5rem' }}>Margins & Valuation Ratios</h4>
                  <table style={{ width: '100%', fontSize: '0.78rem', borderCollapse: 'collapse' }}>
                    <tbody>
                      <tr style={{ height: '26px' }}>
                        <td style={{ color: 'var(--text-secondary)' }}>PE Ratio</td>
                        <td style={{ textAlign: 'right', fontWeight: 600 }}>{research.fundamental_analysis.pe_ratio}x</td>
                      </tr>
                      <tr style={{ height: '26px' }}>
                        <td style={{ color: 'var(--text-secondary)' }}>PEG Ratio</td>
                        <td style={{ textAlign: 'right', fontWeight: 600 }}>{research.fundamental_analysis.peg_ratio}x</td>
                      </tr>
                      <tr style={{ height: '26px' }}>
                        <td style={{ color: 'var(--text-secondary)' }}>Debt / Equity</td>
                        <td style={{ textAlign: 'right', fontWeight: 600 }}>{research.fundamental_analysis.debt_to_equity}</td>
                      </tr>
                      <tr style={{ height: '26px' }}>
                        <td style={{ color: 'var(--text-secondary)' }}>Operating Margin</td>
                        <td style={{ textAlign: 'right', fontWeight: 600 }}>{research.fundamental_analysis.operating_margin}%</td>
                      </tr>
                      <tr style={{ height: '26px' }}>
                        <td style={{ color: 'var(--text-secondary)' }}>Dividend Yield</td>
                        <td style={{ textAlign: 'right', fontWeight: 600 }}>{research.fundamental_analysis.dividend_yield}%</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* Ownership Shareholdings Card */}
            <div className="card-panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
              <h3 className="section-title" style={{ margin: '0 0 0.75rem 0' }}><TrendingUp size={14} /> Ownership Shares</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>
                    <span>Promoter</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{research.fundamental_analysis.promoter_holding}%</span>
                  </div>
                  <div style={{ height: '6px', backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ width: `${research.fundamental_analysis.promoter_holding}%`, height: '100%', backgroundColor: 'var(--success)' }}></div>
                  </div>
                </div>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>
                    <span>FII (Foreign Institutional)</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{research.fundamental_analysis.fii_holding}%</span>
                  </div>
                  <div style={{ height: '6px', backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ width: `${research.fundamental_analysis.fii_holding}%`, height: '100%', backgroundColor: 'var(--primary)' }}></div>
                  </div>
                </div>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>
                    <span>DII (Domestic Institutional)</span>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{research.fundamental_analysis.dii_holding}%</span>
                  </div>
                  <div style={{ height: '6px', backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ width: `${research.fundamental_analysis.dii_holding}%`, height: '100%', backgroundColor: 'var(--text-secondary)' }}></div>
                  </div>
                </div>
              </div>
              <div style={{ borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '0.5rem', marginTop: '0.5rem', fontSize: '0.68rem', color: 'var(--text-secondary)', textAlign: 'center' }}>
                Institutional ownership: {(research.fundamental_analysis.fii_holding + research.fundamental_analysis.dii_holding).toFixed(1)}%
              </div>
            </div>
          </div>

          {/* Earnings performance tracker */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '1.5rem'
          }}>
            {/* Earnings surprise details */}
            <div className="card-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              <h3 className="section-title" style={{ margin: 0 }}><CheckCircle size={14} /> Earnings Performance ({research.earnings_performance.latest_quarter})</h3>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                <div style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.02)', borderRadius: '4px' }}>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>Revenue Surprise</div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 700, marginTop: '0.15rem', color: research.earnings_performance.revenue_surprise_pct >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                    {research.earnings_performance.revenue_surprise_pct >= 0 ? '+' : ''}{research.earnings_performance.revenue_surprise_pct}%
                  </div>
                </div>
                <div style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.02)', borderRadius: '4px' }}>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>Earnings Surprise</div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 700, marginTop: '0.15rem', color: research.earnings_performance.earnings_surprise_pct >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                    {research.earnings_performance.earnings_surprise_pct >= 0 ? '+' : ''}{research.earnings_performance.earnings_surprise_pct}%
                  </div>
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Latest Quarterly Revenue & Profit</div>
                <div style={{ fontSize: '0.8rem', fontWeight: 600 }}>
                  Revenue: ₹{research.earnings_performance.quarterly_revenue_cr} Cr | Profit: ₹{research.earnings_performance.quarterly_profit_cr} Cr
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Management Guidance Outlook</div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-primary)', lineHeight: '1.4' }}>
                  {research.earnings_performance.guidance}
                </div>
              </div>
            </div>

            {/* Call sentiment and catalysts */}
            <div className="card-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              <h3 className="section-title" style={{ margin: 0 }}><TrendingUp size={14} /> Future Catalysts & Call Sentiments</h3>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                <div style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.02)', borderRadius: '4px' }}>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>Conf Call Sentiment</div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 700, marginTop: '0.15rem', color: research.earnings_performance.conf_call_sentiment === 'Positive' ? 'var(--success)' : 'var(--danger)' }}>
                    {research.earnings_performance.conf_call_sentiment}
                  </div>
                </div>
                <div style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.02)', borderRadius: '4px' }}>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>Earnings View</div>
                  <div style={{ fontSize: '0.9rem', fontWeight: 700, marginTop: '0.15rem', color: research.earnings_performance.overall_earnings_view === 'Positive' ? 'var(--success)' : 'var(--danger)' }}>
                    {research.earnings_performance.overall_earnings_view}
                  </div>
                </div>
              </div>

              <div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>Catalyst Schedule logs</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {research.catalyst_analysis.map((cat, idx) => (
                    <div key={idx} style={{ padding: '0.5rem', background: 'rgba(255,255,255,0.01)', borderLeft: '3px solid var(--primary)', borderRadius: '2px', fontSize: '0.72rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600, marginBottom: '0.15rem' }}>
                        <span>{cat.type}</span>
                        <span className={cat.impact === 'HIGH' ? 'text-bullish' : 'text-neutral'}>{cat.impact} IMPACT</span>
                      </div>
                      <span style={{ color: 'var(--text-secondary)' }}>{cat.description}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Investment Memo Document */}
          <div className="card-panel">
            <h3 className="section-title" style={{ margin: '0 0 1.25rem 0', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}><FileText size={16} /> AORA Institutional Equity Memo</h3>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div>
                <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--primary)', marginBottom: '0.4rem' }}>1. Executive Summary & Recommendation</h4>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', background: 'rgba(255,255,255,0.02)', padding: '0.75rem', borderRadius: '4px', marginBottom: '0.5rem' }}>
                  <div>
                    <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>DECISION</div>
                    <div className="text-bullish" style={{ fontSize: '1.2rem', fontWeight: 800 }}>{research.investment_memo.ai_recommendation}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>CONFIDENCE STRENGTH</div>
                    <div style={{ fontSize: '1.2rem', fontWeight: 800 }}>{research.investment_memo.confidence_score}%</div>
                  </div>
                  <div style={{ flex: 1, fontSize: '0.78rem', color: 'var(--text-secondary)', borderLeft: '1px solid rgba(255,255,255,0.08)', paddingLeft: '0.75rem' }}>
                    This thesis is generated by compiling local technical support lines, corporate cash returns, and real-time market regimes.
                  </div>
                </div>
                <p style={{ fontSize: '0.8rem', lineHeight: '1.5', color: 'var(--text-primary)', margin: 0 }}>{research.investment_memo.business_summary}</p>
              </div>

              <div>
                <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--primary)', marginBottom: '0.4rem' }}>2. Competitive Advantages (Economic Moat)</h4>
                <p style={{ fontSize: '0.8rem', lineHeight: '1.5', color: 'var(--text-primary)', margin: 0 }}>{research.investment_memo.competitive_advantages}</p>
              </div>

              <div>
                <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--primary)', marginBottom: '0.4rem' }}>3. Financial Growth Drivers</h4>
                <p style={{ fontSize: '0.8rem', lineHeight: '1.5', color: 'var(--text-primary)', margin: 0 }}>{research.investment_memo.growth_drivers}</p>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
                <div>
                  <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--danger)', marginBottom: '0.4rem' }}>4. Primary Investment Risks</h4>
                  <p style={{ fontSize: '0.8rem', lineHeight: '1.5', color: 'var(--text-primary)', margin: 0 }}>{research.investment_memo.key_risks}</p>
                </div>
                <div>
                  <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--primary)', marginBottom: '0.4rem' }}>5. Technical & Macro Alignment</h4>
                  <p style={{ fontSize: '0.8rem', lineHeight: '1.4', color: 'var(--text-primary)', margin: 0 }}>
                    <strong>Technicals:</strong> {research.investment_memo.technical_view}<br />
                    <strong style={{ display: 'inline-block', marginTop: '0.35rem' }}>Macro Regime:</strong> {research.investment_memo.macro_view}
                  </p>
                </div>
              </div>
            </div>
            
            <div style={{ borderTop: '1px solid var(--border-color)', marginTop: '1.5rem', paddingTop: '0.75rem', display: 'flex', justifyContent: 'space-between', fontSize: '0.68rem', color: 'var(--text-secondary)' }}>
              <span>Memo Compiled At: {research.updated_at_str || 'Recently'}</span>
              <span>Grounding Sources: Screener, Tickertape, Moneycontrol filings</span>
            </div>
          </div>

          {/* News Intelligence */}
          <div className="card-panel">
            <h3 className="section-title" style={{ margin: '0 0 1rem 0' }}><Info size={15} /> Real-time News Intelligence & Sentiment</h3>
            <div className="table-container">
              <table className="premium-table">
                <thead>
                  <tr>
                    <th>Category</th>
                    <th>Headline</th>
                    <th>Importance</th>
                    <th>Sentiment</th>
                    <th>Confidence</th>
                    <th>Duration</th>
                  </tr>
                </thead>
                <tbody>
                  {research.news_intelligence.map((news, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: 600 }}>{news.category}</td>
                      <td style={{ fontSize: '0.78rem', maxWidth: '350px', whiteSpace: 'normal', lineHeight: '1.4' }}>{news.headline}</td>
                      <td>
                        <span className={`badge ${news.importance === 'HIGH' ? 'badge-danger' : news.importance === 'MEDIUM' ? 'badge-warning' : 'badge-success'}`} style={{ fontSize: '0.65rem' }}>
                          {news.importance}
                        </span>
                      </td>
                      <td className={news.sentiment === 'BULLISH' ? 'text-bullish' : news.sentiment === 'BEARISH' ? 'text-bearish' : 'text-neutral'} style={{ fontWeight: 700 }}>
                        {news.sentiment}
                      </td>
                      <td>{news.confidence}%</td>
                      <td>{news.expected_duration}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      ) : (
        <div className="card-panel" style={{ textAlign: 'center', padding: '2rem' }}>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Select a stock to start research compilation.</p>
        </div>
      )}
    </div>
  );
}
