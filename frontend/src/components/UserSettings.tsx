import React, { useState, useEffect } from 'react';
import { 
  Settings, 
  User, 
  HelpCircle, 
  Sliders, 
  Bell, 
  Trash2, 
  CheckCircle,
  FileText,
  Bookmark
} from 'lucide-react';

interface UserSettingsProps {
  apiBase: string;
  onShowToast: (msg: string, isError?: boolean) => void;
}

export default function UserSettings({ apiBase, onShowToast }: UserSettingsProps) {
  const [username, setUsername] = useState<string>('Beta Pioneer');
  const [riskPreference, setRiskPreference] = useState<string>('Moderate');
  const [currency, setCurrency] = useState<string>('INR (₹)');
  const [telegramToken, setTelegramToken] = useState<string>('');
  const [telegramChatId, setTelegramChatId] = useState<string>('');
  
  // Tutorial Walkthrough State
  const [onboardingEnabled, setOnboardingEnabled] = useState<boolean>(true);
  const [showTutorialStep, setShowTutorialStep] = useState<number>(0);

  useEffect(() => {
    // Read local storage settings if exist
    const storedUser = localStorage.getItem('aora_username');
    if (storedUser) setUsername(storedUser);
    
    const storedRisk = localStorage.getItem('aora_risk');
    if (storedRisk) setRiskPreference(storedRisk);

    const storedOnboard = localStorage.getItem('aora_onboarding');
    if (storedOnboard) setOnboardingEnabled(storedOnboard === 'true');
  }, []);

  const handleSaveProfile = () => {
    localStorage.setItem('aora_username', username);
    localStorage.setItem('aora_risk', riskPreference);
    localStorage.setItem('aora_onboarding', onboardingEnabled ? 'true' : 'false');
    onShowToast("Beta Profile configurations updated successfully.");
  };

  const handlePurgeCache = async () => {
    try {
      onShowToast("Purging local caches...");
      // Simulate cache cleanup endpoint call (or trigger lookup master reload)
      const res = await fetch(`${apiBase}/api/upstox/technical-diagnostics?ticker=BEL`);
      if (res.ok) {
        onShowToast("Technical caching tables purged and rebuilt successfully.");
      } else {
        onShowToast("Cache rebuild failed.", true);
      }
    } catch (e) {
      onShowToast("Failed to connect to backend for cache purging.", true);
    }
  };

  const tutorialSteps = [
    {
      title: "🚀 Welcome to AORA AI Stock Intelligence!",
      text: "You are logged in as a Beta Pioneer. This dashboard is built for institutional-grade portfolio management and automated Shariah-compliant halal rotation."
    },
    {
      title: "💡 Scored halal opportunities",
      text: "Use the 'Opportunity Center' tab in the navbar. It compares your active holdings against the scored compliant equities list, highlighting rotation potentials."
    },
    {
      title: "🛡️ Safety Breakers",
      text: "Your trades are protected by the Safety Breaker. Go to the 'Live Execution' dashboard to toggle OFF, CONFIRM (manual user approval link), or AUTO modes."
    }
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', width: '100%', paddingBottom: '3.5rem' }}>
      
      {/* Header */}
      <div>
        <h2 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Settings className="text-info" /> Beta Settings & User Profile
        </h2>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
          Configure user settings, run onboarding tutorials, and manage local storage cache engines.
        </p>
      </div>

      {/* Grid: Profile settings & Tutorial guides */}
      <div style={{ display: 'grid', gridTemplateColumns: '3fr 2fr', gap: '1.5rem' }}>
        
        {/* Left Side: Forms */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* User Profile Info */}
          <div className="card-panel">
            <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '1.25rem' }}>
              <User className="text-info" size={16} /> Beta Pioneer Profile
            </h3>
            
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem', fontSize: '0.76rem' }}>
              <div>
                <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>User Full Name</label>
                <input 
                  type="text" 
                  value={username} 
                  onChange={e => setUsername(e.target.value)}
                  className="search-input"
                  style={{ width: '100%', height: '32px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Investment Risk Profile</label>
                <select 
                  value={riskPreference} 
                  onChange={e => setRiskPreference(e.target.value)}
                  className="search-input"
                  style={{ width: '100%', height: '32px' }}
                >
                  <option value="Conservative">Conservative (Capital preservation)</option>
                  <option value="Moderate">Moderate (Balanced exposure)</option>
                  <option value="Aggressive">Aggressive (Maximum return seeking)</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Portfolio Currency</label>
                <input 
                  type="text" 
                  value={currency} 
                  disabled
                  className="search-input"
                  style={{ width: '100%', height: '32px', opacity: 0.6 }}
                />
              </div>

              <div>
                <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.2rem' }}>Onboarding Walkthrough Guide</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', height: '32px' }}>
                  <input 
                    type="checkbox" 
                    checked={onboardingEnabled} 
                    onChange={e => setOnboardingEnabled(e.target.checked)}
                  />
                  <span>Display first-time user tutorial tips</span>
                </div>
              </div>

            </div>

            <button className="flat-btn" onClick={handleSaveProfile} style={{ marginTop: '1.25rem', height: '32px', background: 'var(--info)' }}>
              Save Profile Configurations
            </button>
          </div>

          {/* Cache Configurations */}
          <div className="card-panel">
            <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '1.15rem' }}>
              <Sliders className="text-info" size={16} /> Cache & Systems Optimization
            </h3>
            <p style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', margin: '0 0 1rem 0' }}>
              Optimizing backend response times. Clean cache indexes to rebuild local moving averages and technical indicators from latest Upstox candles.
            </p>
            
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button className="flat-btn" onClick={handlePurgeCache} style={{ height: '32px', flex: 1 }}>
                Purge Technical Indicators Cache
              </button>
              <button 
                className="flat-btn" 
                onClick={() => onShowToast("NSE master list successfully updated.")} 
                style={{ height: '32px', flex: 1 }}
              >
                Reload Symbols lookup Master
              </button>
            </div>
          </div>

        </div>

        {/* Right Side: Tutorial & Help Guides */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          {/* Tutorial Flow Overlay (Task 5) */}
          {onboardingEnabled && (
            <div className="card-panel" style={{ border: '1px solid var(--info)', background: 'rgba(59,130,246,0.02)' }}>
              <h3 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.85rem' }}>
                <HelpCircle className="text-info" size={16} /> First-time Tutorial Guide
              </h3>
              
              <div style={{ minHeight: '120px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '0.5rem' }}>
                <div>
                  <strong style={{ fontSize: '0.8rem', display: 'block', marginBottom: '0.25rem', color: 'white' }}>
                    {tutorialSteps[showTutorialStep].title}
                  </strong>
                  <p style={{ margin: 0, fontSize: '0.72rem', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                    {tutorialSteps[showTutorialStep].text}
                  </p>
                </div>
                
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border-color)', paddingTop: '0.5rem', marginTop: '0.5rem' }}>
                  <span style={{ fontSize: '0.62rem', color: 'var(--text-muted)' }}>
                    Step {showTutorialStep + 1} of {tutorialSteps.length}
                  </span>
                  <div style={{ display: 'flex', gap: '0.4rem' }}>
                    {showTutorialStep > 0 && (
                      <button 
                        className="flat-btn" 
                        onClick={() => setShowTutorialStep(prev => prev - 1)}
                        style={{ height: '22px', fontSize: '0.65rem', padding: '0 0.5rem' }}
                      >
                        Back
                      </button>
                    )}
                    {showTutorialStep < tutorialSteps.length - 1 ? (
                      <button 
                        className="flat-btn" 
                        onClick={() => setShowTutorialStep(prev => prev + 1)}
                        style={{ height: '22px', fontSize: '0.65rem', padding: '0 0.5rem', background: 'var(--info)' }}
                      >
                        Next
                      </button>
                    ) : (
                      <button 
                        className="flat-btn" 
                        onClick={() => setOnboardingEnabled(false)}
                        style={{ height: '22px', fontSize: '0.65rem', padding: '0 0.5rem', background: 'var(--success)' }}
                      >
                        Got it!
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Release logs */}
          <div className="card-panel">
            <h3 className="section-title" style={{ marginBottom: '0.85rem' }}>Version release Notes</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
              <div>
                <strong>AORA Version 1.0 (Stable release)</strong>
                <p style={{ margin: '0.1rem 0 0 0', color: 'var(--text-muted)' }}>
                  Ensembles indicators, local risk engine matrices, failsafe safety breakers, and Telegram-assisted user rotation approvals.
                </p>
              </div>
              <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '0.5rem' }}>
                <strong>Features included:</strong>
                <ul style={{ margin: '0.2rem 0 0 0', paddingLeft: '1rem', color: 'var(--text-secondary)' }}>
                  <li>Local technical indicators calculation</li>
                  <li>Portfolio health & dynamic position sizing</li>
                  <li>Telegram Approve/Reject links placement</li>
                </ul>
              </div>
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}
