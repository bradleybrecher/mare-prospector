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

export default function Page() {
  const [isDeploying, setIsDeploying] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [formData, setFormData] = useState({ location: "", state: "" });
  const [leads, setLeads] = useState([]);
  const [apiError, setApiError] = useState("");

  const handleDeploy = async () => {
    if (!formData.location || !formData.state) {
      alert("Initialization failed: Please provide geographic focus data.");
      return;
    }
    
    setIsDeploying(true);
    setShowResults(false);
    setApiError("");
    
    try {
      const res = await fetch('/api/prospect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      
      const payload = await res.json();

      if (!payload || !Array.isArray(payload.results)) {
        throw new Error(payload?.message || "Unexpected response from prospect API.");
      }
      
      setLeads(payload.results);
      setApiError(payload.error || "");
      setShowResults(true);
    } catch (error) {
      console.error("Failed to fetch leads", error);
      alert(`Radar malfunction: ${error.message}`);
      setLeads([]);
      setApiError(error.message);
    } finally {
      setIsDeploying(false);
    }
  };

  const exportToCSV = () => {
    if (leads.length === 0) return;

    const headers = [
      "Salon Name", "Location", "State", "URL", "Email", "Phone", "Prestige Score", 
      "1M+ Verified", "Infrastructure", "Upsell Potential", 
      "Outreach Script", "Content Hook", "Content Concept"
    ];

    const csvRows = leads.map(lead => {
      return [
        `"${lead.salon_name || ''}"`,
        `"${lead.search_location || formData.location || ''}"`,
        `"${lead.search_state || formData.state || ''}"`,
        `"${lead.url || ''}"`,
        `"${lead.contact_email || ''}"`,
        `"${lead.contact_phone || ''}"`,
        `"${lead.prestige_index || ''}"`,
        `"${lead.revenue_verified_1M ? 'Yes' : 'No'}"`,
        `"${lead.infrastructure_viability || ''}"`,
        `"${lead.incentive_calculator?.upsell_potential || ''}"`,
        `"${lead.bespoke_outreach_script || ''}"`,
        `"${lead.creative_director_assets?.[0]?.hook || ''}"`,
        `"${lead.creative_director_assets?.[0]?.concept || ''}"`
      ].join(',');
    });

    const csvContent = [headers.join(','), ...csvRows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `MaRe_Leads_${formData.location.replace(/\s+/g, '_')}_${formData.state}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="container">
      <header>
        <h1>MaRe Command Center</h1>
        <p className="subtitle">Global Prospector & Content Engine</p>
      </header>

      {!showResults ? (
        <div className="input-group">
          <div className="field">
            <label htmlFor="location">Target Proximity</label>
            <input 
              type="text" 
              id="location"
              placeholder="e.g., Beverly Hills, SoHo, Brickell" 
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
              value={formData.state}
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
            {isDeploying ? "Synthesizing Data..." : "Run Growth Catalyst"}
          </button>

          {isDeploying && (
            <div className="status-console">
              <p className="pulse-text">Initiating MaRe Eye Protocol...</p>
              <p className="pulse-text" style={{ animationDelay: '0.5s' }}>
                Scanning luxury domains in {formData.location}, {formData.state}...
              </p>
              <p className="pulse-text" style={{ animationDelay: '1.2s' }}>
                Auditing facility infrastructure & $1M+ revenue markers...
              </p>
            </div>
          )}
        </div>
      ) : (
        <div className="results-area">
          <div className="result-header">
            <h3>Radar Results: {formData.location}, {formData.state}</h3>
            <span className="status-tag">{leads.length} Target(s) Acquired</span>
          </div>

          <section className="data-section">
            <div className="spa-list">
              {apiError && (
                <p style={{ color: '#9f1239', marginBottom: '16px' }}>
                  {apiError}
                </p>
              )}
              {leads.length === 0 ? (
                <p style={{color: '#71717a'}}>No salons met the strict MaRe luxury criteria in this sector.</p>
              ) : leads.map((lead, i) => (
                <div key={i} className="lead-card">
                  <div className="lead-header">
                    <div className="header-title-group">
                      <h4>{lead.salon_name || "Unverified Luxury Entity"}</h4>
                      <a href={lead.url} target="_blank" rel="noopener noreferrer" className="lead-url">
                        {lead.url}
                      </a>
                    </div>
                    <span className="prestige-score">Score: {lead.prestige_index}/100</span>
                  </div>

                  {(lead.contact_email || lead.contact_phone) && (
                    <div className="lead-contact">
                      {lead.contact_email && <span>📧 {lead.contact_email}</span>}
                      {lead.contact_phone && <span>📞 {lead.contact_phone}</span>}
                    </div>
                  )}
                  
                  <div className="lead-metrics">
                    <span className={lead.revenue_verified_1M ? "metric pass" : "metric"}>
                      {lead.revenue_verified_1M ? "$1M+ Verified" : "Revenue Unverified"}
                    </span>
                    <span className="metric">State: {lead.search_state || formData.state}</span>
                    <span className="metric">Infra: {lead.infrastructure_viability}</span>
                    <span className="metric">AI Reach: {lead.ai_search_dominance}</span>
                  </div>

                  <div className="lead-content">
                    <p><strong>Revenue Logic:</strong> {lead.revenue_reasoning}</p>

                    <div className="incentive-box">
                      <strong>📈 Incentive Calculator</strong>
                      <p><em>Upsell Potential:</em> {lead.incentive_calculator?.upsell_potential}</p>
                      <p><em>Est. ROI Timeline:</em> {lead.incentive_calculator?.roi_timeline}</p>
                    </div>
                    
                    <div className="outreach-box">
                      <div className="outreach-header">
                        <strong>Human-in-the-Loop Outreach Draft</strong>
                        <a 
                          href={`mailto:${lead.contact_email || ''}?subject=${encodeURIComponent("Elevating the Head Spa Experience at " + (lead.salon_name || "Your Salon"))}&body=${encodeURIComponent(lead.bespoke_outreach_script)}`} 
                          className="email-draft-btn"
                        >
                          ✉️ Open in Email
                        </a>
                      </div>
                      <p>"{lead.bespoke_outreach_script}"</p>
                    </div>

                    <div className="content-engine-box">
                      <strong>Content Engine Asset</strong>
                      <p><em>Hook:</em> {lead.creative_director_assets?.[0]?.hook}</p>
                      <p><em>Concept:</em> {lead.creative_director_assets?.[0]?.concept}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <div className="action-buttons">
            <button className="export-btn" onClick={exportToCSV} disabled={leads.length === 0}>
              📥 Export to CSV
            </button>
            <button className="reset-btn" onClick={() => setShowResults(false)}>
              Initialize New Scan
            </button>
          </div>
        </div>
      )}
    </div>
  );
}