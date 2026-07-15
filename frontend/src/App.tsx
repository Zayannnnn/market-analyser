import React, { useState, useEffect } from 'react';
import { Routes, Route, useNavigate, useParams } from 'react-router-dom';
import { LayoutDashboard, Briefcase, Bookmark, Clock, Search, AlertCircle, Activity, Play, Cpu, PieChart, Layers, Shield, Server, Settings, Globe, Brain, BookOpen, Award } from 'lucide-react';
import Dashboard from './components/Dashboard.tsx';
import StockDetail from './components/StockDetail.tsx';
import IndexDetail from './components/IndexDetail.tsx';
import PortfolioIntelligence from './components/PortfolioIntelligence.tsx';
import StrategyLab from './components/StrategyLab.tsx';
import PaperTradingDashboard from './components/PaperTradingDashboard.tsx';
import LiveTradingMonitor from './components/LiveTradingMonitor.tsx';
import PortfolioManager from './components/PortfolioManager.tsx';
import OpportunityCenter from './components/OpportunityCenter.tsx';
import LiveExecution from './components/LiveExecution.tsx';
import ProductionHealth from './components/ProductionHealth.tsx';
import UserSettings from './components/UserSettings.tsx';
import PersonalCIO from './components/PersonalCIO.tsx';
import AILearning from './components/AILearning.tsx';
import MarketIntelligence from './components/MarketIntelligence.tsx';
import ResearchEngine from './components/ResearchEngine.tsx';

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
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

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
  const [view, setView] = useState<'cio' | 'dashboard' | 'portfolio' | 'watchlist' | 'strategy_lab' | 'paper_trading' | 'monitor' | 'manager' | 'opportunity' | 'live' | 'health' | 'settings' | 'learning' | 'macro' | 'research'>('cio');
  const [halalOnly, setHalalOnly] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [searchSuggestions, setSearchSuggestions] = useState<SearchSuggestion[]>([]);
  const [showSearchSuggestions, setShowSearchSuggestions] = useState<boolean>(false);
  // Local Storage States
  const [watchlist, setWatchlist] = useState<string[]>(() => {
    return JSON.parse(localStorage.getItem('watchlist') || '[]');
  });
  const [livePortfolio, setLivePortfolio] = useState<any>({
    holdings: [],
    cash_available: 0.0,
    realized_pnl: 0.0,
    unrealized_pnl: 0.0,
    authenticated: false,
    error: "Loading portfolio..."
  });

  const portfolio = (livePortfolio.holdings || []).map((h: any) => ({
    ticker: h.trading_symbol || h.ticker || h.tradingsymbol || '',
    quantity: h.quantity || 0,
    entryPrice: h.average_price || 0.0
  }));


  const [watchlistRankings, setWatchlistRankings] = useState<any[]>([]);
  const [loadingWatchlist, setLoadingWatchlist] = useState<boolean>(false);

  useEffect(() => {
    if (watchlist.length === 0) {
      setWatchlistRankings([]);
      return;
    }
    setLoadingWatchlist(true);
    fetch(`${API_BASE}/watchlist/rank?tickers=${watchlist.join(',')}`)
      .then(res => res.json())
      .then(data => {
        if (data.status === 'success') {
          setWatchlistRankings(data.rankings || []);
        }
        setLoadingWatchlist(false);
      })
      .catch(err => {
        console.error("Error loading watchlist rankings:", err);
        setLoadingWatchlist(false);
      });
  }, [watchlist]);

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

      // 4. Fetch Live Portfolio (Single Source of Truth)
      const portRes = await fetch(`${API_BASE}/portfolio/intelligence`);
      if (portRes.ok) {
        const portData = await portRes.json();
        if (portData.status === 'success' && portData.portfolio) {
          setLivePortfolio(portData.portfolio);
        } else {
          setLivePortfolio({
            holdings: [],
            cash_available: 0.0,
            realized_pnl: 0.0,
            unrealized_pnl: 0.0,
            authenticated: false,
            error: "Broker authentication required."
          });
        }
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
            className={`flat-btn nav-tab-btn ${view === 'cio' ? '' : 'flat-btn-outline'}`}
            style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', height: '30px', padding: '0 0.75rem' }}
            onClick={() => { setView('cio'); navigate('/'); }}
          >
            <Award size={13} /> Personal CIO
          </button>
          <button 
            className={`flat-btn nav-tab-btn ${view === 'learning' ? '' : 'flat-btn-outline'}`}
            style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', height: '30px', padding: '0 0.75rem' }}
            onClick={() => { setView('learning'); navigate('/'); }}
          >
            <Brain size={13} /> AI Learning
          </button>
          <button 
            className={`flat-btn nav-tab-btn ${view === 'macro' ? '' : 'flat-btn-outline'}`}
            style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', height: '30px', padding: '0 0.75rem' }}
            onClick={() => { setView('macro'); navigate('/'); }}
          >
            <Globe size={13} /> Market Intelligence
          </button>
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
          <button 
            className={`flat-btn nav-tab-btn ${view === 'research' ? '' : 'flat-btn-outline'}`}
            style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', height: '30px', padding: '0 0.75rem' }}
            onClick={() => { setView('research'); navigate('/'); }}
          >
            <BookOpen size={13} /> Research Engine
          </button>
          <button 
            className={`flat-btn nav-tab-btn ${view === 'strategy_lab' ? '' : 'flat-btn-outline'}`}
            style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', height: '30px', padding: '0 0.75rem' }}
            onClick={() => { setView('strategy_lab'); navigate('/'); }}
          >
            <Activity size={13} /> Strategy Lab
          </button>
          <button 
            className={`flat-btn nav-tab-btn ${view === 'paper_trading' ? '' : 'flat-btn-outline'}`}
            style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', height: '30px', padding: '0 0.75rem' }}
            onClick={() => { setView('paper_trading'); navigate('/'); }}
          >
            <Play size={13} /> Paper Trading
          </button>
          <button 
            className={`flat-btn nav-tab-btn ${view === 'monitor' ? '' : 'flat-btn-outline'}`}
            style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', height: '30px', padding: '0 0.75rem' }}
            onClick={() => { setView('monitor'); navigate('/'); }}
          >
            <Cpu size={13} /> Monitor
          </button>
          <button 
            className={`flat-btn nav-tab-btn ${view === 'manager' ? '' : 'flat-btn-outline'}`}
            style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', height: '30px', padding: '0 0.75rem' }}
            onClick={() => { setView('manager'); navigate('/'); }}
          >
            <PieChart size={13} /> AI Portfolio Manager
          </button>
          <button 
            className={`flat-btn nav-tab-btn ${view === 'opportunity' ? '' : 'flat-btn-outline'}`}
            style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', height: '30px', padding: '0 0.75rem' }}
            onClick={() => { setView('opportunity'); navigate('/'); }}
          >
            <Layers size={13} /> Opportunity Center
          </button>
          <button 
            className={`flat-btn nav-tab-btn ${view === 'live' ? '' : 'flat-btn-outline'}`}
            style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', height: '30px', padding: '0 0.75rem' }}
            onClick={() => { setView('live'); navigate('/'); }}
          >
            <Shield size={13} /> Live Execution
          </button>
          <button 
            className={`flat-btn nav-tab-btn ${view === 'health' ? '' : 'flat-btn-outline'}`}
            style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', height: '30px', padding: '0 0.75rem' }}
            onClick={() => { setView('health'); navigate('/'); }}
          >
            <Server size={13} /> Production Health
          </button>
          <button 
            className={`flat-btn nav-tab-btn ${view === 'settings' ? '' : 'flat-btn-outline'}`}
            style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', height: '30px', padding: '0 0.75rem' }}
            onClick={() => { setView('settings'); navigate('/'); }}
          >
            <Settings size={13} /> Settings
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
                {view === 'cio' && (
                  <div className="dashboard-container">
                    <PersonalCIO apiBase={API_BASE} onShowToast={(msg, isErr) => showToast(msg, isErr || false)} />
                  </div>
                )}
                {view === 'learning' && (
                  <div className="dashboard-container">
                    <AILearning apiBase={API_BASE} onShowToast={(msg, isErr) => showToast(msg, isErr || false)} />
                  </div>
                )}
                {view === 'macro' && (
                  <div className="dashboard-container">
                    <MarketIntelligence apiBase={API_BASE} onShowToast={(msg, isErr) => showToast(msg, isErr || false)} />
                  </div>
                )}

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
                    apiBase={API_BASE}
                  />
                )}

                {view === 'watchlist' && (
                  <div className="dashboard-container">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                      <h2 className="section-title" style={{ margin: 0 }}><Bookmark size={18} /> Watchlist Rankings & Relative Strength</h2>
                      {loadingWatchlist && <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Ranking assets...</span>}
                    </div>
                    <div className="card-panel">
                      {watchlist.length > 0 ? (
                        <div className="table-container">
                          <table className="premium-table">
                            <thead>
                              <tr>
                                <th>Ticker</th>
                                <th>Price</th>
                                <th>Tech Score</th>
                                <th>News Score</th>
                                <th>Regime Score</th>
                                <th>Risk Score</th>
                                <th>Momentum</th>
                                <th>Rel Strength</th>
                                <th>Overall AI Score</th>
                                <th>Sentiment</th>
                              </tr>
                            </thead>
                            <tbody>
                              {watchlistRankings.map((item: any) => {
                                const isChangeBearish = item.change < 0;
                                return (
                                  <tr key={item.ticker} onClick={() => openStock(item.ticker)}>
                                    <td className="table-ticker">
                                      {item.ticker}
                                      <span style={{ display: 'block', fontSize: '0.62rem', fontWeight: 'normal', color: 'var(--text-secondary)' }}>
                                        {item.company_name}
                                      </span>
                                    </td>
                                    <td className="table-price">
                                      ₹{item.price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                                      <span className={isChangeBearish ? 'text-bearish' : 'text-bullish'} style={{ display: 'block', fontSize: '0.65rem', fontWeight: 600 }}>
                                        {item.change >= 0 ? '+' : ''}{item.change.toFixed(2)}%
                                      </span>
                                    </td>
                                    <td>{item.technical_score}/100</td>
                                    <td>{item.news_score}/100</td>
                                    <td>{item.market_regime_score}/100</td>
                                    <td>{item.risk_score}/100</td>
                                    <td>{item.momentum} (RSI)</td>
                                    <td className={item.relative_strength >= 0 ? 'text-bullish' : 'text-bearish'} style={{ fontWeight: 600 }}>
                                      {item.relative_strength >= 0 ? '+' : ''}{item.relative_strength.toFixed(2)}%
                                    </td>
                                    <td className="table-score" style={{ fontSize: '0.9rem', fontWeight: 800 }}>{item.overall_ai_score}/100</td>
                                    <td>
                                      <span className={`badge ${item.news_sentiment === 'Bullish' ? 'badge-success' : item.news_sentiment === 'Bearish' ? 'badge-danger' : 'badge-warning'}`}>
                                        {item.news_sentiment.toUpperCase()}
                                      </span>
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
                  <div className="dashboard-container" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                    <PortfolioIntelligence portfolio={portfolio} activeStocks={activeStocks} apiBase={API_BASE} />
                  </div>
                )}
                {view === 'strategy_lab' && (
                  <div className="dashboard-container">
                    <StrategyLab activeStocks={activeStocks} apiBase={API_BASE} />
                  </div>
                )}
                {view === 'paper_trading' && (
                  <div className="dashboard-container">
                    <PaperTradingDashboard apiBase={API_BASE} onShowToast={(msg, isErr) => showToast(msg, isErr || false)} />
                  </div>
                )}
                {view === 'monitor' && (
                  <div className="dashboard-container">
                    <LiveTradingMonitor apiBase={API_BASE} onShowToast={(msg, isErr) => showToast(msg, isErr || false)} />
                  </div>
                )}
                {view === 'manager' && (
                  <div className="dashboard-container">
                    <PortfolioManager apiBase={API_BASE} onShowToast={(msg, isErr) => showToast(msg, isErr || false)} />
                  </div>
                )}
                {view === 'opportunity' && (
                  <div className="dashboard-container">
                    <OpportunityCenter apiBase={API_BASE} onShowToast={(msg, isErr) => showToast(msg, isErr || false)} />
                  </div>
                )}
                {view === 'live' && (
                  <div className="dashboard-container">
                    <LiveExecution apiBase={API_BASE} onShowToast={(msg, isErr) => showToast(msg, isErr || false)} />
                  </div>
                )}
                {view === 'health' && (
                  <div className="dashboard-container">
                    <ProductionHealth apiBase={API_BASE} onShowToast={(msg, isErr) => showToast(msg, isErr || false)} />
                  </div>
                )}
                {view === 'settings' && (
                  <div className="dashboard-container">
                    <UserSettings apiBase={API_BASE} onShowToast={(msg, isErr) => showToast(msg, isErr || false)} />
                  </div>
                )}
                {view === 'research' && (
                  <div className="dashboard-container">
                    <ResearchEngine activeStocks={activeStocks} apiBase={API_BASE} />
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
          className={`bottom-nav-item ${view === 'cio' ? 'active' : ''}`}
          onClick={() => { setView('cio'); navigate('/'); }}
        >
          <Award size={20} />
          <span>CIO</span>
        </button>
        <button 
          className={`bottom-nav-item ${view === 'learning' ? 'active' : ''}`}
          onClick={() => { setView('learning'); navigate('/'); }}
        >
          <Brain size={20} />
          <span>Learning</span>
        </button>
        <button 
          className={`bottom-nav-item ${view === 'macro' ? 'active' : ''}`}
          onClick={() => { setView('macro'); navigate('/'); }}
        >
          <Globe size={20} />
          <span>Macro</span>
        </button>
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
        <button 
          className={`bottom-nav-item ${view === 'strategy_lab' ? 'active' : ''}`}
          onClick={() => { setView('strategy_lab'); navigate('/'); }}
        >
          <Activity size={20} />
          <span>Lab</span>
        </button>
        <button 
          className={`bottom-nav-item ${view === 'paper_trading' ? 'active' : ''}`}
          onClick={() => { setView('paper_trading'); navigate('/'); }}
        >
          <Play size={20} />
          <span>Paper</span>
        </button>
        <button 
          className={`bottom-nav-item ${view === 'monitor' ? 'active' : ''}`}
          onClick={() => { setView('monitor'); navigate('/'); }}
        >
          <Cpu size={20} />
          <span>Monitor</span>
        </button>
        <button 
          className={`bottom-nav-item ${view === 'manager' ? 'active' : ''}`}
          onClick={() => { setView('manager'); navigate('/'); }}
        >
          <PieChart size={20} />
          <span>Manager</span>
        </button>
        <button 
          className={`bottom-nav-item ${view === 'opportunity' ? 'active' : ''}`}
          onClick={() => { setView('opportunity'); navigate('/'); }}
        >
          <Layers size={20} />
          <span>Opportunity</span>
        </button>
        <button 
          className={`bottom-nav-item ${view === 'live' ? 'active' : ''}`}
          onClick={() => { setView('live'); navigate('/'); }}
        >
          <Shield size={20} />
          <span>Live</span>
        </button>
        <button 
          className={`bottom-nav-item ${view === 'health' ? 'active' : ''}`}
          onClick={() => { setView('health'); navigate('/'); }}
        >
          <Server size={20} />
          <span>Health</span>
        </button>
        <button 
          className={`bottom-nav-item ${view === 'settings' ? 'active' : ''}`}
          onClick={() => { setView('settings'); navigate('/'); }}
        >
          <Settings size={20} />
          <span>Settings</span>
        </button>
      </div>
    </div>
  );
}
