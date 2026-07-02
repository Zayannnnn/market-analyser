import React, { useState, useEffect, useRef } from 'react';
import { Bookmark, ArrowLeft, CheckCircle2, ShieldAlert, Award, Star, BarChart3, HelpCircle, Activity } from 'lucide-react';
import { createChart, LineSeries } from 'lightweight-charts';
import { StockItem, PortfolioItem } from '../App.tsx';

class ChartErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: any, errorInfo: any) {
    console.error("ChartErrorBoundary caught chart rendering crash:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%', height: '220px', background: '#0E1322', border: '1px solid var(--border-color)', borderRadius: '8px', color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
          Price chart temporarily unavailable
        </div>
      );
    }
    return this.props.children;
  }
}


const ChartComponent = ({ prices, dates }: { prices: number[]; dates: string[] }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || !prices || prices.length < 2) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 220,
      layout: {
        background: { color: '#0E1322' },
        textColor: '#9CA3AF',
      },
      grid: {
        vertLines: { color: '#1F2937' },
        horzLines: { color: '#1F2937' },
      },
      timeScale: {
        borderVisible: false,
      },
      rightPriceScale: {
        borderVisible: false,
      },
      handleScale: false,
      handleScroll: false,
    });

    if (!chart || typeof chart.addSeries !== 'function') {
      console.error("Chart initialization failed: addSeries method not supported on chart instance");
      return;
    }

    const lineSeries = chart.addSeries(LineSeries, {
      color: '#10B981',
      lineWidth: 2,
    });

    const data = dates.map((date, idx) => {
      const formattedDate = date.substring(0, 10);
      return {
        time: formattedDate,
        value: prices[idx] || 0,
      };
    });

    const uniqueData = [];
    const seenTimes = new Set();
    for (const item of data) {
      if (!seenTimes.has(item.time)) {
        seenTimes.add(item.time);
        uniqueData.push(item);
      }
    }
    uniqueData.sort((a, b) => a.time.localeCompare(b.time));

    lineSeries.setData(uniqueData);

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [prices, dates]);

  return <div ref={containerRef} style={{ width: '100%', height: '220px' }} />;
};


// Resolve host URL
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
  ? 'http://localhost:8000/api' 
  : '/api';

interface StockDetailProps {
  stock: StockItem;
  providerTicker: string;
  onClose: () => void;
  watchlist: string[];
  onToggleWatchlist: (ticker: string) => void;
  portfolio: PortfolioItem[];
  onAddHolding: (ticker: string, quantity: number, entryPrice: number) => void;
  onRemoveHolding: (ticker: string) => void;
  onShowToast: (message: string, isError?: boolean) => void;
}

interface DetailData {
  ticker: string;
  company_name: string;
  provider_ticker: string;
  price: string;
  change: string;
  volume: number;
  avg_volume: number;
  market_cap: number | null;
  pe_ratio: number | null;
  technical_indicators: {
    rsi: number;
    macd: string;
    sma50: number;
    sma200: number;
    volume_surge: number;
    breakout_detected: boolean;
  };
  history_close: number[];
  history_volume: number[];
  history_dates: string[];
  support: number;
  resistance: number;
  ai_explanation: {
    why_ranked: string;
    bullish_factors: string[];
    risk_factors: string[];
    confidence_level: string;
  };
  news: {
    title: string;
    source: string;
    url: string;
    summary: string;
    published_at: string;
    sentiment_score: number;
  }[];
  sentiment_breakdown: {
    bullish_pct: number;
    bearish_pct: number;
    neutral_pct: number;
  };
  valuation_score: number;
  growth_score: number;
  risk_score: number;
  recommendation: string;
  is_halal: boolean;
  score?: number;
  sector?: string;
}

