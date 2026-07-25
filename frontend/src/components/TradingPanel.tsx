import React, { useState, useEffect } from 'react';
import { Play, X, Shield, ShieldAlert, ShieldCheck, AlertTriangle, RefreshCw, Trash2, Edit, CheckCircle2, TrendingUp, Info } from 'lucide-react';

interface TradingPanelProps {
  apiBase: string;
  onShowToast: (message: string, isError?: boolean) => void;
}

interface AIReview {
  confidence: number;
  recommendation: string;
  risk: string;
  expected_reward: string;
  suggested_quantity: number;
  reasons: string[];
  warnings: string[];
}

export default function TradingPanel({ apiBase, onShowToast }: TradingPanelProps) {
  const [ticker, setTicker] = useState('BEL');
  const [quantity, setQuantity] = useState(10);
  const [side, setSide] = useState<'BUY' | 'SELL'>('BUY');
  const [orderType, setOrderType] = useState<'MARKET' | 'LIMIT'>('MARKET');
  const [price, setPrice] = useState('250.00');
  
  // Loading & Flow State
  const [loadingReview, setLoadingReview] = useState(false);
  const [aiReview, setAiReview] = useState<AIReview | null>(null);
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [executingOrder, setExecutingOrder] = useState(false);
  const [orderSuccess, setOrderSuccess] = useState<string | null>(null);
  
  // Data lists
  const [orders, setOrders] = useState<any[]>([]);
  const [positions, setPositions] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  
  const [loadingData, setLoadingData] = useState(false);
  const [activeTab, setActiveTab] = useState<'positions' | 'orders' | 'history'>('positions');

  // Load telemetry data from backend
  const loadTradingData = async () => {
    setLoadingData(true);
    try {
      // 1. Fetch positions
      const posRes = await fetch(`${apiBase}/trading/positions`);
      if (posRes.ok) {
        const pData = await posRes.json();
        setPositions(pData.positions || []);
      }
      
      // 2. Fetch orders
      const ordRes = await fetch(`${apiBase}/trading/orders`);
      if (ordRes.ok) {
        const oData = await ordRes.json();
        setOrders(oData.orders || []);
      }
      
      // 3. Fetch history
      const histRes = await fetch(`${apiBase}/trading/history`);
      if (histRes.ok) {
        const hData = await histRes.json();
        setHistory(hData.history || []);
      }
    } catch (err) {
      console.error("Failed to load trading lists:", err);
      onShowToast("Failed to sync broker trading data.", true);
    } finally {
      setLoadingData(false);
    }
  };

  useEffect(() => {
    loadTradingData();
    const interval = setInterval(loadTradingData, 30000);
    return () => clearInterval(interval);
  }, []);

  // Price estimator for calculations
  const numericPrice = parseFloat(price) || 0.0;
  const rawTotal = quantity * numericPrice;
  const brokerage = 20.00; // Flat flat brokerage fee
  const taxes = rawTotal * 0.0015; // Estimated 0.15% STT + stamp duty + exchange charges
  const totalCashRequired = rawTotal + brokerage + taxes;

  const handleRequestReview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticker.trim()) {
      onShowToast("Please specify a stock ticker symbol.", true);
      return;
    }
    if (quantity <= 0) {
      onShowToast("Quantity must be greater than zero.", true);
      return;
    }
    if (orderType === 'LIMIT' && numericPrice <= 0) {
      onShowToast("Limit price must be greater than zero.", true);
      return;
    }

    setLoadingReview(true);
    setAiReview(null);
    setShowReviewModal(true);
    setOrderSuccess(null);

    try {
      const payload = {
        ticker: ticker.toUpperCase().strip ? ticker.toUpperCase().trim() : ticker.toUpperCase(),
        quantity: parseInt(quantity.toString()),
        side: side,
        price: orderType === 'LIMIT' ? parseFloat(price) : null,
        order_type: orderType
      };

      const response = await fetch(`${apiBase}/trading/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (response.ok) {
        const data = await response.json();
        setAiReview(data);
      } else {
        const error = await response.text();
        onShowToast(`Failed to generate AI Review: ${error}`, true);
        setShowReviewModal(false);
      }
    } catch (err) {
      onShowToast("Error communicating with AI Review Engine.", true);
      setShowReviewModal(false);
    } finally {
      setLoadingReview(false);
    }
  };

  const handleConfirmOrder = async () => {
    if (!aiReview) return;
    setExecutingOrder(true);
    setOrderSuccess(null);

    try {
      // Choose correct API endpoint based on Side and OrderType
      let endpoint = '';
      if (orderType === 'MARKET') {
        endpoint = side === 'BUY' ? '/trading/buy' : '/trading/sell';
      } else {
        endpoint = side === 'BUY' ? '/trading/limit-buy' : '/trading/limit-sell';
      }

      const payload: any = {
        ticker: ticker.toUpperCase().trim ? ticker.toUpperCase().trim() : ticker.toUpperCase(),
        quantity: parseInt(quantity.toString()),
        product: "D"
      };
      if (orderType === 'LIMIT') {
        payload.price = parseFloat(price);
      }

      const response = await fetch(`${apiBase}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (response.ok && data.status === 'success') {
        setOrderSuccess(data.order_id);
        onShowToast(`Order successfully placed! ID: ${data.order_id}`);
        // Refresh telemetry lists
        setTimeout(loadTradingData, 1500);
      } else {
        onShowToast(`Order Placement Rejected: ${data.detail || data.message || 'Unknown broker rejection.'}`, true);
      }
    } catch (err) {
      onShowToast("Network exception placing order.", true);
    } finally {
      setExecutingOrder(false);
    }
  };

  const handleCancelOrder = async (orderId: string) => {
    if (!window.confirm(`Are you sure you want to cancel order ${orderId}?`)) return;
    
    try {
      const response = await fetch(`${apiBase}/trading/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order_id: orderId })
      });
      const data = await response.json();
      if (response.ok && data.status === 'success') {
        onShowToast(`Order ${orderId} successfully cancelled.`);
        loadTradingData();
      } else {
        onShowToast(`Cancel Failed: ${data.detail || data.message}`, true);
      }
    } catch (err) {
      onShowToast("Network error cancelling order.", true);
    }
  };

  return (
    <div className="trading-container" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', minHeight: 'calc(100vh - 120px)' }}>
      
      {/* Title Panel */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 className="section-title" style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <TrendingUp size={22} className="text-bullish" /> AI-Assisted Trading Panel
          </h2>
          <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
            Execute real-time order placements on Upstox with strict safety guards and multi-agent AI verification.
          </p>
        </div>
        <button 
          onClick={loadTradingData} 
          disabled={loadingData}
          className="flat-btn flat-btn-outline" 
          style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', height: '32px', fontSize: '0.75rem' }}
        >
          <RefreshCw size={12} className={loadingData ? 'spin' : ''} /> Refresh Data
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.8fr', gap: '1.5rem' }}>
        
        {/* Trading Panel Form */}
        <div className="card-panel" style={{ height: 'fit-content' }}>
          <h3 style={{ fontSize: '0.95rem', margin: '0 0 1rem 0', fontWeight: 700, color: 'var(--text-primary)' }}>Order Entry</h3>
          
          <form onSubmit={handleRequestReview} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            
            {/* Buy / Sell Toggle */}
            <div>
              <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem', fontWeight: 600 }}>TRANSACTION TYPE</label>
              <div style={{ display: 'flex', background: 'rgba(255,255,255,0.03)', padding: '3px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.06)' }}>
                <button
                  type="button"
                  onClick={() => setSide('BUY')}
                  style={{
                    flex: 1,
                    padding: '8px',
                    borderRadius: '4px',
                    border: 'none',
                    fontSize: '0.8rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    background: side === 'BUY' ? 'rgba(16, 185, 129, 0.15)' : 'transparent',
                    color: side === 'BUY' ? '#10B981' : 'var(--text-secondary)',
                    transition: 'all 0.2s'
                  }}
                >
                  BUY
                </button>
                <button
                  type="button"
                  onClick={() => setSide('SELL')}
                  style={{
                    flex: 1,
                    padding: '8px',
                    borderRadius: '4px',
                    border: 'none',
                    fontSize: '0.8rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    background: side === 'SELL' ? 'rgba(239, 68, 68, 0.15)' : 'transparent',
                    color: side === 'SELL' ? '#EF4444' : 'var(--text-secondary)',
                    transition: 'all 0.2s'
                  }}
                >
                  SELL
                </button>
              </div>
            </div>

            {/* Ticker Symbol */}
            <div>
              <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem', fontWeight: 600 }}>STOCK SYMBOL</label>
              <input 
                type="text" 
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder="e.g. RELIANCE, TCS, BEL"
                style={{
                  width: '100%',
                  padding: '10px',
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: '6px',
                  color: 'var(--text-primary)',
                  fontWeight: 700,
                  fontSize: '0.88rem'
                }}
              />
            </div>

            {/* Order Type Toggle */}
            <div>
              <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem', fontWeight: 600 }}>ORDER TYPE</label>
              <div style={{ display: 'flex', background: 'rgba(255,255,255,0.03)', padding: '3px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.06)' }}>
                <button
                  type="button"
                  onClick={() => setOrderType('MARKET')}
                  style={{
                    flex: 1,
                    padding: '6px',
                    borderRadius: '4px',
                    border: 'none',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    background: orderType === 'MARKET' ? 'rgba(255,255,255,0.08)' : 'transparent',
                    color: orderType === 'MARKET' ? 'var(--text-primary)' : 'var(--text-secondary)',
                  }}
                >
                  MARKET
                </button>
                <button
                  type="button"
                  onClick={() => setOrderType('LIMIT')}
                  style={{
                    flex: 1,
                    padding: '6px',
                    borderRadius: '4px',
                    border: 'none',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    cursor: 'pointer',
                    background: orderType === 'LIMIT' ? 'rgba(255,255,255,0.08)' : 'transparent',
                    color: orderType === 'LIMIT' ? 'var(--text-primary)' : 'var(--text-secondary)',
                  }}
                >
                  LIMIT
                </button>
              </div>
            </div>

            {/* Quantity and Price */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
              <div>
                <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem', fontWeight: 600 }}>QUANTITY</label>
                <input 
                  type="number" 
                  min="1"
                  value={quantity}
                  onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                  style={{
                    width: '100%',
                    padding: '10px',
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: '6px',
                    color: 'var(--text-primary)',
                    fontWeight: 700,
                    fontSize: '0.85rem'
                  }}
                />
              </div>
              <div>
                <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.4rem', fontWeight: 600 }}>PRICE (₹)</label>
                <input 
                  type="text" 
                  disabled={orderType === 'MARKET'}
                  value={orderType === 'MARKET' ? 'LTP (Market)' : price}
                  onChange={(e) => setPrice(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px',
                    background: orderType === 'MARKET' ? 'rgba(255,255,255,0.01)' : 'rgba(255,255,255,0.02)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: '6px',
                    color: orderType === 'MARKET' ? 'var(--text-secondary)' : 'var(--text-primary)',
                    fontWeight: 700,
                    fontSize: '0.85rem'
                  }}
                />
              </div>
            </div>

            {/* Financial Calculations breakdown */}
            <div style={{ background: 'rgba(255,255,255,0.015)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: '6px', padding: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                <span>Subtotal ({quantity} x ₹{orderType === 'MARKET' ? 'LTP' : numericPrice.toFixed(2)})</span>
                <span>₹{orderType === 'MARKET' ? 'Calculated at LTP' : rawTotal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                <span>Estimated Brokerage Fee</span>
                <span>₹{brokerage.toFixed(2)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                <span>Taxes & Stamp Duties</span>
                <span>{orderType === 'MARKET' ? 'Est ~0.15%' : `₹${taxes.toFixed(2)}`}</span>
              </div>
              <hr style={{ border: 'none', borderTop: '1px solid rgba(255,255,255,0.06)', margin: '0.3rem 0' }} />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                <span>Estimated Cash Required</span>
                <span>{orderType === 'MARKET' ? 'Pending LTP' : `₹${totalCashRequired.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`}</span>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              className="flat-btn"
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '6px',
                border: 'none',
                fontWeight: 700,
                fontSize: '0.88rem',
                cursor: 'pointer',
                background: side === 'BUY' ? 'linear-gradient(135deg, #10B981, #059669)' : 'linear-gradient(135deg, #EF4444, #DC2626)',
                color: 'white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.4rem',
                boxShadow: side === 'BUY' ? '0 4px 12px rgba(16, 185, 129, 0.2)' : '0 4px 12px rgba(239, 68, 68, 0.2)'
              }}
            >
              <Play size={14} /> REVIEW {side} ORDER
            </button>
          </form>
        </div>

        {/* Workspace Portfolio telemetry and active lists */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          
          <div className="card-panel" style={{ flex: 1, minHeight: '380px', display: 'flex', flexDirection: 'column' }}>
            
            {/* Tabs */}
            <div style={{ display: 'flex', borderBottom: '1px solid rgba(255,255,255,0.08)', marginBottom: '1rem', gap: '1rem' }}>
              <button
                onClick={() => setActiveTab('positions')}
                style={{
                  padding: '8px 4px',
                  background: 'none',
                  border: 'none',
                  fontSize: '0.82rem',
                  fontWeight: activeTab === 'positions' ? 700 : 500,
                  color: activeTab === 'positions' ? 'var(--text-primary)' : 'var(--text-secondary)',
                  borderBottom: activeTab === 'positions' ? '2px solid var(--info)' : 'none',
                  cursor: 'pointer'
                }}
              >
                Positions ({positions.length})
              </button>
              <button
                onClick={() => setActiveTab('orders')}
                style={{
                  padding: '8px 4px',
                  background: 'none',
                  border: 'none',
                  fontSize: '0.82rem',
                  fontWeight: activeTab === 'orders' ? 700 : 500,
                  color: activeTab === 'orders' ? 'var(--text-primary)' : 'var(--text-secondary)',
                  borderBottom: activeTab === 'orders' ? '2px solid var(--info)' : 'none',
                  cursor: 'pointer'
                }}
              >
                Open Orders ({orders.length})
              </button>
              <button
                onClick={() => setActiveTab('history')}
                style={{
                  padding: '8px 4px',
                  background: 'none',
                  border: 'none',
                  fontSize: '0.82rem',
                  fontWeight: activeTab === 'history' ? 700 : 500,
                  color: activeTab === 'history' ? 'var(--text-primary)' : 'var(--text-secondary)',
                  borderBottom: activeTab === 'history' ? '2px solid var(--info)' : 'none',
                  cursor: 'pointer'
                }}
              >
                Order Logs ({history.length})
              </button>
            </div>

            {/* List panel */}
            <div style={{ flex: 1, overflowY: 'auto' }}>
              
              {loadingData && (
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', gap: '0.5rem', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                  <RefreshCw size={14} className="spin" /> Synchronizing data...
                </div>
              )}

              {!loadingData && activeTab === 'positions' && (
                positions.length > 0 ? (
                  <div className="table-container">
                    <table className="premium-table">
                      <thead>
                        <tr>
                          <th>Symbol</th>
                          <th>Qty</th>
                          <th>Buy Price</th>
                          <th>LTP</th>
                          <th>PnL</th>
                        </tr>
                      </thead>
                      <tbody>
                        {positions.map((p, idx) => {
                          const pnl = parseFloat(p.pnl) || 0.0;
                          const tickerSymbol = p.trading_symbol || p.ticker || p.tradingsymbol || 'Unknown';
                          return (
                            <tr key={idx}>
                              <td style={{ fontWeight: 700 }}>{tickerSymbol}</td>
                              <td>{p.quantity || p.qty}</td>
                              <td>₹{parseFloat(p.average_price || p.averagePrice || 0).toFixed(2)}</td>
                              <td>₹{parseFloat(p.last_price || p.ltp || 0).toFixed(2)}</td>
                              <td className={pnl >= 0 ? 'text-bullish' : 'text-bearish'} style={{ fontWeight: 700 }}>
                                {pnl >= 0 ? '+' : ''}{pnl.toFixed(2)}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div style={{ padding: '3rem 1rem', textShadow: 'none', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                    No open positions detected in this session.
                  </div>
                )
              )}

              {!loadingData && activeTab === 'orders' && (
                orders.length > 0 ? (
                  <div className="table-container">
                    <table className="premium-table">
                      <thead>
                        <tr>
                          <th>Symbol</th>
                          <th>Side</th>
                          <th>Type</th>
                          <th>Qty</th>
                          <th>Price</th>
                          <th>Status</th>
                          <th>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {orders.map((o, idx) => (
                          <tr key={idx}>
                            <td style={{ fontWeight: 700 }}>{o.trading_symbol || o.ticker}</td>
                            <td style={{ color: o.transaction_type === 'BUY' ? '#10B981' : '#EF4444', fontWeight: 700 }}>{o.transaction_type}</td>
                            <td>{o.order_type}</td>
                            <td>{o.quantity}</td>
                            <td>₹{parseFloat(o.price || 0).toFixed(2)}</td>
                            <td>
                              <span className={`badge ${o.status === 'open' || o.status === 'validation pending' ? 'badge-warning' : 'badge-danger'}`}>
                                {o.status.toUpperCase()}
                              </span>
                            </td>
                            <td>
                              {(o.status === 'open' || o.status === 'validation pending') && (
                                <button
                                  onClick={() => handleCancelOrder(o.order_id)}
                                  style={{
                                    background: 'none',
                                    border: 'none',
                                    color: '#EF4444',
                                    cursor: 'pointer',
                                    padding: '4px'
                                  }}
                                  title="Cancel Order"
                                >
                                  <Trash2 size={13} />
                                </button>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div style={{ padding: '3rem 1rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                    No active/open orders found.
                  </div>
                )
              )}

              {!loadingData && activeTab === 'history' && (
                history.length > 0 ? (
                  <div className="table-container">
                    <table className="premium-table">
                      <thead>
                        <tr>
                          <th>Symbol</th>
                          <th>Side</th>
                          <th>Qty</th>
                          <th>Avg Price</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {history.map((h, idx) => (
                          <tr key={idx}>
                            <td style={{ fontWeight: 700 }}>{h.trading_symbol || h.ticker}</td>
                            <td style={{ color: h.transaction_type === 'BUY' ? '#10B981' : '#EF4444', fontWeight: 700 }}>{h.transaction_type}</td>
                            <td>{h.quantity}</td>
                            <td>₹{parseFloat(h.average_price || 0).toFixed(2)}</td>
                            <td>
                              <span className={`badge ${h.status === 'complete' || h.status === 'filled' ? 'badge-success' : 'badge-danger'}`}>
                                {h.status.toUpperCase()}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div style={{ padding: '3rem 1rem', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                    Order execution log history is empty.
                  </div>
                )
              )}
            </div>
          </div>
        </div>
      </div>

      {/* AI Trade Review Dialog Modal */}
      {showReviewModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(5, 8, 15, 0.85)',
          backdropFilter: 'blur(12px)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 9999,
          padding: '1.5rem'
        }}>
          
          <div className="card-panel" style={{ width: '100%', maxWidth: '620px', padding: '1.5rem', maxHeight: '90vh', overflowY: 'auto', border: '1px solid rgba(255,255,255,0.08)' }}>
            
            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.2rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <Shield size={18} className="text-bullish" />
                <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 800 }}>AI Decision Briefing & Safety Constraint Audit</h3>
              </div>
              <button 
                onClick={() => setShowReviewModal(false)}
                disabled={executingOrder}
                style={{ background: 'none', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}
              >
                <X size={18} />
              </button>
            </div>

            {loadingReview && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem', padding: '3rem 1rem' }}>
                <div className="skeleton-loader" style={{ width: '60px', height: '60px', borderRadius: '50%', border: '4px solid rgba(255,255,255,0.03)', borderTopColor: 'var(--info)', animation: 'spin 1s linear infinite' }}></div>
                <div style={{ textAlign: 'center' }}>
                  <p style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>AORA AI Analyst at Work...</p>
                  <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
                    Compiling RSI, MACD overlays, news sentiment matrices, cash exposures and stop-loss targets...
                  </p>
                </div>
              </div>
            )}

            {!loadingReview && aiReview && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
                
                {/* Executive Verdict Badge */}
                <div style={{
                  background: 'rgba(255,255,255,0.015)',
                  border: '1px solid rgba(255,255,255,0.04)',
                  borderRadius: '8px',
                  padding: '1rem',
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr 1fr',
                  gap: '1rem',
                  textAlign: 'center'
                }}>
                  <div>
                    <span style={{ fontSize: '0.62rem', color: 'var(--text-secondary)', display: 'block', fontWeight: 600 }}>RECOMMENDATION</span>
                    <span style={{
                      fontSize: '1.3rem',
                      fontWeight: 900,
                      color: aiReview.recommendation === 'BUY' ? '#10B981' : aiReview.recommendation === 'SELL' ? '#EF4444' : '#F59E0B'
                    }}>
                      {aiReview.recommendation}
                    </span>
                  </div>
                  <div>
                    <span style={{ fontSize: '0.62rem', color: 'var(--text-secondary)', display: 'block', fontWeight: 600 }}>CONFIDENCE LEVEL</span>
                    <span style={{ fontSize: '1.3rem', fontWeight: 900, color: 'var(--info)' }}>
                      {aiReview.confidence}%
                    </span>
                  </div>
                  <div>
                    <span style={{ fontSize: '0.62rem', color: 'var(--text-secondary)', display: 'block', fontWeight: 600 }}>RISK SCORE</span>
                    <span style={{
                      fontSize: '1.3rem',
                      fontWeight: 900,
                      color: aiReview.risk === 'High' ? '#EF4444' : aiReview.risk === 'Medium' ? '#F59E0B' : '#10B981'
                    }}>
                      {aiReview.risk}
                    </span>
                  </div>
                </div>

                {/* Sizing & Reward guidelines */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.2fr', gap: '1rem', fontSize: '0.78rem' }}>
                  <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)', borderRadius: '6px', padding: '0.6rem' }}>
                    <span style={{ display: 'block', fontSize: '0.62rem', color: 'var(--text-secondary)', fontWeight: 600 }}>SUGGESTED QUANTITY</span>
                    <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)' }}>{aiReview.suggested_quantity} shares</span>
                  </div>
                  <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)', borderRadius: '6px', padding: '0.6rem' }}>
                    <span style={{ display: 'block', fontSize: '0.62rem', color: 'var(--text-secondary)', fontWeight: 600 }}>EXPECTED TARGET REWARD</span>
                    <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)' }}>{aiReview.expected_reward}</span>
                  </div>
                </div>

                {/* Key Justification Reasons */}
                <div>
                  <h4 style={{ fontSize: '0.78rem', margin: '0 0 0.5rem 0', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    <ShieldCheck size={14} className="text-bullish" /> Key Justifications
                  </h4>
                  <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                    {aiReview.reasons.map((r, i) => <li key={i}>{r}</li>)}
                  </ul>
                </div>

                {/* Warnings / Risk Guidelines */}
                {aiReview.warnings && aiReview.warnings.length > 0 && (
                  <div style={{ background: 'rgba(245, 158, 11, 0.03)', border: '1px solid rgba(245, 158, 11, 0.08)', borderRadius: '6px', padding: '0.75rem' }}>
                    <h4 style={{ fontSize: '0.78rem', margin: '0 0 0.4rem 0', fontWeight: 700, color: '#F59E0B', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                      <AlertTriangle size={14} /> Risk & Capital Warnings
                    </h4>
                    <ul style={{ margin: 0, paddingLeft: '1.2rem', fontSize: '0.72rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                      {aiReview.warnings.map((w, i) => <li key={i}>{w}</li>)}
                    </ul>
                  </div>
                )}

                {/* Success Animation Notification */}
                {orderSuccess && (
                  <div style={{ background: 'rgba(16, 185, 129, 0.04)', border: '1px solid rgba(16, 185, 129, 0.15)', borderRadius: '6px', padding: '0.8rem', textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.4rem' }}>
                    <CheckCircle2 size={32} style={{ color: '#10B981', animation: 'bounce 1s' }} />
                    <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#10B981' }}>Order Placed Successfully!</span>
                    <span style={{ fontSize: '0.65rem', color: 'var(--text-secondary)' }}>Broker Confirmation Order ID: {orderSuccess}</span>
                  </div>
                )}

                {/* Footer Execution Buttons */}
                {!orderSuccess && (
                  <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
                    <button
                      onClick={() => setShowReviewModal(false)}
                      disabled={executingOrder}
                      className="flat-btn flat-btn-outline"
                      style={{ flex: 1, padding: '10px' }}
                    >
                      ABORT
                    </button>
                    <button
                      onClick={handleConfirmOrder}
                      disabled={executingOrder}
                      className="flat-btn"
                      style={{
                        flex: 1.5,
                        padding: '10px',
                        background: side === 'BUY' ? '#10B981' : '#EF4444',
                        color: 'white',
                        fontWeight: 700,
                        border: 'none',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '0.3rem'
                      }}
                    >
                      {executingOrder ? <RefreshCw size={13} className="spin" /> : <ShieldCheck size={14} />}
                      {executingOrder ? 'EXECUTING ORDER...' : `CONFIRM ${side}`}
                    </button>
                  </div>
                )}
                
              </div>
            )}
          </div>
        </div>
      )}

    </div>
  );
}
