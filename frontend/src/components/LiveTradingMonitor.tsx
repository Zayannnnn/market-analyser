import React, { useState, useEffect } from 'react';
import { 
  Play, 
  RefreshCw, 
  Activity, 
  Cpu, 
  ShieldAlert, 
  CheckCircle, 
  XCircle, 
  Clock, 
  AlertTriangle,
  History,
  Info
} from 'lucide-react';

interface LogEntry {
  timestamp: string;
  event: string;
  level: string;
  message: string;
}

interface SchedulerStatus {
  status: string;
  current_job: string;
  last_scan_time: string;
  next_scan_time: string;
  gemini_status: string;
  upstox_status: string;
  firestore_status: string;
  telegram_status: string;
  today_trades_count: number;
  today_pnl: number;
  logs: LogEntry[];
}

interface OpenTrade {
  ticker: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  unrealized_pnl: number;
  stop_loss: number;
  target: number;
  entry_date: string;
}

interface LiveTradingMonitorProps {
  apiBase: string;
  onShowToast: (msg: string, isError?: boolean) => void;
}

export default function LiveTradingMonitor({ apiBase, onShowToast }: LiveTradingMonitorProps) {
  const [sched, setSched] = useState<SchedulerStatus | null>(null);
  const [openTrades, setOpenTrades] = useState<OpenTrade[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);
  const [isChecking, setIsChecking] = useState<boolean>(false);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      
      // Fetch status
      const resStatus = await fetch(`${apiBase}/api/paper/scheduler/status`);
      const dataStatus = await resStatus.json();
      setSched(dataStatus);
      
      // Fetch positions (open trades)
      const resPos = await fetch(`${apiBase}/api/paper/positions`);
      const dataPos = await resPos.json();
      setOpenTrades(dataPos);
      
    } catch (e) {
      console.error(e);
      onShowToast("Failed to fetch scheduler status metrics.", true);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Poll every 10 seconds for real-time live trading monitor updates
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleSimulateDay = async () => {
    try {
      setIsSimulating(true);
      onShowToast("Simulating trading day. Scans, news, events, and AI trade logs are loading...");
      
      const res = await fetch(`${apiBase}/api/paper/scheduler/run-simulated-day`, { method: "POST" });
      if (res.ok) {
        onShowToast("E2E Simulated trading day sequence executed successfully!");
        fetchData();
      } else {
        onShowToast("Failed to run simulated day checks.", true);
      }
    } catch (e) {
      onShowToast("Simulate day connection failed.", true);
    } finally {
      setIsSimulating(false);
    }
  };

  const handleRunChecks = async () => {
    try {
      setIsChecking(true);
      const res = await fetch(`${apiBase}/api/paper/scheduler/health-checks`, { method: "POST" });
      if (res.ok) {
        onShowToast("Morning health verification checks completed.");
        fetchData();
      } else {
        onShowToast("Failed to trigger health checks.", true);
      }
    } catch (e) {
      onShowToast("Health check connection failed.", true);
    } finally {
      setIsChecking(false);
    }
  };

  if (isLoading && !sched) {
    return (
      <div className="empty-state" style={{ height: '350px' }}>
        <div className="skeleton-line" style={{ width: '180px', height: '2rem', marginBottom: '1rem' }}></div>
        <div className="skeleton-line" style={{ height: '240px' }}></div>
      </div>
    );
  }

  const statusColor = sched?.status === "ACTIVE" ? "text-bullish" : sched?.status === "IDLE" ? "text-warning" : "text-bearish";
  const logsList = sched?.logs || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', width: '100%', paddingBottom: '3rem' }}>
      
      {/* Header controls */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Activity className="text-bullish" /> Autonomous Live Trading Monitor
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
            Real-time status tracking of morning health checks, watchlist scanner tasks, and paper trading automation.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button 
            className="flat-btn" 
            style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', height: '36px' }}
            onClick={handleSimulateDay}
            disabled={isSimulating}
          >
            <Play size={14} /> {isSimulating ? 'Simulating Day...' : 'Run Simulated Day'}
          </button>
          <button 
            className="flat-btn flat-btn-outline" 
            style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', height: '36px' }}
            onClick={handleRunChecks}
            disabled={isChecking}
          >
            <RefreshCw size={14} /> {isChecking ? 'Checking...' : 'Trigger Health Checks'}
          </button>
        </div>
      </div>

      {/* Grid: Health Status Indicators & Scheduler Info */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
        
        {/* Scheduler General Stats Card */}
        <div className="card-panel">
          <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '1.25rem' }}>
            <Cpu size={16} /> Scheduler Configuration
          </h3>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', fontSize: '0.82rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>System Status</span>
              <strong className={statusColor}>{sched?.status || "ACTIVE"}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Active Job</span>
              <strong style={{ color: 'var(--text-primary)' }}>{sched?.current_job || "IDLE"}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border-color)', paddingBottom: '0.5rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Last Watchlist Scan</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <Clock size={12} /> {sched?.last_scan_time ? new Date(sched.last_scan_time).toLocaleTimeString() : 'Never'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '0.25rem' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Next Scan Scheduled</span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                <Clock size={12} /> {sched?.next_scan_time ? new Date(sched.next_scan_time).toLocaleTimeString() : 'Pending'}
              </span>
            </div>
          </div>
        </div>

        {/* Integration Status Panel */}
        <div className="card-panel">
          <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '1.25rem' }}>
            <ShieldAlert size={16} /> Services API Status
          </h3>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', fontSize: '0.8rem' }}>
            
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem', background: 'rgba(255,255,255,0.01)', borderRadius: '6px' }}>
              {sched?.gemini_status === "CONNECTED" ? <CheckCircle size={14} className="text-bullish" /> : <XCircle size={14} className="text-bearish" />}
              <div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Gemini AI</div>
                <strong style={{ color: 'var(--text-primary)' }}>{sched?.gemini_status}</strong>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem', background: 'rgba(255,255,255,0.01)', borderRadius: '6px' }}>
              {sched?.upstox_status === "CONNECTED" ? <CheckCircle size={14} className="text-bullish" /> : <XCircle size={14} className="text-bearish" />}
              <div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Upstox Broker</div>
                <strong style={{ color: 'var(--text-primary)' }}>{sched?.upstox_status}</strong>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem', background: 'rgba(255,255,255,0.01)', borderRadius: '6px' }}>
              {sched?.firestore_status === "CONNECTED" ? <CheckCircle size={14} className="text-bullish" /> : <XCircle size={14} className="text-bearish" />}
              <div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Firestore DB</div>
                <strong style={{ color: 'var(--text-primary)' }}>{sched?.firestore_status}</strong>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem', background: 'rgba(255,255,255,0.01)', borderRadius: '6px' }}>
              {sched?.telegram_status === "CONNECTED" ? <CheckCircle size={14} className="text-bullish" /> : <XCircle size={14} className="text-bearish" />}
              <div>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Telegram Bot</div>
                <strong style={{ color: 'var(--text-primary)' }}>{sched?.telegram_status}</strong>
              </div>
            </div>

          </div>
        </div>

      </div>

      {/* Mini Performance Cards */}
      <section className="metrics-row" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
        <div className="info-card">
          <span className="info-card-label">Today's Trades executed</span>
          <span className="info-card-value">{sched?.today_trades_count || 0}</span>
        </div>
        <div className="info-card">
          <span className="info-card-label">Today's P&L</span>
          <span className={`info-card-value ${(sched?.today_pnl || 0) >= 0 ? 'text-bullish' : 'text-bearish'}`}>
            {(sched?.today_pnl || 0) >= 0 ? '+' : ''}₹{(sched?.today_pnl || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
          </span>
        </div>
        <div className="info-card">
          <span className="info-card-label">Sim Active Positions</span>
          <span className="info-card-value">{openTrades.length}</span>
        </div>
      </section>

      {/* Open Trades list */}
      <div className="card-panel">
        <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '1rem' }}>
          <Activity size={16} /> Active Positions ({openTrades.length})
        </h3>
        {openTrades.length > 0 ? (
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
                </tr>
              </thead>
              <tbody>
                {openTrades.map((item, idx) => (
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
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ height: '80px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)', fontStyle: 'italic', fontSize: '0.8rem' }}>
            No open paper positions actively tracked.
          </div>
        )}
      </div>

      {/* Execution Logs list */}
      <div className="card-panel">
        <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '1rem' }}>
          <History size={16} /> Execution Logs ({logsList.length})
        </h3>
        {logsList.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '350px', overflowY: 'auto', paddingRight: '0.5rem' }}>
            {logsList.slice().reverse().map((log, idx) => {
              const badgeClass = log.level === "ERROR" ? "badge-danger" : log.level === "WARNING" ? "badge-warning" : "badge-success";
              return (
                <div 
                  key={idx} 
                  style={{ 
                    display: 'flex', 
                    flexDirection: 'column',
                    gap: '0.25rem',
                    padding: '0.65rem', 
                    background: 'rgba(255,255,255,0.01)', 
                    border: '1px solid var(--border-color)', 
                    borderRadius: '6px' 
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.7rem' }}>
                    <span style={{ color: 'var(--text-muted)' }}>{new Date(log.timestamp).toLocaleString()}</span>
                    <span className={`badge ${badgeClass}`}>{log.event}</span>
                  </div>
                  <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                    {log.message}
                  </p>
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{ height: '100px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)', fontStyle: 'italic', fontSize: '0.8rem' }}>
            No scheduler logs loaded. Trigger checks or runs to generate logs.
          </div>
        )}
      </div>

    </div>
  );
}
