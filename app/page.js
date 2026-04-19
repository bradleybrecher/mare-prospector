"use client";
import { useState } from "react";

const US_STATES = [
  "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado", "Connecticut", 
  "Delaware", "Florida", "Georgia", "Hawaii", "Idaho", "Illinois", "Indiana", "Iowa", 
  "Kansas", "Kentucky", "Louisiana", "Maine", "Maryland", "Massachusetts", "Michigan", 
  "Minnesota", "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada", "New Hampshire", 
  "New Jersey", "New Mexico", "New York", "North Carolina", "North Dakota", "Ohio", 
  "Oklahoma", "Oregon", "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota", 
  "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington", "West Virginia", 
  "Wisconsin", "Wyoming"
];

// Mock Intelligence Data
const DETECTED_SPAS = [
  { name: "Aethel Wellness Lab", tech: "Hyperbaric / DNA-Tailored", status: "Market Leader" },
  { name: "Neon Soma Center", tech: "Robotic Massage / Red Light", status: "Emerging" },
  { name: "The Drift Bathhouse", tech: "Communal Bio-Thermal", status: "Established" }
];

export default function Page() {
  const [isDeploying, setIsDeploying] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [formData, setFormData] = useState({ location: "", state: "" });

  const handleDeploy = () => {
    if (!formData.location || !formData.state) {
      alert("Initialization failed: Provide geographic focus data.");
      return;
    }
    
    setIsDeploying(true);
    setShowResults(false);
    
    // Simulated Processing Time for "Radar Sweep"
    setTimeout(() => {
      setIsDeploying(false);
      setShowResults(true);
    }, 3500);
  };

  return (
    <div className="container">
      <header>
        <h1>MaRe Command Center</h1>
        <p className="subtitle">Strategic Growth Catalyst | Pulse Miami</p>
      </header>

      {!showResults ? (
        <div className="input-group">
          <div className="field">
            <label htmlFor="location">Geographic Focus</label>
            <input 
              type="text" 
              id="location"
              placeholder="City, County, or Zip Code" 
              disabled={isDeploying}
              value={formData.location}
              onChange={(e) => setFormData({ ...formData, location: e.target.value })}
            />
          </div>

          <div className="field">
            <label htmlFor="state">State / Region</label>
            <select 
              id="state"
              className="state-dropdown" 
              defaultValue="" 
              disabled={isDeploying}
              onChange={(e) => setFormData({ ...formData, state: e.target.value })}
            >
              <option value="" disabled>Select State</option>
              {US_STATES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <button 
            className={`deploy-btn ${isDeploying ? 'loading' : ''}`} 
            onClick={handleDeploy}
            disabled={isDeploying}
          >
            {isDeploying ? "Scanning Market..." : "Deploy Radar"}
          </button>

          {isDeploying && (
            <div className="status-console">
              <div className="scanner-line"></div>
              <p className="pulse-text">UPLINK ESTABLISHED...</p>
              <p className="pulse-text" style={{ animationDelay: '0.5s' }}>
                SCRAPING PROXIMITY DATA FOR {formData.location.toUpperCase()}...
              </p>
              <p className="pulse-text" style={{ animationDelay: '1.2s' }}>
                IDENTIFYING SECTOR DISRUPTORS...
              </p>
            </div>
          )}
        </div>
      ) : (
        <div className="results-area">
          <div className="result-header">
            <h3>RADAR RESULTS: {formData.location.toUpperCase()}, {formData.state.toUpperCase()}</h3>
            <span className="status-tag">Live Feed</span>
          </div>
          
          <div className="stats-grid">
            <div className="stat-card">
              <label>Growth Potential</label>
              <div className="value">88%</div>
              <div className="mini-bar">
                <div className="fill" style={{ width: '88%' }}></div>
              </div>
            </div>
            <div className="stat-card">
              <label>Market Saturation</label>
              <div className="value">Low</div>
              <div className="mini-bar">
                <div className="fill" style={{ width: '22%', background: '#22c55e' }}></div>
              </div>
            </div>
          </div>

          {/* New: Detected Spas Section */}
          <section className="data-section">
            <h4>Detected Establishments</h4>
            <div className="spa-list">
              {DETECTED_SPAS.map((spa, i) => (
                <div key={i} className="spa-card">
                  <div className="spa-info">
                    <strong>{spa.name}</strong>
                    <span>{spa.tech}</span>
                  </div>
                  <span className="spa-status">{spa.status}</span>
                </div>
              ))}
            </div>
          </section>

          {/* New: Strategic Next Steps Section */}
          <section className="data-section">
            <h4>Strategic Roadmap</h4>
            <ul className="steps-list">
              <li>
                <strong>01 Site Scoring</strong>
                Conduct a 10-year yield analysis on parcel accessibility within {formData.location}.
              </li>
              <li>
                <strong>02 Tech Integration</strong>
                Scope "Aescape" robotic systems to offset {formData.state}'s rising labor costs.
              </li>
              <li>
                <strong>03 Zoning Audit</strong>
                Validate {formData.state} Class-B commercial zoning for longevity-focused clinical use.
              </li>
            </ul>
          </section>

          <button className="reset-btn" onClick={() => setShowResults(false)}>
            Initialize New Scan
          </button>
        </div>
      )}
    </div>
  );
}