import React, { useState, useEffect } from 'react';
import { Routes, Route, useNavigate, useParams } from 'react-router-dom';
import { LayoutDashboard, Briefcase, Bookmark, Clock, Search, AlertCircle } from 'lucide-react';
import Dashboard from './components/Dashboard.tsx';
import StockDetail from './components/StockDetail.tsx';
import IndexDetail from './components/IndexDetail.tsx';

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("ErrorBoundary caught rendering exception:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="detail-page" style={{ padding: '2rem', color: '#EF4444', background: '#0D1321', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '8px', margin: '1rem' }}>
          <h2>Stock Detail Render Failed</h2>
          <pre style={{ marginTop: '1rem', whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: '#9CA3AF', overflowX: 'auto' }}>
            {this.state.error?.stack || this.state.error?.toString()}
          </pre>
        </div>
      );
    }

    return this.props.children;
  }
}


// Resolve host URL
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
  ? 'http://localhost:8000/api' 
  : '/api';

export interface Subscores {
  fundamentals: number;
  news_sentiment: number;
  growth_potential: number;
  valuation: number;
  technical_analysis: number;
}

export interface TechnicalIndicators {
  rsi: number;
  macd: string;
  sma50: number;
  sma200: number;
  volume_surge: number;
  breakout_detected: boolean;
}

export interface AIExplanation {
  why_ranked: string;
  bullish_factors: string[];
  risk_factors: string[];
  confidence_level: string;
}

export interface StockItem {
  rank: number;
  ticker: string;
  company_name: string;
  price: string;
  change: string;
  score: number;
  confidence: string;
  sentiment: string;
  recent_headline: string;
  technical_indicators: TechnicalIndicators;
  ai_explanation: AIExplanation;
  subscores: Subscores;
}

export interface IndexItem {
  price: number;
  change: number;
  history: number[];
}

export interface MarketSummary {
  timestamp: string;
  sp500: IndexItem;
  nasdaq: IndexItem;
  nifty50: IndexItem;
  sensex: IndexItem;
  banknifty: IndexItem;
  summary_text: string;
}

export interface NewsArticle {
  id: string;
  ticker: string;
  title: string;
  url: string;
  source: string;
  summary: string;
  sentiment_score: number;
  impact_level: string;
  published_at: string;
}

export interface PortfolioItem {
  ticker: string;
  quantity: number;
  entryPrice: number;
}

export interface SearchSuggestion {
  ticker: string;
  company_name: string;
  provider_ticker: string;
  sector: string;
}

function StockDetailRoute({
  watchlist,
  portfolio,
  onToggleWatchlist,
  onAddHolding,
  onRemoveHolding,
  onShowToast,
}: {
  watchlist: string[];
  portfolio: PortfolioItem[];
  onToggleWatchlist: (ticker: string) => void;
  onAddHolding: (ticker: string, quantity: number, entryPrice: number) => void;
  onRemoveHolding: (ticker: string) => void;
  onShowToast: (message: string, isError?: boolean) => void;
}) {
  const { ticker = '' } = useParams();
  const navigate = useNavigate();
  const normalizedTicker = decodeURIComponent(ticker).toUpperCase();

  const stock: StockItem = {
    rank: 0,
    ticker: normalizedTicker,
    company_name: normalizedTicker,
    price: 'Unavailable',
    change: 'Unavailable',
    score: 0,
    confidence: 'Medium',
    sentiment: 'Neutral',
    recent_headline: '',
    technical_indicators: {
      rsi: 50,
      macd: 'Neutral',
      sma50: 0,
      sma200: 0,
      volume_surge: 1,
      breakout_detected: false,
    },
    ai_explanation: {
      why_ranked: '',
      bullish_factors: [],
      risk_factors: [],
      confidence_level: 'Medium',
    },
    subscores: {
      fundamentals: 0,
      news_sentiment: 0,
      growth_potential: 0,
      valuation: 0,
      technical_analysis: 0,
    },
  };

  return (
    <ErrorBoundary>
      <StockDetail
        stock={stock}
        providerTicker=""
        onClose={() => navigate('/')}
        watchlist={watchlist}
        onToggleWatchlist={onToggleWatchlist}
        portfolio={portfolio}
        onAddHolding={onAddHolding}
        onRemoveHolding={onRemoveHolding}
        onShowToast={onShowToast}
      />
    </ErrorBoundary>
  );
}

