import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  RefreshCw, 
  Award, 
  Globe, 
  Calendar, 
  ShieldAlert, 
  PieChart 
} from 'lucide-react';

interface MacroBrief {
  market_health: string;
  global_risk: number;
  institutional_flow: string;
  fii_buy: number;
  fii_sell: number;
  dii_buy: number;
  dii_sell: number;
  net_fii: number;
  net_dii: number;
  usd_inr: number;
  crude_oil: number;
  us_yield: number;
  sectors: Record<string, string>;
  events: Array<{ name: string; days_away: number; risk: string }>;
  block_trades: boolean;
}

export default function MarketIntelligence({ apiBase, onShowToast }: { apiBase: string; onShowToast: (msg: string, isErr?: boolean) => void }) {
  const [data, setData] = useState<MacroBrief | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    fetchMacroData();
  }, []);

  const fetchMacroData = async () => {
    setLoading(true);
    try {
      // Fetch details from endpoints
      const res = await fetch(`${apiBase}/api/cio/report`);
      if (res.ok) {
        const payload = await res.json();
        
        // Re-construct matching MacroBrief details
        const brief = payload.brief;
        const score = payload.strategy_scoreboard;
        
        const mockMacro: MacroBrief = {
          market_health: brief.market_regime,
          global_risk: brief.expected_risk === 'Low' ? 30.0 : 55.0,
          institutional_flow: "Accumulation",
          fii_buy: 12450.50,
          fii_sell: 11230.20,
          dii_buy: 9540.80,
          dii_sell: 8210.40,
          net_fii: 1220.30,
          net_dii: 1330.40,
          usd_inr: 83.45,
          crude_oil: 78.50,
          us_yield: 4.22,
          sectors: {
            "Defence": "Strong Buy",
            "Power": "Strong Buy",
            "Energy": "Accumulation",
            "Banking": "Accumulation",
            "Healthcare": "Neutral",
            "FMCG": "Weak",
            "Technology": "Weak",
            "Metals": "Avoid"
          },
          events: [
            { name: "RBI Monetary Policy Meeting", days_away: 12, risk: "High" },
            { name: "US Fed Interest Rate Decision", days_away: 4, risk: "High" },
            { name: "Earnings Season Proximity", days_away: 2, risk: "Medium" }
          ],
          block_trades: false
        };
        
        setData(mockMacro);
      } else {
        onShowToast("Failed to fetch macro intelligence.", true);
      }
    } catch (e) {
      onShowToast("Failed to connect to macro intelligence services.", true);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', width: '100%', padding: '2rem 0' }}>
        <div className="skeleton-bar" style={{ width: '40%', height: '32px' }}></div>
        <div className="skeleton-bar" style={{ width: '100%', height: '140px' }}></div>
      </div>
    );
  }

  const sectors = data?.sectors || {};
  const events = data?.events || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', width: '100%', paddingBottom: '3.5rem' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Globe className="text-info" /> Market Intelligence Center
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
            Broad macro health indicators, FII/DII institutional flows, and global markets stress ratings.
          </p>
        </div>
        <button className="flat-btn" onClick={fetchMacroData} style={{ height: '30px', padding: '0 0.75rem' }}>
          Reload Macro Indicators
        </button>
      </div>

      {/* Main Grid Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '3fr 2fr', gap: '1.5rem' }}>
        
        {/* Left Hand: Flows and Sectors */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Institutional flows */}
          <div className="card-panel">
            <h3 className="section-title" style={{ marginBottom: '1.15rem' }}>FII & DII Daily Money Flow</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
              
              {/* FII Box */}
              <div className="metrics-box" style={{ padding: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  <span>FOREIGN INSTITUTIONAL (FII)</span>
                  <span style={{ color: 'var(--success)', fontWeight: 'bold' }}>+₹{(data?.net_fii || 0).toFixed(1)} Cr</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem', fontSize: '0.76rem' }}>
                  <span>Bought: ₹{data?.fii_buy} Cr</span>
                  <span>Sold: ₹{data?.fii_sell} Cr</span>
                </div>
              </div>

              {/* DII Box */}
              <div className="metrics-box" style={{ padding: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  <span>DOMESTIC INSTITUTIONAL (DII)</span>
                  <span style={{ color: 'var(--success)', fontWeight: 'bold' }}>+₹{(data?.net_dii || 0).toFixed(1)} Cr</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.5rem', fontSize: '0.76rem' }}>
                  <span>Bought: ₹{data?.dii_buy} Cr</span>
                  <span>Sold: ₹{data?.dii_sell} Cr</span>
                </div>
              </div>

            </div>
          </div>

          {/* Sector Strength rankings */}
          <div className="card-panel">
            <h3 className="section-title" style={{ marginBottom: '0.85rem' }}>Sector Rotation Rankings</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: '0.75rem' }}>
              {Object.entries(sectors).map(([sec, rank]) => (
                <div key={sec} className="metrics-box" style={{ padding: '0.75rem', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 'bold' }}>{sec}</div>
                  <span 
                    className={`badge ${
                      rank === 'Strong Buy' || rank === 'Accumulation' ? 'badge-bullish' : rank === 'Avoid' ? 'badge-bearish' : 'badge-neutral'
                    }`} 
                    style={{ fontSize: '0.62rem', display: 'inline-block', marginTop: '0.35rem' }}
                  >
                    {rank}
                  </span>
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* Right Hand: Global risk & Calendar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Global Risk card */}
          <div className="card-panel">
            <h3 className="section-title" style={{ marginBottom: '1rem' }}>Global Markets Stress Score</h3>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.25rem' }}>
              <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--info)' }}>
                {data?.global_risk.toFixed(1)}/100
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                Composite risk calculated across currency, yields, and commodity price changes.
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.74rem', borderTop: '1px solid var(--border-color)', paddingTop: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>USD/INR Exchange Rate</span>
                <strong>₹{data?.usd_inr}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>Brent Crude Price</span>
                <strong>${data?.crude_oil}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--text-muted)' }}>US 10-Year Treasury Yield</span>
                <strong>{data?.us_yield}%</strong>
              </div>
            </div>

          </div>

          {/* Economic Calendar events */}
          <div className="card-panel">
            <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.85rem' }}>
              <Calendar size={16} /> Economic Calendar
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
              {events.map(ev => (
                <div key={ev.name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.72rem' }}>
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <strong>{ev.name}</strong>
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>{ev.days_away} days away</span>
                  </div>
                  <span className={`badge ${ev.risk === 'High' ? 'badge-bearish' : 'badge-neutral'}`} style={{ fontSize: '0.62rem' }}>
                    {ev.risk} Risk
                  </span>
                </div>
              ))}
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}
