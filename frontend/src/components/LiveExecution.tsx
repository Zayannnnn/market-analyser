import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  RotateCcw,
  CheckCircle,
  AlertTriangle,
  Play,
  Pause,
  Settings,
  Plus,
  Trash2,
  Lock,
  Unlock,
  Radio,
  FileText
} from 'lucide-react';

interface LiveOrder {
  order_id: string;
  ticker: string;
  quantity: number;
  price: number;
  order_type: string;
  transaction_type: string;
  reason: string;
  confidence: number;
  risk_score: number;
  market_regime: string;
  mode: string;
  status: string;
  broker_response: string;
  execution_latency_ms: number;
  created_at: string;
}

interface LiveExecutionProps {
  apiBase: string;
  onShowToast: (msg: string, isError?: boolean) => void;
}

export default function LiveExecution({ apiBase, onShowToast }: LiveExecutionProps) {
  const [orders, setOrders] = useState<LiveOrder[]>([]);
  const [mode, setMode] = useState<string>('CONFIRM');
  const [liveTradingEnabled, setLiveTradingEnabled] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isUpdatingConfig, setIsUpdatingConfig] = useState<boolean>(false);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  
  // Custom manual order states
  const [customTicker, setCustomTicker] = useState<string>('');
  const [customQty, setCustomQty] = useState<number>(100);
  const [customPrice, setCustomPrice] = useState<number>(10.0);
  const [customAction, setCustomAction] = useState<string>('BUY');
  const [customReason, setCustomReason] = useState<string>('Manual safety test');
  const [isSubmittingCustom, setIsSubmittingCustom] = useState<boolean>(false);

  const fetchStatus = async () => {
    try {
      setIsLoading(true);
      
      // 1. Fetch live orders
      const resOrders = await fetch(`${apiBase}/api/live/orders`);
      const ordersData = await resOrders.json();
      setOrders(ordersData);
      
      // 2. Fetch live configs
      const resConfig = await fetch(`${apiBase}/api/live/config`);
      const configData = await resConfig.json();
      setMode(configData.mode || 'CONFIRM');
      setLiveTradingEnabled(configData.live_trading_enabled || false);
      
      // 3. Fetch general scheduler status to check broker auth
      const resScheduler = await fetch(`${apiBase}/api/paper/scheduler/status`);
      const schedulerData = await resScheduler.json();
      setIsAuthenticated(schedulerData.upstox_status === 'CONNECTED');
      
    } catch (e) {
      console.error(e);
      onShowToast("Failed to fetch Live execution status.", true);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleUpdateMode = async (newMode: string, enabled: boolean) => {
    try {
      setIsUpdatingConfig(true);
      const res = await fetch(`${apiBase}/api/live/config?mode=${newMode}&live_trading_enabled=${enabled}`, {
        method: "POST"
      });
      if (res.ok) {
        setMode(newMode);
        setLiveTradingEnabled(enabled);
        onShowToast(`Live config updated: Mode=${newMode}, Real Trading=${enabled ? 'ENABLED' : 'DISABLED'}`);
      } else {
        onShowToast("Failed to update live configurations.", true);
      }
    } catch (e) {
      onShowToast("Connection error during live configs update.", true);
    } finally {
      setIsUpdatingConfig(false);
    }
  };

  const handleApproveOrder = async (orderId: string) => {
    try {
      const res = await fetch(`${apiBase}/api/live/approve?order_id=${orderId}`);
      if (res.ok) {
        onShowToast("Order approved and submitted.");
        fetchStatus();
      } else {
        onShowToast("Failed to approve order.", true);
      }
    } catch (e) {
      onShowToast("Connection failed.", true);
    }
  };

  const handleRejectOrder = async (orderId: string) => {
    try {
      const res = await fetch(`${apiBase}/api/live/reject?order_id=${orderId}`);
      if (res.ok) {
        onShowToast("Order rejected successfully.");
        fetchStatus();
      } else {
        onShowToast("Failed to reject order.", true);
      }
    } catch (e) {
      onShowToast("Connection failed.", true);
    }
  };

  const handleSubmitCustomOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!customTicker.trim()) {
      onShowToast("Please enter a valid stock ticker.", true);
      return;
    }
    
    try {
      setIsSubmittingCustom(true);
      const res = await fetch(
        `${apiBase}/api/live/submit?ticker=${customTicker.toUpperCase().trim()}&qty=${customQty}&price=${customPrice}&tx_type=${customAction}&reason=${encodeURIComponent(customReason)}`,
        { method: "POST" }
      );
      
      if (res.ok) {
        onShowToast("Safety checks completed. Order submitted.");
        setCustomTicker('');
        fetchStatus();
      } else {
        onShowToast("Safety Layer / Execution engine rejected the order.", true);
      }
    } catch (e) {
      onShowToast("Connection error during order submission.", true);
    } finally {
      setIsSubmittingCustom(false);
    }
  };

  const pending = orders.filter(o => o.status === 'PENDING_APPROVAL');
  const filled = orders.filter(o => ['FILLED', 'FILLED_SIMULATED'].includes(o.status));
  const rejected = orders.filter(o => ['REJECTED_SAFETY', 'REJECTED_BROKER', 'REJECTED_MANUAL'].includes(o.status));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', width: '100%', paddingBottom: '3.5rem' }}>
      
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Activity className="text-bullish" /> Live Execution & Trade Safety
          </h2>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
            Verify API limits, manage approval logs, and toggle autonomous market order routing. Real cash trading is disabled by default.
          </p>
        </div>
        <button className="flat-btn" onClick={fetchStatus} style={{ height: '36px' }}>
          <RotateCcw size={14} /> Refresh Logs
        </button>
      </div>

      {/* Grid: Broker & Authentication indicators */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
        
        {/* Status card */}
        <div className="card-panel" style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
          <div style={{ padding: '0.75rem', background: isAuthenticated ? 'rgba(34,197,94,0.06)' : 'rgba(239,68,68,0.06)', borderRadius: '50%' }}>
            <Radio className={isAuthenticated ? "text-success" : "text-danger"} size={32} />
          </div>
          <div>
            <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', display: 'block' }}>Broker Auth Link</span>
            <strong style={{ fontSize: '1.15rem' }}>{isAuthenticated ? "Authenticated" : "Disconnected (Expired)"}</strong>
            <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.65rem', color: 'var(--text-muted)' }}>
              {isAuthenticated ? "Live API orders link active." : "Visit Settings / Callback URL to re-authenticate."}
            </p>
          </div>
        </div>

        {/* Configurations Toggle (Task 4) */}
        <div className="card-panel" style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Execution Mode Configurations (Task 4)</span>
          
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {['OFF', 'CONFIRM', 'AUTO'].map((m) => (
              <button 
                key={m}
                onClick={() => handleUpdateMode(m, liveTradingEnabled)}
                disabled={isUpdatingConfig}
                className="flat-btn"
                style={{ 
                  flex: 1, 
                  height: '32px', 
                  fontSize: '0.75rem',
                  background: mode === m ? 'var(--info)' : 'var(--border-color)',
                  color: 'white'
                }}
              >
                {m}
              </button>
            ))}
          </div>

          {/* Secure Live Trading Toggle */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '0.25rem', borderTop: '1px solid var(--border-color)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.72rem' }}>
              {liveTradingEnabled ? <Unlock size={14} className="text-warning" /> : <Lock size={14} className="text-success" />}
              <span>Cash Trading Account: <strong>{liveTradingEnabled ? 'ENABLED' : 'DISABLED (Simulated)'}</strong></span>
            </div>
            <button
              onClick={() => handleUpdateMode(mode, !liveTradingEnabled)}
              disabled={isUpdatingConfig}
              className="flat-btn"
              style={{
                height: '24px',
                padding: '0 0.5rem',
                fontSize: '0.65rem',
                background: liveTradingEnabled ? 'var(--danger)' : 'var(--success)'
              }}
            >
              {liveTradingEnabled ? 'Disable Cash' : 'Enable Cash'}
            </button>
          </div>

        </div>

      </div>

      {/* Main Grid: Pending Approval Queues & Manual entry */}
      <div style={{ display: 'grid', gridTemplateColumns: '3fr 2fr', gap: '1.5rem' }}>
        
        {/* Left Side: Pending Approval Queues */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Pending Approval List */}
          <div className="card-panel" style={{ borderLeft: '4px solid var(--info)' }}>
            <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '1.25rem' }}>
              <AlertTriangle className="text-info" size={16} /> Pending Manual Approvals ({pending.length})
            </h3>
            
            {pending.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                {pending.map((o, idx) => (
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
                      <div style={{ fontSize: '0.85rem', fontWeight: 800 }}>
                        <span className={o.transaction_type === 'BUY' ? 'text-success' : 'text-danger'}>
                          {o.transaction_type} {o.ticker}
                        </span>
                        <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginLeft: '0.5rem' }}>
                          Qty: {o.quantity} @ ₹{o.price}
                        </span>
                      </div>
                      <div style={{ display: 'flex', gap: '0.4rem' }}>
                        <button 
                          className="flat-btn" 
                          onClick={() => handleApproveOrder(o.order_id)}
                          style={{ height: '26px', fontSize: '0.68rem', background: 'var(--success)' }}
                        >
                          Approve
                        </button>
                        <button 
                          className="flat-btn" 
                          onClick={() => handleRejectOrder(o.order_id)}
                          style={{ height: '26px', fontSize: '0.68rem', background: 'var(--danger)' }}
                        >
                          Reject
                        </button>
                      </div>
                    </div>
                    <p style={{ margin: 0, fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                      <strong>Reason:</strong> {o.reason}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: '1rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.75rem' }}>
                No live orders waiting for manual confirmation.
              </div>
            )}
          </div>

          {/* Filled / Audit orders logs */}
          <div className="card-panel">
            <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '1.15rem' }}>
              <CheckCircle className="text-success" size={16} /> Order Audit Trail / Executions
            </h3>
            
            <div className="table-responsive" style={{ maxHeight: '300px', overflowY: 'auto' }}>
              <table className="orders-table">
                <thead>
                  <tr>
                    <th>Ticker</th>
                    <th>Action</th>
                    <th>Qty</th>
                    <th>Price</th>
                    <th>Status</th>
                    <th>Response</th>
                    <th>Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {orders.map((o, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: 800 }}>{o.ticker}</td>
                      <td>
                        <span className={o.transaction_type === 'BUY' ? 'text-success' : 'text-danger'}>
                          {o.transaction_type}
                        </span>
                      </td>
                      <td>{o.quantity}</td>
                      <td>₹{o.price}</td>
                      <td>
                        <span className={`badge ${['FILLED', 'FILLED_SIMULATED'].includes(o.status) ? 'badge-success' : o.status.startsWith('PENDING') ? 'badge-warning' : 'badge-danger'}`} style={{ fontSize: '0.62rem' }}>
                          {o.status}
                        </span>
                      </td>
                      <td style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={o.broker_response}>
                        {o.broker_response}
                      </td>
                      <td style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>{o.execution_latency_ms}ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>

        {/* Right Side: Manual Order Verification Form */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Manual Entry Form */}
          <div className="card-panel">
            <h3 className="section-title" style={{ marginBottom: '1.15rem' }}>Manual Order Entry Safety Test</h3>
            
            <form onSubmit={handleSubmitCustomOrder} style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', fontSize: '0.76rem' }}>
              <div>
                <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Ticker Symbol</label>
                <input 
                  type="text" 
                  value={customTicker} 
                  onChange={e => setCustomTicker(e.target.value)}
                  className="search-input"
                  style={{ width: '100%', height: '32px' }}
                  placeholder="e.g. GREENPOWER"
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                <div>
                  <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Quantity</label>
                  <input 
                    type="number" 
                    value={customQty} 
                    onChange={e => setCustomQty(Number(e.target.value))}
                    className="search-input"
                    style={{ width: '100%', height: '32px' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Limit Price (₹)</label>
                  <input 
                    type="number" 
                    step="0.05"
                    value={customPrice} 
                    onChange={e => setCustomPrice(Number(e.target.value))}
                    className="search-input"
                    style={{ width: '100%', height: '32px' }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Transaction Action</label>
                <select 
                  value={customAction} 
                  onChange={e => setCustomAction(e.target.value)}
                  className="search-input"
                  style={{ width: '100%', height: '32px' }}
                >
                  <option value="BUY">BUY</option>
                  <option value="SELL">SELL</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Audit Reason</label>
                <input 
                  type="text" 
                  value={customReason} 
                  onChange={e => setCustomReason(e.target.value)}
                  className="search-input"
                  style={{ width: '100%', height: '32px' }}
                />
              </div>

              <button 
                type="submit" 
                className="flat-btn" 
                style={{ width: '100%', height: '34px', marginTop: '0.5rem', background: customAction === 'BUY' ? 'var(--success)' : 'var(--danger)' }}
                disabled={isSubmittingCustom}
              >
                <Plus size={14} /> {isSubmittingCustom ? 'Verifying Sizing...' : `Submit Live ${customAction}`}
              </button>
            </form>
          </div>

          {/* Safety Checklist Card */}
          <div className="card-panel">
            <h3 className="section-title" style={{ marginBottom: '0.85rem' }}>E2E Safety Rule Constraints</h3>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Market Open Check:</span>
                <strong>09:15 - 15:30 IST Mon-Fri</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Internet Connectivity:</span>
                <strong>Required</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Upstox API Session:</span>
                <strong>Required (24h Expire)</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Single-Stock Concentration Cap:</span>
                <strong>&lt; 20.0% Portfolio Value</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Cash Margin Cover:</span>
                <strong>Required</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Duplicate Order Cover:</span>
                <strong>Required (5 Min Span)</strong>
              </div>
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}
