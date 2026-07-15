import React, { useState, useEffect } from 'react';
import { 
  Award, 
  TrendingUp, 
  Settings, 
  Brain, 
  ChevronRight, 
  ArrowUpRight 
} from 'lucide-react';

interface ScoreboardItem {
  name: string;
  win_rate: number;
  sharpe: number;
  profit_factor: number;
  return_pct: number;
  drawdown: number;
  rank: number;
}

interface LearningDashboardData {
  weights: Record<string, number>;
  scoreboard: ScoreboardItem[];
  ratings: Record<string, string>;
  learning_progress: number;
}

export default function AILearning({ apiBase, onShowToast }: { apiBase: string; onShowToast: (msg: string, isErr?: boolean) => void }) {
  const [data, setData] = useState<LearningDashboardData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    fetchLearningData();
  }, []);

  const fetchLearningData = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiBase}/api/learning/dashboard`);
      if (res.ok) {
        const payload = await res.json();
        setData(payload);
      } else {
        onShowToast("Failed to fetch learning parameters.", true);
      }
    } catch (e) {
      onShowToast("Failed to connect to self-learning services.", true);
    } finally {
      setLoading(false);
    }
  };

  const handleSimulateTrade = async () => {
    try {
      onShowToast("Simulating completed trade...");
      // Simulate BEL closing in profit to trigger weight tuning updates
      const res = await fetch(`${apiBase}/api/learning/simulate-trade?ticker=BEL&entry_price=300.0&exit_price=330.0`, {
        method: 'POST'
      });
      if (res.ok) {
        onShowToast("Trade recorded. Weight Optimizer step triggered successfully.");
        fetchLearningData();
      } else {
        onShowToast("Failed to simulate trade outcome.", true);
      }
    } catch (e) {
      onShowToast("Connection error during simulation.", true);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', width: '100%', padding: '2rem 0' }}>
        <div className="skeleton-bar" style={{ width: '30%', height: '32px' }}></div>
        <div className="skeleton-bar" style={{ width: '100%', height: '180px' }}></div>
      </div>
    );
  }

  const scoreboard = data?.scoreboard || [];
  const weights = data?.weights || {};
  const ratings = data?.ratings || {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', width: '100%', paddingBottom: '3.5rem' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <Brain className="text-info" /> AI Learning Center
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
            Telemetry of committee weights, stock reliability grades, and sub-strategy scoreboard.
          </p>
        </div>
        
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="flat-btn" onClick={handleSimulateTrade} style={{ height: '30px', padding: '0 0.75rem' }}>
            Simulate Completed WIN Trade
          </button>
          <button className="flat-btn" onClick={fetchLearningData} style={{ height: '30px', padding: '0 0.75rem' }}>
            Reload Telemetry
          </button>
        </div>
      </div>

      {/* Main content grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        
        {/* Left Side: Committee Weights & Ratings */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Committee Weights chart */}
          <div className="card-panel">
            <h3 className="section-title" style={{ marginBottom: '1.15rem' }}>Committee Voting Weights</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
              {Object.entries(weights).map(([name, weight]) => (
                <div key={name}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
                    <span>{name} Committee</span>
                    <strong style={{ color: 'var(--info)' }}>{(weight * 100).toFixed(1)}%</strong>
                  </div>
                  <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.04)', borderRadius: '4px', overflow: 'hidden' }}>
                    <div style={{ width: `${weight * 100}%`, height: '100%', background: 'var(--info)', borderRadius: '4px' }}></div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Stock Grades Grid */}
          <div className="card-panel">
            <h3 className="section-title" style={{ marginBottom: '0.85rem' }}>Stock Reliability Ratings</h3>
            <p style={{ margin: '0 0 1rem 0', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              Permanent grades based on historical accuracy, average returns, and drawdowns.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: '0.75rem' }}>
              {Object.entries(ratings).map(([ticker, grade]) => (
                <div key={ticker} className="metrics-box" style={{ padding: '0.75rem', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 'bold' }}>{ticker}</div>
                  <div 
                    style={{ 
                      fontSize: '1.4rem', 
                      fontWeight: 'bold', 
                      color: grade.startsWith('A') ? 'var(--success)' : grade.startsWith('B') ? 'var(--info)' : 'var(--warning)', 
                      marginTop: '0.25rem' 
                    }}
                  >
                    {grade}
                  </div>
                </div>
              ))}
            </div>
          </div>

        </div>

        {/* Right Side: Strategy Scoreboard & Progress */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Strategy Scoreboard */}
          <div className="card-panel">
            <h3 className="section-title" style={{ marginBottom: '1rem' }}>Anchor Strategy Scoreboard</h3>
            <div className="table-responsive">
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.72rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left', color: 'var(--text-secondary)' }}>
                    <th style={{ padding: '0.4rem 0.25rem' }}>Rank</th>
                    <th style={{ padding: '0.4rem 0.25rem' }}>Strategy Name</th>
                    <th style={{ padding: '0.4rem 0.25rem' }}>Win Rate</th>
                    <th style={{ padding: '0.4rem 0.25rem' }}>Sharpe</th>
                    <th style={{ padding: '0.4rem 0.25rem' }}>Return</th>
                  </tr>
                </thead>
                <tbody>
                  {scoreboard.map(row => (
                    <tr key={row.name} style={{ borderBottom: '1px solid rgba(255,255,255,0.02)' }}>
                      <td style={{ padding: '0.5rem 0.25rem', color: 'var(--text-muted)' }}>#{row.rank}</td>
                      <td style={{ padding: '0.5rem 0.25rem', fontWeight: 'bold' }}>{row.name}</td>
                      <td style={{ padding: '0.5rem 0.25rem', color: 'var(--success)' }}>{row.win_rate}%</td>
                      <td style={{ padding: '0.5rem 0.25rem', color: 'var(--info)' }}>{row.sharpe.toFixed(2)}</td>
                      <td style={{ padding: '0.5rem 0.25rem', color: row.return_pct > 0 ? 'var(--success)' : 'var(--danger)' }}>
                        {row.return_pct > 0 ? '+' : ''}{row.return_pct.toFixed(2)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Learning Progress Curve card */}
          <div className="card-panel">
            <h3 className="section-title" style={{ marginBottom: '0.85rem' }}>Self-Learning Engine Status</h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
              <div style={{ fontSize: '1.8rem', fontWeight: 'bold', color: 'var(--info)' }}>
                {data?.learning_progress}%
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                Cumulative accuracy over last 100 optimized cycles.
              </div>
            </div>
            
            <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '0.75rem', fontSize: '0.7rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>
              <strong>Optimization Rules:</strong> Committee weights undergo minor rolling adjustments based on daily closing validations. Underperforming models are dynamically capped to prevent sudden decision drift.
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}
