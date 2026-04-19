"use client";
import { useState } from 'react';

export default function MaReAdmin() {
  const [form, setForm] = useState({ city: '', state: '' });
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(false);

  const startScan = async () => {
    setLoading(true);
    const res = await fetch('/api/prospect', {
      method: 'POST',
      body: JSON.stringify(form),
    });
    const data = await res.json();
    setLeads(data);
    setLoading(false);
  };

  return (
    <div className="p-12 bg-[#E2E2DE] min-h-screen text-[#2A2420] font-sans">
      <header className="mb-12">
        <h1 className="text-5xl font-serif italic mb-2">MaRe Command Center</h1>
        <p className="tracking-widest text-[#653D24] uppercase text-xs font-bold">Strategic Growth Catalyst</p>
      </header>

      <div className="flex gap-4 mb-16 max-w-2xl">
        <input 
          className="bg-white p-4 border-b border-[#296167] flex-grow outline-none" 
          placeholder="City (e.g., Miami)" 
          onChange={e => setForm({...form, city: e.target.value})} 
        />
        <input 
          className="bg-white p-4 border-b border-[#296167] flex-grow outline-none" 
          placeholder="State (e.g., Florida)" 
          onChange={e => setForm({...form, state: e.target.value})} 
        />
        <button 
          onClick={startScan} 
          className="bg-[#296167] text-white px-10 py-4 uppercase text-xs tracking-widest hover:bg-[#214E52] transition"
        >
          {loading ? "📡 Scanning..." : "Deploy Radar"}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {leads.map((l, i) => (
          <div key={i} className="bg-white p-8 border-l-4 border-[#653D24] shadow-sm">
            <h2 className="text-2xl font-serif italic mb-4">{l.salon_name} — Score: {l.prestige_index}</h2>
            <div className="text-sm space-y-2 mb-6">
              <p><strong>Revenue Verification:</strong> {l.revenue_reasoning}</p>
              <p><strong>Infrastructure Match:</strong> {l.infrastructure_viability}</p>
            </div>
            <div className="pt-4 border-t border-[#E2E2DE]">
              <p className="text-[10px] uppercase tracking-widest text-[#653D24] font-bold mb-2 font-sans">Creative Director Pitch</p>
              <p className="italic text-gray-500 mb-6 font-sans">"{l.creative_director_asset}"</p>
              <div className="bg-[#F6F6F4] p-4 text-xs leading-relaxed font-sans">{l.bespoke_outreach_script}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}