export default function StockDetail({
  stock,
  providerTicker,
  onClose,
  watchlist,
  onToggleWatchlist,
  portfolio,
  onAddHolding,
  onRemoveHolding,
  onShowToast
}: StockDetailProps) {
  const [timeframe, setTimeframe] = useState<'1D' | '1W' | '1M' | '3M' | '6M' | '1Y' | '5Y' | 'MAX'>('1M');
  const [detailData, setDetailData] = useState<DetailData | null>(null);
  const [chartHistory, setChartHistory] = useState<{ history_close: number[]; history_volume: number[]; history_dates: string[] } | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isChartLoading, setIsChartLoading] = useState<boolean>(true);
  const [qtyInput, setQtyInput] = useState<string>('');
  const [costInput, setCostInput] = useState<string>('');

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartStateRef = useRef({ zoom: 1, pan: 0, isDragging: false, startX: 0 });
  const mousePosRef = useRef({ x: -1, y: -1, active: false });

  const isBookmarked = watchlist.includes(stock.ticker);
  const userHolding = portfolio.find(item => item.ticker === stock.ticker);

  // Load live stock detail (no synthetic fallback)
  useEffect(() => {
    let active = true;
    const fetchDetail = async () => {
      setIsLoading(true);
      try {
        const params = new URLSearchParams({
          selected_company: stock.company_name || stock.ticker,
        });
        console.log('Selected Company', stock.company_name);
        console.log('Selected Ticker', stock.ticker);
        console.log('Provider Ticker', providerTicker);
        const res = await fetch(`${API_BASE}/stocks/${stock.ticker}?${params.toString()}`);
        if (res.ok) {
          const data = await res.json();
          console.log('Resolved Ticker', data.ticker);
          console.log('Provider Ticker', data.provider_ticker);
          if (active) {
            setDetailData(data);
          }
        } else {
          onShowToast(`Failed to retrieve details for ${stock.ticker}.`, true);
        }
      } catch (err) {
        console.error(err);
        onShowToast('Network error loading stock detail metadata.', true);
      } finally {
        if (active) setIsLoading(false);
      }
    };
    fetchDetail();
    return () => {
      active = false;
    };
  }, [stock.ticker, stock.company_name, providerTicker]);

  // Load chart history when timeframe changes
  useEffect(() => {
    let active = true;
    const fetchHistory = async () => {
      setIsChartLoading(true);
      try {
        const res = await fetch(`${API_BASE}/stocks/${stock.ticker}/history?period=${timeframe}`);
        if (res.ok) {
          const data = await res.json();
          if (active) {
            setChartHistory({
              history_close: data.history_close || [],
              history_volume: data.history_volume || [],
              history_dates: data.history_dates || [],
            });
          }
        } else {
          if (active) setChartHistory(null);
        }
      } catch (err) {
        console.error(err);
        if (active) setChartHistory(null);
      } finally {
        if (active) setIsChartLoading(false);
      }
    };
    fetchHistory();
    return () => {
      active = false;
    };
  }, [stock.ticker, timeframe]);

  // High-performance canvas area price and volume plot
  const drawChart = () => {
    const canvas = canvasRef.current;
    if (!canvas || !chartHistory) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    
    // Scale canvas resolution
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);

    ctx.clearRect(0, 0, width, height);

    const prices = chartHistory.history_close || [];
    const volumes = chartHistory.history_volume || [];
    const dates = chartHistory.history_dates || [];
    const pointsCount = prices.length;
    
    if (pointsCount < 2) return;

    const zoom = chartStateRef.current.zoom;
    const pan = chartStateRef.current.pan;

    const slicedPrices = prices;
    const slicedVolumes = volumes;
    const slicedDates = dates;
    const slicedCount = slicedPrices.length;

    const minPrice = Math.min(...slicedPrices);
    const maxPrice = Math.max(...slicedPrices);
    const priceRange = maxPrice - minPrice === 0 ? 10 : maxPrice - minPrice;

    const maxVolume = Math.max(...slicedVolumes) || 1;

    // Margins
    const padXLeft = 15;
    const padXRight = 60;
    const padYTop = 30;
    const padYBottom = 30;
    
    const graphWidth = width - padXLeft - padXRight;
    const graphHeight = height - padYTop - padYBottom;

    // Map points to canvas coordinates
    const coords: { x: number; y: number }[] = [];
    for (let i = 0; i < slicedCount; i++) {
      const rawX = padXLeft + (graphWidth / (slicedCount - 1)) * i;
      // Apply zoom & pan centered on graph midpoint
      const x = (rawX - width / 2) * zoom + width / 2 + pan;
      const y = padYTop + graphHeight - ((slicedPrices[i] - minPrice) / priceRange) * graphHeight;
      coords.push({ x, y });
    }

    // Gridlines background
    ctx.strokeStyle = '#1F2937';
    ctx.lineWidth = 1;
    ctx.setLineDash([]);
    for (let i = 0; i < 4; i++) {
      const yGrid = padYTop + (graphHeight / 3) * i;
      ctx.beginPath();
      ctx.moveTo(padXLeft, yGrid);
      ctx.lineTo(width - padXRight, yGrid);
      ctx.stroke();

      // Right axis labels
      ctx.fillStyle = '#9CA3AF';
      ctx.font = '9px monospace';
      const labelVal = maxPrice - (priceRange / 3) * i;
      ctx.fillText(`₹${labelVal.toLocaleString("en-IN", { maximumFractionDigits: 1 })}`, width - padXRight + 6, yGrid + 3);
    }

    // Plot volume bars scaled to bottom 15% height
    ctx.fillStyle = 'rgba(59, 130, 246, 0.08)';
    const barWidth = Math.max(1, (graphWidth / slicedCount) * 0.7 * zoom);
    for (let i = 0; i < slicedCount; i++) {
      const c = coords[i];
      if (c.x < padXLeft || c.x > width - padXRight) continue;
      const volHeight = (slicedVolumes[i] / maxVolume) * (graphHeight * 0.15);
      const volY = padYTop + graphHeight - volHeight;
      ctx.fillRect(c.x - barWidth / 2, volY, barWidth, volHeight);
    }

    // Draw Support (Green line)
    const supportVal = detailData?.support || 0;
    if (supportVal && supportVal >= minPrice && supportVal <= maxPrice) {
      const supY = padYTop + graphHeight - ((supportVal - minPrice) / priceRange) * graphHeight;
      ctx.strokeStyle = 'rgba(16, 185, 129, 0.4)';
      ctx.lineWidth = 1.2;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(padXLeft, supY);
      ctx.lineTo(width - padXRight, supY);
      ctx.stroke();

      ctx.fillStyle = 'var(--success)';
      ctx.font = '9px var(--font-sans)';
      ctx.fillText(`SUP: ₹${supportVal.toFixed(1)}`, padXLeft + 5, supY - 4);
    }

    // Draw Resistance (Red line)
    const resistanceVal = detailData?.resistance || 0;
    if (resistanceVal && resistanceVal >= minPrice && resistanceVal <= maxPrice) {
      const resY = padYTop + graphHeight - ((resistanceVal - minPrice) / priceRange) * graphHeight;
      ctx.strokeStyle = 'rgba(239, 68, 68, 0.4)';
      ctx.lineWidth = 1.2;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(padXLeft, resY);
      ctx.lineTo(width - padXRight, resY);
      ctx.stroke();

      ctx.fillStyle = 'var(--danger)';
      ctx.font = '9px var(--font-sans)';
      ctx.fillText(`RES: ₹${resistanceVal.toFixed(1)}`, padXLeft + 5, resY - 4);
    }

    // Reset line dash
    ctx.setLineDash([]);

    // Gradient fill area
    const isBullish = !detailData?.change?.includes('-');
    const lineColor = isBullish ? '#10B981' : '#EF4444';
    const grad = ctx.createLinearGradient(0, padYTop, 0, padYTop + graphHeight);
    grad.addColorStop(0, isBullish ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)');
    grad.addColorStop(1, 'rgba(11, 15, 25, 0)');

    ctx.beginPath();
    ctx.moveTo(coords[0].x, padYTop + graphHeight);
    coords.forEach(c => ctx.lineTo(c.x, c.y));
    ctx.lineTo(coords[coords.length - 1].x, padYTop + graphHeight);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // Plot stroke line
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(coords[0].x, coords[0].y);
    for (let i = 1; i < coords.length; i++) {
      const xc = (coords[i].x + coords[i - 1].x) / 2;
      const yc = (coords[i].y + coords[i - 1].y) / 2;
      ctx.quadraticCurveTo(coords[i - 1].x, coords[i - 1].y, xc, yc);
    }
    ctx.lineTo(coords[coords.length - 1].x, coords[coords.length - 1].y);
    ctx.stroke();

    // Draw interactive crosshair vertical/horizontal line and tooltip
    if (mousePosRef.current.active && mousePosRef.current.x >= padXLeft && mousePosRef.current.x <= width - padXRight) {
      const mouseX = mousePosRef.current.x;
      
      // Find closest index point
      let closestIdx = 0;
      let minDistance = Infinity;
      for (let i = 0; i < coords.length; i++) {
        const dist = Math.abs(coords[i].x - mouseX);
        if (dist < minDistance) {
          minDistance = dist;
          closestIdx = i;
        }
      }

      const closestPoint = coords[closestIdx];
      if (closestPoint.x >= padXLeft && closestPoint.x <= width - padXRight) {
        // Draw crosshair lines
        ctx.strokeStyle = '#4B5563';
        ctx.lineWidth = 0.8;
        ctx.setLineDash([2, 3]);

        // Vertical line
        ctx.beginPath();
        ctx.moveTo(closestPoint.x, padYTop);
        ctx.lineTo(closestPoint.x, padYTop + graphHeight);
        ctx.stroke();

        // Horizontal line
        ctx.beginPath();
        ctx.moveTo(padXLeft, closestPoint.y);
        ctx.lineTo(width - padXRight, closestPoint.y);
        ctx.stroke();

        // Dot indicator
        ctx.fillStyle = lineColor;
        ctx.setLineDash([]);
        ctx.beginPath();
        ctx.arc(closestPoint.x, closestPoint.y, 4, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = '#FFFFFF';
        ctx.lineWidth = 1;
        ctx.stroke();

        // Date indicator tooltip bubble at the bottom
        ctx.fillStyle = '#1F2937';
        ctx.fillRect(closestPoint.x - 35, padYTop + graphHeight + 4, 70, 16);
        ctx.fillStyle = '#FFFFFF';
        ctx.font = '8px monospace';
        ctx.textAlign = 'center';
        ctx.fillText(slicedDates[closestIdx], closestPoint.x, padYTop + graphHeight + 15);

        // Price indicator tooltip bubble on right axis
        ctx.fillStyle = '#1F2937';
        ctx.fillRect(width - padXRight + 2, closestPoint.y - 8, 56, 16);
        ctx.fillStyle = '#FFFFFF';
        ctx.textAlign = 'left';
        ctx.fillText(`₹${slicedPrices[closestIdx].toFixed(1)}`, width - padXRight + 6, closestPoint.y + 3);
      }
    }
  };

  useEffect(() => {
    if (!isChartLoading && chartHistory && detailData) {
      drawChart();
    }
  }, [isChartLoading, chartHistory, detailData, timeframe]);

  // Drag pan controls
  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    chartStateRef.current.isDragging = true;
    chartStateRef.current.startX = e.clientX - chartStateRef.current.pan;
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    mousePosRef.current = { x, y, active: true };

    if (chartStateRef.current.isDragging) {
      chartStateRef.current.pan = e.clientX - chartStateRef.current.startX;
    }
    drawChart();
  };

  const handleMouseLeave = () => {
    chartStateRef.current.isDragging = false;
    mousePosRef.current.active = false;
    drawChart();
  };

  const handleWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.08 : 0.92;
    chartStateRef.current.zoom = Math.max(0.6, Math.min(6, chartStateRef.current.zoom * zoomFactor));
    drawChart();
  };

  // Submit Position Holding
  const handleHoldingSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const qty = parseFloat(qtyInput);
    const entry = parseFloat(costInput);
    
    if (isNaN(qty) || qty <= 0 || isNaN(entry) || entry <= 0) {
      onShowToast("Please enter a valid quantity and cost value.", true);
      return;
    }
    
    onAddHolding(stock.ticker, qty, entry);
    setQtyInput('');
    setCostInput('');
  };

  if (isLoading) {
    return (
      <div className="detail-page">
        <button className="back-btn" onClick={onClose}><ArrowLeft size={16} /> Back</button>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', padding: '1rem' }}>
          <div className="skeleton-line" style={{ width: '180px', height: '2.2rem' }}></div>
          <div className="skeleton-line" style={{ width: '320px', height: '1rem' }}></div>
          <div className="skeleton-line" style={{ height: '260px', marginTop: '1rem' }}></div>
        </div>
      </div>
    );
  }

  if (!detailData) {
    return (
      <div className="detail-page">
        <button className="back-btn" onClick={onClose}><ArrowLeft size={16} /> Back</button>
        <div className="empty-state">
          <HelpCircle size={40} className="empty-state-icon" />
          <h3>Error Loading Dataset</h3>
          <p>No valid stock intelligence matches found for symbol {stock.ticker}.</p>
        </div>
      </div>
    );
  }

  // Sentiment bar calculations
  const sentiment = detailData?.sentiment_breakdown || { bullish_pct: 40, neutral_pct: 40, bearish_pct: 20 };
  const ai = detailData?.ai_explanation || { why_ranked: 'Opportunity stock listing.', bullish_factors: [], risk_factors: [] };
  const techIndicators = detailData?.technical_indicators || stock?.technical_indicators || { rsi: 50, macd: 'Neutral', sma50: 0, sma200: 0, volume_surge: 1.0, breakout_detected: false };
  const rec = detailData?.recommendation || 'Hold';
  const isIndex = (detailData?.ticker || stock?.ticker || '').startsWith('^');
  const timeframes = ['1D', '1W', '1M', '3M', '6M', '1Y', '5Y', 'MAX'] as const;
  const formatMarketCap = (value: number | null | undefined) => value && value > 0 ? `₹${value.toFixed(2)} B` : 'Unavailable';
  const formatPeRatio = (value: number | null | undefined) => value && value > 0 ? value.toFixed(2) : 'Unavailable';
  const formatSector = (value: string | null | undefined) => value || 'Unavailable';

  const getRecBadgeClass = (recText: string) => {
    const text = recText.toLowerCase();
    if (text.includes('strong buy')) return 'badge-success';
    if (text.includes('buy')) return 'badge-success';
    if (text.includes('hold')) return 'badge-warning';
    return 'badge-danger';
  };

  return (
    <div className="detail-page">
      {/* ========================================================================= */}
      {/* 1. Mobile-Only Layout */}
      {/* ========================================================================= */}
      <div className="mobile-only-layout">
        
        {/* Custom Mobile Header */}
        <div className="mobile-detail-nav-header">
          <button className="back-btn-mobile" onClick={onClose}>
            ← Back to Dashboard
          </button>
          <div className="mobile-detail-nav-title">
            <span className="mobile-detail-name">{detailData.company_name}</span>
            <span className="mobile-detail-ticker">({detailData.ticker})</span>
          </div>
          <div className="mobile-detail-nav-badges">
            {!isIndex && (
              <span className={`badge ${detailData.is_halal ? 'badge-success' : 'badge-danger'}`} style={{ fontSize: '0.62rem' }}>
                {detailData.is_halal ? 'SHARIAH COMPLIANT' : 'SHARIAH NON-COMPLIANT'}
              </span>
            )}
            {isIndex && (
              <span className="badge badge-success" style={{ fontSize: '0.62rem' }}>
                ASSET TYPE: INDEX
              </span>
            )}
            <span className={`badge ${getRecBadgeClass(rec)}`} style={{ fontSize: '0.62rem' }}>
              {rec.toUpperCase()}
            </span>
          </div>
        </div>

        {/* 1. Price Summary */}
        <div className="mobile-price-summary">
          <span className="mobile-price">{detailData.price}</span>
          <span className={`mobile-change ${!detailData.change?.includes('-') ? 'text-bullish' : 'text-bearish'}`}>
            {detailData.change}
          </span>
        </div>

        {/* 2. Price Chart */}
        <div className="mobile-chart-section">
          <div className="chart-timeframes" style={{ marginBottom: '0.65rem', justifyContent: 'flex-start', flexWrap: 'wrap' }}>
            {timeframes.map(tf => (
              <button 
                key={tf} 
                className={`tf-btn ${timeframe === tf ? 'active' : ''}`}
                onClick={() => setTimeframe(tf)}
              >
                {tf}
              </button>
            ))}
          </div>
          <ChartErrorBoundary>
            {isChartLoading || !chartHistory ? (
              <div className="skeleton-line" style={{ height: '220px' }} />
            ) : (
              <ChartComponent prices={chartHistory.history_close || []} dates={chartHistory.history_dates || []} />
            )}
          </ChartErrorBoundary>
        </div>

        {/* 3. AI Score & Corporate Metrics */}
        <div className="mobile-ai-score-card">
          <span className="card-label">AI Score</span>
          <span className="card-value">{detailData.score || stock.score}/100</span>
          
          {isIndex ? (
            <div style={{ marginTop: '0.75rem', fontSize: '0.82rem', fontWeight: 700, color: 'var(--success)' }}>
              Asset Type: Index
            </div>
          ) : (
            <div className="mobile-metrics-grid">
              <div className="metric-item">
                <span className="metric-label">Current Price</span>
                <span className="metric-value">
                  {detailData.price}
                </span>
              </div>
              <div className="metric-item">
                <span className="metric-label">Market Capital</span>
                <span className="metric-value">
                  {formatMarketCap(detailData.market_cap)}
                </span>
              </div>
              <div className="metric-item">
                <span className="metric-label">P/E Ratio</span>
                <span className="metric-value">
                  {formatPeRatio(detailData.pe_ratio)}
                </span>
              </div>
              <div className="metric-item">
                <span className="metric-label">Sector</span>
                <span className="metric-value" style={{ fontSize: '0.75rem' }}>
                  {formatSector(detailData.sector)}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* 4. Bullish Drivers */}
        <div className="factor-box">
          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--success)', letterSpacing: '0.05em' }}>BULLISH DRIVERS</span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.25rem' }}>
            {ai.bullish_factors && ai.bullish_factors.length > 0 ? (
              ai.bullish_factors.map((factor, i) => (
                <div key={i} className="factor-item">
                  <CheckCircle2 size={13} className="text-bullish" style={{ flexShrink: 0, marginTop: '0.15rem' }} />
                  <span>{factor}</span>
                </div>
              ))
            ) : (
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>No major bullish drivers registered.</span>
            )}
          </div>
        </div>

        {/* 5. Risks / Headwinds */}
        <div className="factor-box">
          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--danger)', letterSpacing: '0.05em' }}>RISKS / HEADWINDS</span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.25rem' }}>
            {ai.risk_factors && ai.risk_factors.length > 0 ? (
              ai.risk_factors.map((factor, i) => (
                <div key={i} className="factor-item">
                  <ShieldAlert size={13} className="text-bearish" style={{ flexShrink: 0, marginTop: '0.15rem' }} />
                  <span>{factor}</span>
                </div>
              ))
            ) : (
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>No critical risk factors registered.</span>
            )}
          </div>
        </div>

        {/* 6. Technical Indicators */}
        <div className="card-panel">
          <h3 className="section-title"><BarChart3 size={16} /> Technical Indicators</h3>
          
          <div className="mobile-gauge-grid">
            {/* RSI */}
            <div className="gauge-card">
              <span className="gauge-title">RSI (14)</span>
              <div className="gauge-display" style={{ marginTop: '0.35rem' }}>
                <svg width="60" height="35" style={{ display: 'block' }}>
                  <path d="M 5 30 A 25 25 0 0 1 55 30" fill="none" stroke="#1F2937" strokeWidth="6" strokeLinecap="round" />
                  <path 
                    d="M 5 30 A 25 25 0 0 1 55 30" 
                    fill="none" 
                    stroke={techIndicators.rsi >= 70 ? 'var(--danger)' : techIndicators.rsi <= 30 ? 'var(--success)' : 'var(--warning)'} 
                    strokeWidth="6" 
                    strokeLinecap="round" 
                    strokeDasharray={2 * Math.PI * 25}
                    strokeDashoffset={(2 * Math.PI * 25) * (1 - (techIndicators.rsi / 100))}
                  />
                </svg>
                <span className="gauge-value">{Math.round(techIndicators.rsi)}</span>
              </div>
              <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                {techIndicators.rsi >= 70 ? 'OVERBOUGHT' : techIndicators.rsi <= 30 ? 'OVERSOLD' : 'NEUTRAL ZONE'}
              </span>
            </div>

            {/* MACD */}
            <div className="gauge-card">
              <span className="gauge-title">MACD State</span>
              <span style={{ fontSize: '1rem', fontWeight: 800, margin: '0.5rem 0', color: (techIndicators?.macd || '').toLowerCase().includes('bull') ? 'var(--success)' : 'var(--danger)' }}>
                {(techIndicators?.macd || 'NEUTRAL').toUpperCase()}
              </span>
              <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', fontWeight: 600 }}>TREND SIGNAL</span>
            </div>

            {/* SMAs */}
            <div className="gauge-card">
              <span className="gauge-title">SMA 50 vs 200</span>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem', margin: '0.4rem 0' }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>50: ₹{techIndicators.sma50 ? techIndicators.sma50.toFixed(1) : '--'}</span>
                <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>200: ₹{techIndicators.sma200 ? techIndicators.sma200.toFixed(1) : '--'}</span>
              </div>
              <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                {techIndicators.sma50 > techIndicators.sma200 ? (
                  <span className="text-bullish">BULLISH ALIGNMENT</span>
                ) : (
                  <span className="text-bearish">BEARISH ALIGNMENT</span>
                )}
              </span>
            </div>
          </div>
        </div>

        {/* 7. Position Holdings (Safe bottom placement) */}
        {!isIndex && (
          <div className="card-panel">
            <h3 className="section-title"><Bookmark size={16} /> Asset holdings position</h3>
            {userHolding ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                  <div style={{ padding: '0.65rem', background: 'rgba(255,255,255,0.02)', borderRadius: '4px' }}>
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>Shares Owned</div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, marginTop: '0.2rem' }}>{userHolding.quantity}</div>
                  </div>
                  <div style={{ padding: '0.65rem', background: 'rgba(255,255,255,0.02)', borderRadius: '4px' }}>
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>Avg Buy Cost</div>
                    <div style={{ fontSize: '1rem', fontWeight: 700, marginTop: '0.2rem' }}>
                      ₹{userHolding.entryPrice.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                    </div>
                  </div>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-color)', paddingTop: '0.75rem' }}>
                  <div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>Profit / Loss</div>
                    {(() => {
                      const currentPriceClean = parseFloat(detailData.price.replace(/[^\d.]/g, '')) || userHolding.entryPrice;
                      const profit = (currentPriceClean - userHolding.entryPrice) * userHolding.quantity;
                      const profitPct = (profit / (userHolding.entryPrice * userHolding.quantity)) * 100;
                      return (
                        <div className={profit >= 0 ? 'text-bullish' : 'text-bearish'} style={{ fontSize: '0.95rem', fontWeight: 700, marginTop: '0.15rem' }}>
                          {profit >= 0 ? '+' : ''}₹{profit.toLocaleString("en-IN", { minimumFractionDigits: 2 })} ({profit >= 0 ? '+' : ''}{profitPct.toFixed(2)}%)
                        </div>
                      );
                    })()}
                  </div>
                  <button 
                    className="flat-btn" 
                    style={{ background: 'none', border: '1px solid var(--danger-border)', color: 'var(--danger)', height: '28px', fontSize: '0.7rem' }}
                    onClick={() => onRemoveHolding(detailData.ticker)}
                  >
                    Clear Position
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleHoldingSubmit} className="form-inline" style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', alignItems: 'stretch' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                  <div className="form-input-group" style={{ flex: 1 }}>
                    <label>Quantity</label>
                    <input 
                      type="number" 
                      placeholder="e.g. 50" 
                      value={qtyInput}
                      onChange={(e) => setQtyInput(e.target.value)}
                      required
                      style={{ width: '100%' }}
                    />
                  </div>
                  <div className="form-input-group" style={{ flex: 1 }}>
                    <label>Entry Price (₹)</label>
                    <input 
                      type="number" 
                      placeholder="Average price"
                      value={costInput}
                      onChange={(e) => setCostInput(e.target.value)}
                      required
                      style={{ width: '100%' }}
                    />
                  </div>
                </div>
                <button type="submit" className="flat-btn" style={{ width: '100%' }}>Add Position</button>
              </form>
            )}
          </div>
        )}

        {/* 8. Sentiment & News Breakdown */}
        <div className="card-panel">
          <h3 className="section-title">Sentiment breakdown</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.5rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontWeight: 600 }}>
              <span className="text-bullish">Bullish {sentiment.bullish_pct}%</span>
              <span className="text-neutral">Neutral {sentiment.neutral_pct}%</span>
              <span className="text-bearish">Bearish {sentiment.bearish_pct}%</span>
            </div>
            <div style={{ display: 'flex', height: '6px', borderRadius: '3px', overflow: 'hidden' }}>
              <div style={{ width: `${sentiment.bullish_pct}%`, backgroundColor: 'var(--success)' }}></div>
              <div style={{ width: `${sentiment.neutral_pct}%`, backgroundColor: 'var(--text-secondary)' }}></div>
              <div style={{ width: `${sentiment.bearish_pct}%`, backgroundColor: 'var(--danger)' }}></div>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1.25rem' }}>
            <span style={{ fontSize: '0.68rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Ticker Ingested News Feed</span>
            {detailData?.news && detailData.news.length > 0 ? (
              detailData.news.slice(0, 3).map((item, idx) => (
                <div key={idx} style={{ paddingBottom: '0.5rem', borderBottom: idx < 2 ? '1px solid var(--border-color)' : 'none' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                    <span>{item.source}</span>
                    <span>{item.published_at.substring(0, 10)}</span>
                  </div>
                  <a href={item.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: '0.78rem', color: 'var(--text-primary)', textDecoration: 'none', fontWeight: 600 }}>
                    {item.title}
                  </a>
                </div>
              ))
            ) : (
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>No recent news matched this stock symbol.</span>
            )}
          </div>
        </div>

      </div>

      {/* ========================================================================= */}
      {/* 2. Desktop-Only Layout */}
      {/* ========================================================================= */}
      <div className="desktop-only-layout">
        
        {/* Header controls */}
        <div>
          <button className="back-btn" onClick={onClose}><ArrowLeft size={16} /> Back to Dashboard</button>
          <div className="detail-header">
            <div>
              <div className="detail-title-block">
                <span className="detail-ticker">{detailData.ticker}</span>
                {!isIndex && (
                  detailData.is_halal ? (
                    <span className="badge badge-success" style={{ fontSize: '0.62rem' }}>SHARIAH COMPLIANT</span>
                  ) : (
                    <span className="badge badge-danger" style={{ fontSize: '0.62rem' }}>SHARIAH NON-COMPLIANT</span>
                  )
                )}
                {isIndex && (
                  <span className="badge badge-success" style={{ fontSize: '0.62rem' }}>ASSET TYPE: INDEX</span>
                )}
                <span className={`badge ${getRecBadgeClass(rec)}`} style={{ fontSize: '0.62rem' }}>
                  {rec.toUpperCase()}
                </span>
              </div>
              <div className="detail-name">{detailData.company_name}</div>
            </div>

            <div className="detail-actions">
              <button 
                className={`watchlist-btn ${isBookmarked ? 'active' : ''}`}
                onClick={() => onToggleWatchlist(detailData.ticker)}
              >
                <Star size={13} fill={isBookmarked ? 'currentColor' : 'none'} />
                {isBookmarked ? 'Watched' : 'Watchlist'}
              </button>
              
              <div className="detail-price-block">
                <span className="detail-price">{detailData.price}</span>
                <span className={`detail-change ${!detailData.change?.includes('-') ? 'text-bullish' : 'text-bearish'}`}>
                  {detailData.change}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Interactive Area Chart Panel */}
        <div className="card-panel chart-panel">
          <div className="chart-header">
            <span style={{ fontSize: '0.75rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.35rem', color: 'var(--text-secondary)' }}>
              <Activity size={14} className="text-bullish" />
              Interactive Historical Close Stream
            </span>
            <div className="chart-timeframes">
              {timeframes.map(tf => (
                <button 
                  key={tf} 
                  className={`tf-btn ${timeframe === tf ? 'active' : ''}`}
                  onClick={() => setTimeframe(tf)}
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>

          <div 
            className="canvas-container"
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={() => { chartStateRef.current.isDragging = false; }}
            onMouseLeave={handleMouseLeave}
            onWheel={handleWheel}
          >
            <canvas ref={canvasRef} style={{ display: 'block', width: '100%', height: '100%' }}></canvas>
            {isChartLoading && (
              <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)', fontSize: '0.8rem' }}>
                Loading chart...
              </div>
            )}
          </div>
        </div>

        {/* Metrics Cards Row */}
        <section className="metrics-row">
          <div className="info-card">
            <span className="info-card-label">AI Score</span>
            <span className="info-card-value" style={{ color: 'var(--info)' }}>{detailData.score || stock.score}/100</span>
          </div>
          {isIndex ? (
            <div className="info-card">
              <span className="info-card-label">Asset Type</span>
              <span className="info-card-value" style={{ color: 'var(--success)' }}>Index</span>
            </div>
          ) : (
            <>
              <div className="info-card">
                <span className="info-card-label">Current Price</span>
                <span className="info-card-value">{detailData.price}</span>
              </div>
              <div className="info-card">
                <span className="info-card-label">Market Capital</span>
                <span className="info-card-value">
                  {formatMarketCap(detailData.market_cap)}
                </span>
              </div>
              <div className="info-card">
                <span className="info-card-label">P/E Ratio</span>
                <span className="info-card-value">
                  {formatPeRatio(detailData.pe_ratio)}
                </span>
              </div>
              <div className="info-card">
                <span className="info-card-label">Sector</span>
                <span className="info-card-value" style={{ fontSize: '0.9rem', padding: '0.15rem 0' }}>{formatSector(detailData.sector)}</span>
              </div>
            </>
          )}
        </section>

        {/* Split Grid */}
        <div className="detail-grid">
          
          {/* Left Column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            
            {/* AI Opportunity Hypothesis */}
            <div className="card-panel">
              <h3 className="section-title"><Award size={16} /> AI Investment Hypothesis</h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.5', fontStyle: 'italic', marginBottom: '1.25rem' }}>
                {ai.why_ranked}
              </p>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                {/* Bullish */}
                <div className="factor-box">
                  <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--success)', letterSpacing: '0.05em' }}>BULLISH DRIVERS</span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.25rem' }}>
                    {ai.bullish_factors && ai.bullish_factors.length > 0 ? (
                      ai.bullish_factors.map((factor, i) => (
                        <div key={i} className="factor-item">
                          <CheckCircle2 size={13} className="text-bullish" style={{ flexShrink: 0, marginTop: '0.15rem' }} />
                          <span>{factor}</span>
                        </div>
                      ))
                    ) : (
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>No major bullish drivers registered.</span>
                    )}
                  </div>
                </div>

                {/* Headwinds */}
                <div className="factor-box">
                  <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--danger)', letterSpacing: '0.05em' }}>RISKS / HEADWINDS</span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.25rem' }}>
                    {ai.risk_factors && ai.risk_factors.length > 0 ? (
                      ai.risk_factors.map((factor, i) => (
                        <div key={i} className="factor-item">
                          <ShieldAlert size={13} className="text-bearish" style={{ flexShrink: 0, marginTop: '0.15rem' }} />
                          <span>{factor}</span>
                        </div>
                      ))
                    ) : (
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>No critical risk factors registered.</span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Technical indicators grid */}
            <div className="card-panel">
              <h3 className="section-title"><BarChart3 size={16} /> Technical Indicators</h3>
              
              <div className="gauge-grid">
                {/* RSI gauge */}
                <div className="gauge-card">
                  <span className="gauge-title">RSI (14)</span>
                  <div className="gauge-display" style={{ marginTop: '0.35rem' }}>
                    <svg width="60" height="35" style={{ display: 'block' }}>
                      <path d="M 5 30 A 25 25 0 0 1 55 30" fill="none" stroke="#1F2937" strokeWidth="6" strokeLinecap="round" />
                      <path 
                        d="M 5 30 A 25 25 0 0 1 55 30" 
                        fill="none" 
                        stroke={techIndicators.rsi >= 70 ? 'var(--danger)' : techIndicators.rsi <= 30 ? 'var(--success)' : 'var(--warning)'} 
                        strokeWidth="6" 
                        strokeLinecap="round" 
                        strokeDasharray={2 * Math.PI * 25}
                        strokeDashoffset={(2 * Math.PI * 25) * (1 - (techIndicators.rsi / 100))}
                      />
                    </svg>
                    <span className="gauge-value">{Math.round(techIndicators.rsi)}</span>
                  </div>
                  <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                    {techIndicators.rsi >= 70 ? 'OVERBOUGHT' : techIndicators.rsi <= 30 ? 'OVERSOLD' : 'NEUTRAL ZONE'}
                  </span>
                </div>

                {/* MACD */}
                <div className="gauge-card">
                  <span className="gauge-title">MACD State</span>
                  <span style={{ fontSize: '1rem', fontWeight: 800, margin: '0.5rem 0', color: (techIndicators?.macd || '').toLowerCase().includes('bull') ? 'var(--success)' : 'var(--danger)' }}>
                    {(techIndicators?.macd || 'NEUTRAL').toUpperCase()}
                  </span>
                  <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', fontWeight: 600 }}>TREND SIGNAL</span>
                </div>

                {/* SMAs */}
                <div className="gauge-card">
                  <span className="gauge-title">SMA 50 vs 200</span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.15rem', margin: '0.4rem 0' }}>
                    <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>50: ₹{techIndicators.sma50 ? techIndicators.sma50.toFixed(1) : '--'}</span>
                    <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>200: ₹{techIndicators.sma200 ? techIndicators.sma200.toFixed(1) : '--'}</span>
                  </div>
                  <span style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
                    {techIndicators.sma50 > techIndicators.sma200 ? (
                      <span className="text-bullish">BULLISH ALIGNMENT</span>
                    ) : (
                      <span className="text-bearish">BEARISH ALIGNMENT</span>
                    )}
                  </span>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginTop: '1rem' }}>
                <div style={{ padding: '0.75rem', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', borderRadius: '6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Volume Surge:</span>
                  <span style={{ fontSize: '0.85rem', fontWeight: 700, color: (techIndicators.volume_surge || 1) > 1.5 ? 'var(--success)' : 'var(--text-primary)' }}>
                    {techIndicators.volume_surge ? techIndicators.volume_surge.toFixed(2) : '1.00'}x
                  </span>
                </div>
                <div style={{ padding: '0.75rem', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', borderRadius: '6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Breakout Status:</span>
                  <span style={{ fontSize: '0.72rem', fontWeight: 700 }}>
                    {techIndicators.breakout_detected ? (
                      <span className="badge badge-success">DETECTED</span>
                    ) : (
                      <span className="badge badge-danger">NONE</span>
                    )}
                  </span>
                </div>
              </div>
            </div>

          </div>

          {/* Right Column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            
            {/* Portfolio position manager */}
            {!isIndex && (
              <div className="card-panel">
                <h3 className="section-title"><Bookmark size={16} /> Asset holdings position</h3>
                
                {userHolding ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
                      <div style={{ padding: '0.65rem', background: 'rgba(255,255,255,0.02)', borderRadius: '4px' }}>
                        <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>Shares Owned</div>
                        <div style={{ fontSize: '1rem', fontWeight: 700, marginTop: '0.2rem' }}>{userHolding.quantity}</div>
                      </div>
                      <div style={{ padding: '0.65rem', background: 'rgba(255,255,255,0.02)', borderRadius: '4px' }}>
                        <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>Avg Buy Cost</div>
                        <div style={{ fontSize: '1rem', fontWeight: 700, marginTop: '0.2rem' }}>
                          ₹{userHolding.entryPrice.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-color)', paddingTop: '0.75rem' }}>
                      <div>
                        <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)' }}>Profit / Loss</div>
                        {(() => {
                          const currentPriceClean = parseFloat(detailData.price.replace(/[^\d.]/g, '')) || userHolding.entryPrice;
                          const profit = (currentPriceClean - userHolding.entryPrice) * userHolding.quantity;
                          const profitPct = (profit / (userHolding.entryPrice * userHolding.quantity)) * 100;
                          
                          return (
                            <div className={profit >= 0 ? 'text-bullish' : 'text-bearish'} style={{ fontSize: '0.95rem', fontWeight: 700, marginTop: '0.15rem' }}>
                              {profit >= 0 ? '+' : ''}₹{profit.toLocaleString("en-IN", { minimumFractionDigits: 2 })} ({profit >= 0 ? '+' : ''}{profitPct.toFixed(2)}%)
                            </div>
                          );
                        })()}
                      </div>

                      <button 
                        className="flat-btn" 
                        style={{ background: 'none', border: '1px solid var(--danger-border)', color: 'var(--danger)', height: '28px', fontSize: '0.7rem' }}
                        onClick={() => {
                          onRemoveHolding(detailData.ticker);
                        }}
                      >
                        Clear Position
                      </button>
                    </div>
                  </div>
                ) : (
                  <form onSubmit={handleHoldingSubmit} className="form-inline" style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem', alignItems: 'stretch' }}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                      <div className="form-input-group" style={{ flex: 1 }}>
                        <label>Quantity</label>
                        <input 
                          type="number" 
                          placeholder="e.g. 50" 
                          value={qtyInput}
                          onChange={(e) => setQtyInput(e.target.value)}
                          required
                          style={{ width: '100%' }}
                        />
                      </div>
                      <div className="form-input-group" style={{ flex: 1 }}>
                        <label>Entry Price (₹)</label>
                        <input 
                          type="number" 
                          placeholder="Average price"
                          value={costInput}
                          onChange={(e) => setCostInput(e.target.value)}
                          required
                          style={{ width: '100%' }}
                        />
                      </div>
                    </div>
                    <button type="submit" className="flat-btn" style={{ width: '100%' }}>Add Position</button>
                  </form>
                )}
              </div>
            )}

            {/* Sentiment Gauge Stacked */}
            <div className="card-panel">
              <h3 className="section-title">Sentiment breakdown</h3>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontWeight: 600 }}>
                  <span className="text-bullish">Bullish {sentiment.bullish_pct}%</span>
                  <span className="text-neutral">Neutral {sentiment.neutral_pct}%</span>
                  <span className="text-bearish">Bearish {sentiment.bearish_pct}%</span>
                </div>
                <div style={{ display: 'flex', height: '6px', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: `${sentiment.bullish_pct}%`, backgroundColor: 'var(--success)' }}></div>
                  <div style={{ width: `${sentiment.neutral_pct}%`, backgroundColor: 'var(--text-secondary)' }}></div>
                  <div style={{ width: `${sentiment.bearish_pct}%`, backgroundColor: 'var(--danger)' }}></div>
                </div>
              </div>

              {/* Ingested News List */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1.25rem' }}>
                <span style={{ fontSize: '0.68rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Ticker Ingested News Feed</span>
                {detailData?.news && detailData.news.length > 0 ? (
                  detailData.news.slice(0, 3).map((item, idx) => (
                    <div key={idx} style={{ paddingBottom: '0.5rem', borderBottom: idx < 2 ? '1px solid var(--border-color)' : 'none' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: '0.2rem' }}>
                        <span>{item.source}</span>
                        <span>{item.published_at.substring(0, 10)}</span>
                      </div>
                      <a href={item.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: '0.78rem', color: 'var(--text-primary)', textDecoration: 'none', fontWeight: 600 }}>
                        {item.title}
                      </a>
                    </div>
                  ))
                ) : (
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>No recent news matched this stock symbol.</span>
                )}
              </div>
            </div>

          </div>

        </div>

      </div>

    </div>
  );
}
