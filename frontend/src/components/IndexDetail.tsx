import React, { useEffect, useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import { createChart, LineSeries } from 'lightweight-charts';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

const TIMEFRAMES = ['1D', '1W', '1M', '3M', '6M', '1Y', '5Y', 'MAX'] as const;
type Timeframe = typeof TIMEFRAMES[number];

interface IndexData {
  symbol: string;
  provider_ticker: string;
  name: string;
  price: number | null;
  change: number | null;
  history_close: number[];
  history_dates: string[];
}

function IndexChart({ prices, dates }: { prices: number[]; dates: string[] }) {
  const ref = React.useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || prices.length < 2) return;
    const chart = createChart(ref.current, {
      width: ref.current.clientWidth,
      height: 280,
      layout: { background: { color: '#0E1322' }, textColor: '#9CA3AF' },
      grid: { vertLines: { color: '#1F2937' }, horzLines: { color: '#1F2937' } },
      timeScale: { borderVisible: false },
      rightPriceScale: { borderVisible: false },
    });
    const line = chart.addSeries(LineSeries, { color: '#10B981', lineWidth: 2 });
    const seen = new Set<string>();
    const data = dates
      .map((date, idx) => ({ time: date.substring(0, 10), value: prices[idx] }))
      .filter((point) => {
        if (seen.has(point.time) || point.value == null) return false;
        seen.add(point.time);
        return true;
      })
      .sort((a, b) => a.time.localeCompare(b.time));
    line.setData(data);
    const resize = () => {
      if (ref.current) chart.applyOptions({ width: ref.current.clientWidth });
    };
    window.addEventListener('resize', resize);
    return () => {
      window.removeEventListener('resize', resize);
      chart.remove();
    };
  }, [prices, dates]);

  return <div ref={ref} style={{ width: '100%', height: 280 }} />;
}

export default function IndexDetail({ symbol, onClose }: { symbol: string; onClose: () => void }) {
  const [timeframe, setTimeframe] = useState<Timeframe>('1M');
  const [data, setData] = useState<IndexData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const load = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${API_BASE}/indexes/${encodeURIComponent(symbol)}?period=${timeframe}`);
        if (!res.ok) {
          if (active) setData(null);
          return;
        }
        const payload = await res.json();
        if (active) setData(payload);
      } finally {
        if (active) setLoading(false);
      }
    };
    load();
    return () => {
      active = false;
    };
  }, [symbol, timeframe]);

  return (
    <div className="detail-page">
      <button className="back-btn" onClick={onClose}><ArrowLeft size={16} /> Back</button>
      <div className="card-panel" style={{ margin: '1rem' }}>
        {loading ? (
          <div className="skeleton-line" style={{ height: 280 }} />
        ) : data ? (
          <>
            <div className="detail-header">
              <div>
                <h2>{data.name}</h2>
                <span className="table-ticker">{data.symbol}</span>
              </div>
              <div className="detail-price-block">
                <span className="detail-price">{data.price == null ? 'Unavailable' : data.price.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
                <span className={`detail-change ${(data.change ?? 0) >= 0 ? 'text-bullish' : 'text-bearish'}`}>
                  {data.change == null ? 'Unavailable' : `${data.change >= 0 ? '+' : ''}${data.change.toFixed(2)}%`}
                </span>
              </div>
            </div>
            <div className="chart-timeframes" style={{ margin: '1rem 0' }}>
              {TIMEFRAMES.map((tf) => (
                <button key={tf} className={`tf-btn ${timeframe === tf ? 'active' : ''}`} onClick={() => setTimeframe(tf)}>
                  {tf}
                </button>
              ))}
            </div>
            <IndexChart prices={data.history_close || []} dates={data.history_dates || []} />
          </>
        ) : (
          <div className="empty-state">
            <h3>Index unavailable</h3>
            <p>No live provider data was returned for {symbol}.</p>
          </div>
        )}
      </div>
    </div>
  );
}
