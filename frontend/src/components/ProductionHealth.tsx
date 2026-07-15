import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  RotateCcw,
  CheckCircle,
  AlertTriangle,
  Server,
  Cloud,
  Database,
  Wifi,
  Clock,
  Briefcase,
  AlertCircle
} from 'lucide-react';

interface HealthMetrics {
  health_score: number;
  upstox_status: string;
  upstox_reason: string;
  upstox_latency_ms: number;
  firestore_status: string;
  firestore_latency_ms: number;
  gemini_status: string;
  gemini_latency_ms: number;
  internet_status: string;
  internet_latency_ms: number;
  scheduler_status: string;
  mode: string;
  last_order: any;
  current_incident: any;
  timestamp: number;
  created_at: string;
}

interface ProductionHealthProps {
  apiBase: string;
  onShowToast: (msg: string, isError?: boolean) => void;
}

export default function ProductionHealth({ apiBase, onShowToast }: ProductionHealthProps) {
  const [metrics, setMetrics] = useState<HealthMetrics | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isUpdating, setIsUpdating] = useState<boolean>(false);

  const fetchHealthMetrics = async (showFeedback = false) => {
    try {
      if (showFeedback) setIsUpdating(true);
      const res = await fetch(`${apiBase}/api/live/health`);
      if (res.ok) {
        const data = await res.json();
        setMetrics(data);
        if (showFeedback) onShowToast("E2E systems health checks updated successfully.");
      } else {
        onShowToast("Health checks endpoint failed.", true);
      }
    } catch (e) {
      console.error(e);
      onShowToast("Health check endpoint connection error.", true);
    } finally {
      setIsLoading(false);
      setIsUpdating(false);
    }
  };

  useEffect(() => {
    fetchHealthMetrics();
    // Auto refresh health metrics every 60 seconds
    const interval = setInterval(() => fetchHealthMetrics(), 60000);
    return () => clearInterval(interval);
  }, []);

  if (isLoading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
        Loading production system validation parameters...
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="card-panel" style={{ textAlign: 'center', padding: '2rem' }}>
        <AlertTriangle className="text-danger" size={32} style={{ marginBottom: '1rem' }} />
        <h3>Failed to load System Health diagnostics.</h3>
        <button className="flat-btn" onClick={() => fetchHealthMetrics(true)} style={{ marginTop: '1rem' }}>
          Retry health check
        </button>
      </div>
    );
  }

  const scoreColor = metrics.health_score >= 85 ? '#22c55e' : metrics.health_score >= 70 ? '#eab308' : '#ef4444';
  const scoreLabel = metrics.health_score >= 85 ? 'HEALTHY' : metrics.health_score >= 70 ? 'DEGRADED' : 'FAILSAFE CRITICAL';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', width: '100%', paddingBottom: '3.5rem' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Server className="text-info" /> Production Health & Hardening Dashboard
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
            Observe API connections status, trace latency, check scheduler checks, and inspect active failsafe safety breakers.
          </p>
        </div>
        <button className="flat-btn" onClick={() => fetchHealthMetrics(true)} disabled={isUpdating} style={{ height: '36px' }}>
          <RotateCcw size={14} className={isUpdating ? 'spin' : ''} /> {isUpdating ? 'Re-Checking...' : 'Run Diagnostics'}
        </button>
      </div>

      {/* Main Grid: Health Score Dial & Detailed stats */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '1.5rem' }}>
        
        {/* Left Side: Score Gauges */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          <div className="card-panel" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '2rem', textAlign: 'center' }}>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>E2E Health Score</span>
            
            {/* SVG radial score */}
            <div style={{ position: 'relative', width: '160px', height: '160px', margin: '1.25rem 0' }}>
              <svg width="100%" height="100%" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="40" fill="none" stroke="var(--border-color)" strokeWidth="6" />
                <circle 
                  cx="50" 
                  cy="50" 
                  r="40" 
                  fill="none" 
                  stroke={scoreColor} 
                  strokeWidth="6" 
                  strokeDasharray={`${2 * Math.PI * 40}`}
                  strokeDashoffset={`${2 * Math.PI * 40 * (1 - metrics.health_score / 100)}`}
                  strokeLinecap="round"
                  transform="rotate(-90 50 50)"
                  style={{ transition: 'stroke-dashoffset 0.8s ease-in-out' }}
                />
              </svg>
              <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <span style={{ fontSize: '2rem', fontWeight: 800, color: 'white', lineHeight: 1 }}>{metrics.health_score}</span>
                <span style={{ fontSize: '0.55rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>out of 100</span>
              </div>
            </div>

            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: scoreColor }}>
              SYSTEM STATUS: {scoreLabel}
            </span>
            <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.68rem', color: 'var(--text-muted)' }}>
              Checked at: {new Date(metrics.timestamp * 1000).toLocaleTimeString()}
            </p>
          </div>

          {/* Active Failsafe incident alerts */}
          {metrics.current_incident && !metrics.current_incident.recovered ? (
            <div className="card-panel" style={{ borderLeft: '4px solid var(--danger)', background: 'rgba(239,68,68,0.02)' }}>
              <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--danger)', fontSize: '0.85rem' }}>
                <AlertCircle size={15} /> ACTIVE SAFETY INCIDENT
              </h3>
              <p style={{ fontSize: '0.72rem', color: 'white', margin: '0.5rem 0' }}>
                <strong>Reason:</strong> {metrics.current_incident.reason}
              </p>
              <span style={{ fontSize: '0.62rem', color: 'var(--text-secondary)' }}>
                Triggered at: {new Date(metrics.current_incident.timestamp * 1000).toLocaleString()}
              </span>
            </div>
          ) : (
            <div className="card-panel" style={{ borderLeft: '4px solid var(--success)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <CheckCircle className="text-success" size={20} />
              <div>
                <strong style={{ fontSize: '0.78rem', display: 'block' }}>Failsafe Status: NORMAL</strong>
                <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>No active failsafe triggers or incidents logs.</span>
              </div>
            </div>
          )}

        </div>

        {/* Right Side: Detailed microservice statuses & Latencies */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Microservice Indicators */}
          <div className="card-panel">
            <h3 className="section-title" style={{ marginBottom: '1.25rem' }}>Module Dependencies Statuses</h3>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
              
              {/* Upstox */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{ padding: '0.5rem', background: metrics.upstox_status === 'CONNECTED' ? 'rgba(34,197,94,0.06)' : 'rgba(239,68,68,0.06)', borderRadius: '6px' }}>
                  <Cloud className={metrics.upstox_status === 'CONNECTED' ? 'text-success' : 'text-danger'} size={18} />
                </div>
                <div>
                  <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', display: 'block' }}>Upstox Authentication</span>
                  <strong style={{ fontSize: '0.8rem' }}>{metrics.upstox_status}</strong>
                </div>
              </div>

              {/* Gemini */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{ padding: '0.5rem', background: metrics.gemini_status === 'CONNECTED' ? 'rgba(34,197,94,0.06)' : 'rgba(239,68,68,0.06)', borderRadius: '6px' }}>
                  <Activity className={metrics.gemini_status === 'CONNECTED' ? 'text-success' : 'text-danger'} size={18} />
                </div>
                <div>
                  <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', display: 'block' }}>Gemini Chairperson AI</span>
                  <strong style={{ fontSize: '0.8rem' }}>{metrics.gemini_status}</strong>
                </div>
              </div>

              {/* Firestore */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{ padding: '0.5rem', background: metrics.firestore_status === 'CONNECTED' ? 'rgba(34,197,94,0.06)' : 'rgba(239,68,68,0.06)', borderRadius: '6px' }}>
                  <Database className={metrics.firestore_status === 'CONNECTED' ? 'text-success' : 'text-danger'} size={18} />
                </div>
                <div>
                  <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', display: 'block' }}>Firestore DB Cluster</span>
                  <strong style={{ fontSize: '0.8rem' }}>{metrics.firestore_status}</strong>
                </div>
              </div>

              {/* Internet */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{ padding: '0.5rem', background: metrics.internet_status === 'CONNECTED' ? 'rgba(34,197,94,0.06)' : 'rgba(239,68,68,0.06)', borderRadius: '6px' }}>
                  <Wifi className={metrics.internet_status === 'CONNECTED' ? 'text-success' : 'text-danger'} size={18} />
                </div>
                <div>
                  <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', display: 'block' }}>Internet Connectivity</span>
                  <strong style={{ fontSize: '0.8rem' }}>{metrics.internet_status}</strong>
                </div>
              </div>

            </div>
          </div>

          {/* Latency Profiling (Task 5) */}
          <div className="card-panel">
            <h3 className="section-title" style={{ marginBottom: '1.25rem' }}>Latency Diagnostics Trace (Task 5)</h3>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', fontSize: '0.75rem' }}>
              
              {/* Upstox */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                  <span>Upstox Session Validation:</span>
                  <strong>{metrics.upstox_latency_ms} ms</strong>
                </div>
                <div style={{ height: '4px', background: 'var(--border-color)', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{ height: '100%', background: 'var(--info)', width: `${Math.min(100, (metrics.upstox_latency_ms / 1500) * 100)}%` }} />
                </div>
              </div>

              {/* Gemini */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                  <span>Gemini API generate:</span>
                  <strong>{metrics.gemini_latency_ms} ms</strong>
                </div>
                <div style={{ height: '4px', background: 'var(--border-color)', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{ height: '100%', background: 'var(--info)', width: `${Math.min(100, (metrics.gemini_latency_ms / 3000) * 100)}%` }} />
                </div>
              </div>

              {/* Firestore */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                  <span>Firestore Read/Write IO:</span>
                  <strong>{metrics.firestore_latency_ms} ms</strong>
                </div>
                <div style={{ height: '4px', background: 'var(--border-color)', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{ height: '100%', background: 'var(--info)', width: `${Math.min(100, (metrics.firestore_latency_ms / 500) * 100)}%` }} />
                </div>
              </div>

              {/* Internet */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' }}>
                  <span>Google Connection Ping:</span>
                  <strong>{metrics.internet_latency_ms} ms</strong>
                </div>
                <div style={{ height: '4px', background: 'var(--border-color)', borderRadius: '2px', overflow: 'hidden' }}>
                  <div style={{ height: '100%', background: 'var(--info)', width: `${Math.min(100, (metrics.internet_latency_ms / 500) * 100)}%` }} />
                </div>
              </div>

            </div>
          </div>

          {/* Last Audited Order panel */}
          {metrics.last_order && (
            <div className="card-panel">
              <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.75rem' }}>
                <Clock size={15} /> Last Order Executed
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Ticker Action:</span>
                  <strong>{metrics.last_order.transaction_type} {metrics.last_order.ticker}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Order Quantity:</span>
                  <strong>{metrics.last_order.quantity} shares</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Sizing Price:</span>
                  <strong>₹{metrics.last_order.price}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Broker Status:</span>
                  <span className={`text-${['FILLED', 'FILLED_SIMULATED'].includes(metrics.last_order.status) ? 'success' : 'danger'}`}>
                    {metrics.last_order.status}
                  </span>
                </div>
              </div>
            </div>
          )}

        </div>

      </div>

    </div>
  );
}