function IndexDetailRoute() {
  const { symbol = '' } = useParams();
  const navigate = useNavigate();
  return <IndexDetail symbol={decodeURIComponent(symbol)} onClose={() => navigate('/')} />;
}

export default function App() {
  const navigate = useNavigate();
  // Global States
  const [activeStocks, setActiveStocks] = useState<StockItem[]>([]);
  const [marketSummary, setMarketSummary] = useState<MarketSummary | null>(null);
  const [newsArticles, setNewsArticles] = useState<NewsArticle[]>([]);
  const [view, setView] = useState<'dashboard' | 'portfolio' | 'watchlist'>('dashboard');
  const [halalOnly, setHalalOnly] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [searchSuggestions, setSearchSuggestions] = useState<SearchSuggestion[]>([]);
  const [showSearchSuggestions, setShowSearchSuggestions] = useState<boolean>(false);
  // Local Storage States
  const [watchlist, setWatchlist] = useState<string[]>(() => {
    return JSON.parse(localStorage.getItem('watchlist') || '[]');
  });
  const [portfolio, setPortfolio] = useState<PortfolioItem[]>(() => {
    return JSON.parse(localStorage.getItem('portfolio') || '[]');
  });

  // Custom add stock form input
  const [addStockInput, setAddStockInput] = useState({ ticker: '', name: '', quality: '75' });

  // User ID for Alerts
  const [userId] = useState<string>(() => {
    let id = localStorage.getItem('userId');
    if (!id) {
      id = 'user_' + Math.random().toString(36).substring(2, 11);
      localStorage.setItem('userId', id);
    }
    return id;
  });

  // Toast State
  const [toast, setToast] = useState<{ show: boolean; message: string; isError: boolean }>({ 
    show: false, 
    message: '', 
    isError: false 
  });

  const triggerToast = (message: string, isError = false) => {
    setToast({ show: true, message, isError });
    setTimeout(() => setToast({ show: false, message: '', isError: false }), 4000);
  };

  // Sync to localStorage
  useEffect(() => {
    localStorage.setItem('watchlist', JSON.stringify(watchlist));
  }, [watchlist]);

  useEffect(() => {
    localStorage.setItem('portfolio', JSON.stringify(portfolio));
  }, [portfolio]);

  // Load API Data
  const loadData = async () => {
    try {
      // 1. Fetch Top 10 Ranked Stocks
      const top10Res = await fetch(`${API_BASE}/top10`);
      if (top10Res.ok) {
        const top10Data = await top10Res.json();
        console.log("top10 response:", top10Data);
        setActiveStocks(top10Data.top_10 || []);
      } else {
        console.error("Failed to fetch top 10 stocks");
      }

      // 2. Fetch Market Overview Indexes
      const summaryRes = await fetch(`${API_BASE}/market-summary`);
      if (summaryRes.ok) {
        const summaryData = await summaryRes.json();
        console.log("marketSummary response:", summaryData);
        setMarketSummary(summaryData);
      } else {
        console.error("Failed to fetch market summary");
      }

      // 3. Fetch News Feed
      const newsRes = await fetch(`${API_BASE}/fetch-news`);
      if (newsRes.ok) {
        const newsData = await newsRes.json();
        setNewsArticles(newsData.articles || []);
      } else {
        console.error("Failed to fetch trending news");
      }
    } catch (e) {
      console.error("API loading failed: ", e);
      triggerToast("Network error. Unable to synchronize platform data.", true);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 120000); // 2 minutes poll
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const query = searchTerm.trim();
    if (!query) {
      setSearchSuggestions([]);
      return;
    }
    let active = true;
    const timer = window.setTimeout(async () => {
      try {
        const res = await fetch(`${API_BASE}/search-stocks?query=${encodeURIComponent(query)}`);
        if (!res.ok) {
          if (active) setSearchSuggestions([]);
          return;
        }
        const data = await res.json();
        const results = data.results || [];
        console.log("search response:", results);
        if (active) {
          setSearchSuggestions(results);
          setShowSearchSuggestions(true);
        }
      } catch (err) {
        console.error("Search failed:", err);
        if (active) setSearchSuggestions([]);
      }
    }, 120);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [searchTerm]);

  // Watchlist Toggle
  const toggleWatchlist = (ticker: string) => {
    if (watchlist.includes(ticker)) {
      setWatchlist(watchlist.filter(t => t !== ticker));
      triggerToast(`Removed ${ticker} from watchlist.`);
    } else {
      setWatchlist([...watchlist, ticker]);
      triggerToast(`Added ${ticker} to watchlist.`);
    }
  };

  // Portfolio holdings additions and removals
  const addHolding = (ticker: string, quantity: number, entryPrice: number) => {
    const existing = portfolio.find(item => item.ticker === ticker);
    if (existing) {
      setPortfolio(portfolio.map(item => 
        item.ticker === ticker 
          ? { 
              ...item, 
              quantity: item.quantity + quantity, 
              entryPrice: ((item.entryPrice * item.quantity) + (entryPrice * quantity)) / (item.quantity + quantity)
            }
          : item
      ));
    } else {
      setPortfolio([...portfolio, { ticker, quantity, entryPrice }]);
    }
    triggerToast(`Added ${quantity} shares of ${ticker} to portfolio.`);
  };

  const removeHolding = (ticker: string) => {
    setPortfolio(portfolio.filter(item => item.ticker !== ticker));
    triggerToast(`Cleared all holdings for ${ticker}.`);
  };

  // Trigger manual backend recalculate
  const handleRecalculate = async () => {
    setIsProcessing(true);
    triggerToast("Triggering analytical pipeline run...");
    try {
      const response = await fetch(`${API_BASE}/analyze-stocks`, { method: "POST" });
      if (response.ok) {
        setTimeout(async () => {
          await loadData();
          setIsProcessing(false);
          triggerToast("Stock rankings updated successfully!");
        }, 8000);
      } else {
        setIsProcessing(false);
        triggerToast("Pipeline calculation trigger failed.", true);
      }
    } catch (e) {
      setIsProcessing(false);
      triggerToast("Error communicating with pipeline API.", true);
    }
  };

  // Add Custom Stock Ticker
  const handleAddStock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addStockInput.ticker || !addStockInput.name) return;
    
    setIsProcessing(true);
    triggerToast(`Registering ${addStockInput.ticker.toUpperCase()} in system...`);
    
    try {
      const qVal = parseFloat(addStockInput.quality);
      const res = await fetch(`${API_BASE}/add-stock?ticker=${addStockInput.ticker.toUpperCase()}&company_name=${encodeURIComponent(addStockInput.name)}&quality_score=${qVal}`, {
        method: "POST"
      });
      if (res.ok) {
        // Run pipeline
        await fetch(`${API_BASE}/analyze-stocks`, { method: "POST" });
        setAddStockInput({ ticker: '', name: '', quality: '75' });
        
        setTimeout(async () => {
          await loadData();
          setIsProcessing(false);
          triggerToast(`Stock ${addStockInput.ticker.toUpperCase()} added & analyzed!`);
        }, 8000);
      } else {
        setIsProcessing(false);
        triggerToast("Failed to register stock ticker.", true);
      }
    } catch (e) {
      setIsProcessing(false);
      triggerToast("Error registering stock.", true);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    triggerToast("Select a stock from the dropdown suggestions to open details.", true);
  };

  const handleSearchSuggestionClick = (suggestion: SearchSuggestion) => {
    console.log('Selected Company', suggestion.company_name);
    console.log('Selected Ticker', suggestion.ticker);
    console.log('Provider Ticker', suggestion.provider_ticker);
    setSearchTerm('');
    setSearchSuggestions([]);
    setShowSearchSuggestions(false);
    navigate(`/stock/${suggestion.ticker}`);
  };

  const openStock = (ticker: string) => {
    if (ticker.startsWith('^')) {
      navigate(`/index/${encodeURIComponent(ticker)}`);
      return;
    }
    navigate(`/stock/${ticker}`);
  };

  return (
    <div className="app-shell">
      {/* Top Navbar */}
      <nav className="top-nav">
        <div className="brand">
          <div className="brand-title">
            <h1>AORA</h1>
            <p>AI Stock Intelligence</p>
          </div>
        </div>

        {/* Search */}
        <form onSubmit={handleSearchSubmit} className="nav-search">
          <Search size={14} className="nav-search-icon" />
          <input 
            type="text" 
            placeholder="Search exact ticker..." 
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setShowSearchSuggestions(true);
            }}
            onFocus={() => setShowSearchSuggestions(true)}
            onBlur={() => window.setTimeout(() => setShowSearchSuggestions(false), 180)}
          />
          {showSearchSuggestions && searchSuggestions.length > 0 && (
            <div className="nav-search-dropdown">
              {searchSuggestions.map((suggestion) => (
                <button
                  type="button"
                  key={suggestion.ticker}
                  className="nav-search-suggestion"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => handleSearchSuggestionClick(suggestion)}
                >
                  <span className="nav-search-ticker">{suggestion.ticker}</span>
                  <span className="nav-search-company">{suggestion.company_name}</span>
                </button>
              ))}
            </div>
          )}
        </form>

        <div className="nav-actions">
          {/* Market open pulse */}
          <div className="market-pulse-text">
            <div className="pulse-dot"></div>
            <span>TERMINAL ACTIVE</span>
          </div>

          {/* Compliance filter */}
          <div className="switch-container" onClick={() => setHalalOnly(!halalOnly)}>
            <div className={`switch-track ${halalOnly ? 'active' : ''}`}>
              <div className="switch-thumb"></div>
            </div>
            <span className="switch-label">SHARIAH ONLY</span>
          </div>

          {/* Tabs */}
          <button 
            className={`flat-btn nav-tab-btn ${view === 'dashboard' ? '' : 'flat-btn-outline'}`}
            style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', height: '30px', padding: '0 0.75rem' }}
            onClick={() => { setView('dashboard'); navigate('/'); }}
          >
            <LayoutDashboard size={13} /> Dashboard
          </button>
          <button 
            className={`flat-btn nav-tab-btn ${view === 'portfolio' ? '' : 'flat-btn-outline'}`}
            style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', height: '30px', padding: '0 0.75rem' }}
            onClick={() => { setView('portfolio'); navigate('/'); }}
          >
            <Briefcase size={13} /> Portfolio ({portfolio.length})
          </button>
          <button 
            className={`flat-btn nav-tab-btn ${view === 'watchlist' ? '' : 'flat-btn-outline'}`}
            style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', height: '30px', padding: '0 0.75rem' }}
            onClick={() => { setView('watchlist'); navigate('/'); }}
          >
            <Bookmark size={13} /> Watchlist ({watchlist.length})
          </button>

          <div className="user-profile" title="User Profile">
            IN
          </div>
        </div>
      </nav>

      {/* Global Ticker Bar */}
      <div className="ticker-ribbon">
        {marketSummary ? (
          <>
            <div className="ribbon-item">
              <span className="ribbon-ticker">NIFTY 50</span>
              <span className="ribbon-price">₹{marketSummary.nifty50.price.toLocaleString("en-IN")}</span>
              <span className={marketSummary.nifty50.change >= 0 ? 'text-bullish' : 'text-bearish'}>
                {marketSummary.nifty50.change >= 0 ? '▲' : '▼'} {marketSummary.nifty50.change.toFixed(2)}%
              </span>
            </div>
            <div className="ribbon-item">
              <span className="ribbon-ticker">SENSEX</span>
              <span className="ribbon-price">₹{marketSummary.sensex.price.toLocaleString("en-IN")}</span>
              <span className={marketSummary.sensex.change >= 0 ? 'text-bullish' : 'text-bearish'}>
                {marketSummary.sensex.change >= 0 ? '▲' : '▼'} {marketSummary.sensex.change.toFixed(2)}%
              </span>
            </div>
            <div className="ribbon-item">
              <span className="ribbon-ticker">BANK NIFTY</span>
              <span className="ribbon-price">₹{marketSummary.banknifty.price.toLocaleString("en-IN")}</span>
              <span className={marketSummary.banknifty.change >= 0 ? 'text-bullish' : 'text-bearish'}>
                {marketSummary.banknifty.change >= 0 ? '▲' : '▼'} {marketSummary.banknifty.change.toFixed(2)}%
              </span>
            </div>
            <div className="ribbon-item">
              <span className="ribbon-ticker">S&P 500</span>
              <span className="ribbon-price">${marketSummary.sp500.price.toLocaleString()}</span>
              <span className={marketSummary.sp500.change >= 0 ? 'text-bullish' : 'text-bearish'}>
                {marketSummary.sp500.change >= 0 ? '▲' : '▼'} {marketSummary.sp500.change.toFixed(2)}%
              </span>
            </div>
            <div className="ribbon-item">
              <span className="ribbon-ticker">NASDAQ</span>
              <span className="ribbon-price">${marketSummary.nasdaq.price.toLocaleString()}</span>
              <span className={marketSummary.nasdaq.change >= 0 ? 'text-bullish' : 'text-bearish'}>
                {marketSummary.nasdaq.change >= 0 ? '▲' : '▼'} {marketSummary.nasdaq.change.toFixed(2)}%
              </span>
            </div>
          </>
        ) : (
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
            <Clock size={10} style={{ display: 'inline', marginRight: '0.25rem' }} /> Synchronizing index tickers from yfinance API...
          </div>
        )}
      </div>

      {/* Main Content Area */}
      <main style={{ flex: 1 }}>
        <Routes>
          <Route
            path="/index/:symbol"
            element={<IndexDetailRoute />}
          />
          <Route
            path="/stock/:ticker"
            element={
              <StockDetailRoute
                watchlist={watchlist}
                portfolio={portfolio}
                onToggleWatchlist={toggleWatchlist}
                onAddHolding={addHolding}
                onRemoveHolding={removeHolding}
                onShowToast={triggerToast}
              />
            }
          />
          <Route
            path="*"
            element={
              <>
                {view === 'dashboard' && (
                  <Dashboard
                    stocks={activeStocks}
                    marketSummary={marketSummary}
                    newsArticles={newsArticles}
                    onSelectStock={(stock) => openStock(stock.ticker)}
                    halalOnly={halalOnly}
                    isProcessing={isProcessing}
                    onRecalculate={handleRecalculate}
                    addStockInput={addStockInput}
                    setAddStockInput={setAddStockInput}
                    onAddStock={handleAddStock}
                    userId={userId}
                    onShowToast={triggerToast}
                  />
                )}

                {view === 'watchlist' && (
                  <div className="dashboard-container">
                    <h2 className="section-title"><Bookmark size={18} /> Watchlist Monitor</h2>
                    <div className="card-panel">
                      {watchlist.length > 0 ? (
                        <div className="table-container">
                          <table className="premium-table">
                            <thead>
                              <tr>
                                <th>Ticker</th>
                                <th>Company Name</th>
                                <th>Current Price</th>
                                <th>Change</th>
                                <th>AI Score</th>
                                <th>Status</th>
                              </tr>
                            </thead>
                            <tbody>
                              {watchlist.map(ticker => {
                                const stock = activeStocks.find(s => s.ticker === ticker);
                                if (!stock) {
                                  return (
                                    <tr key={ticker} onClick={() => openStock(ticker)}>
                                      <td className="table-ticker">{ticker}</td>
                                      <td>Loading custom stock ticker...</td>
                                      <td>--</td>
                                      <td>--</td>
                                      <td>--</td>
                                      <td><span className="badge badge-info">EXTERNAL</span></td>
                                    </tr>
                                  );
                                }
                                const isChangeBearish = stock.change.includes('-');
                                return (
                                  <tr key={ticker} onClick={() => openStock(stock.ticker)}>
                                    <td className="table-ticker">{stock.ticker}</td>
                                    <td>{stock.company_name}</td>
                                    <td className="table-price">{stock.price}</td>
                                    <td className={isChangeBearish ? 'text-bearish' : 'text-bullish'} style={{ fontWeight: 600 }}>
                                      {stock.change}
                                    </td>
                                    <td className="table-score">{stock.score}/100</td>
                                    <td>
                                      {stock.score >= 75 ? (
                                        <span className="badge badge-success">BUY</span>
                                      ) : stock.score >= 55 ? (
                                        <span className="badge badge-warning">HOLD</span>
                                      ) : (
                                        <span className="badge badge-danger">AVOID</span>
                                      )}
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="empty-state">
                          <Bookmark size={40} className="empty-state-icon" />
                          <h3>Your Watchlist is Empty</h3>
                          <p style={{ fontSize: '0.85rem', marginTop: '0.4rem', color: 'var(--text-secondary)' }}>
                            Search stocks or click on rows in the AI Rankings leaderboard, then toggle bookmark stars to watch assets.
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {view === 'portfolio' && (
                  <div className="dashboard-container">
                    <h2 className="section-title"><Briefcase size={18} /> Asset Holdings & Allocations</h2>
                    <div className="card-panel">
                      {portfolio.length > 0 ? (
                        <div className="table-container">
                          <table className="premium-table">
                            <thead>
                              <tr>
                                <th>Ticker</th>
                                <th>Shares Held</th>
                                <th>Avg Entry Cost</th>
                                <th>Market Price</th>
                                <th>Invested Capital</th>
                                <th>Current Value</th>
                                <th>Profit / Loss</th>
                              </tr>
                            </thead>
                            <tbody>
                              {portfolio.map(item => {
                                const stockRef = activeStocks.find(s => s.ticker === item.ticker);
                                const marketPriceVal = stockRef
                                  ? parseFloat(stockRef.price.replace(/[^\d.]/g, ''))
                                  : item.entryPrice;

                                const totalCost = item.quantity * item.entryPrice;
                                const currentValue = item.quantity * marketPriceVal;
                                const profitVal = currentValue - totalCost;
                                const profitPct = totalCost > 0 ? (profitVal / totalCost) * 100 : 0;

                                return (
                                  <tr key={item.ticker} onClick={() => stockRef && openStock(stockRef.ticker)}>
                                    <td className="table-ticker">{item.ticker}</td>
                                    <td>{item.quantity}</td>
                                    <td>₹{item.entryPrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                    <td className="table-price">₹{marketPriceVal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                    <td>₹{totalCost.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                    <td className="table-price">₹{currentValue.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                    <td className={profitVal >= 0 ? 'text-bullish' : 'text-bearish'} style={{ fontWeight: 700 }}>
                                      {profitVal >= 0 ? '+' : ''}₹{profitVal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ({profitVal >= 0 ? '+' : ''}{profitPct.toFixed(2)}%)
                                    </td>
                                  </tr>
                                );
                              })}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <div className="empty-state">
                          <Briefcase size={40} className="empty-state-icon" />
                          <h3>No Open Positions Tracked</h3>
                          <p style={{ fontSize: '0.85rem', marginTop: '0.4rem', color: 'var(--text-secondary)' }}>
                            Add shares inside the stock details page of any asset to track your cost basis, current valuations, and profit analytics.
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </>
            }
          />
        </Routes>
      </main>

      {/* Dynamic Toast Notice */}
      <div className={`toast-notice ${toast.show ? 'show' : ''}`} style={{ borderLeft: `4px solid ${toast.isError ? 'var(--danger)' : 'var(--info)'}` }}>
        {toast.isError && <AlertCircle size={14} className="toast-notice-icon text-bearish" style={{ display: 'inline', verticalAlign: 'middle' }} />}
        <span>{toast.message}</span>
      </div>

      {/* Sticky Bottom Navigation for Mobile */}
      <div className="bottom-nav">
        <button 
          className={`bottom-nav-item ${view === 'dashboard' ? 'active' : ''}`}
          onClick={() => { setView('dashboard'); navigate('/'); }}
        >
          <LayoutDashboard size={20} />
          <span>Dashboard</span>
        </button>
        <button 
          className={`bottom-nav-item ${view === 'portfolio' ? 'active' : ''}`}
          onClick={() => { setView('portfolio'); navigate('/'); }}
        >
          <Briefcase size={20} />
          <span>Portfolio</span>
        </button>
        <button 
          className={`bottom-nav-item ${view === 'watchlist' ? 'active' : ''}`}
          onClick={() => { setView('watchlist'); navigate('/'); }}
        >
          <Bookmark size={20} />
          <span>Watchlist</span>
        </button>
      </div>
    </div>
  );
}
