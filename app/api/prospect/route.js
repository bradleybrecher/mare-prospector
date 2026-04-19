import { auditSalon } from '../../lib/auditSalon.js';
import { discoverSalons } from '../../lib/discoverSalons.js';
import { NextResponse } from 'next/server';

export async function POST(req) {
  try {
    const { city, state } = await req.json();
    const query = `expensive luxury hair salons in ${city} ${state}`;

    // Step 1: Discover URLs
    const discoveredUrls = await discoverSalons(query, 7);

    const finalLeads = [];
    // Step 2: Sequential Audit
    for (const url of discoveredUrls) {
      const isJunk = ["yelp", "instagram", "facebook", "modernluxury", "timeout", "expertise"].some(j => url.includes(j));
      
      if (!isJunk) {
        const report = await auditSalon(url);
        // Apply strict MaRe Scale-Up thresholds
        if (report && report.prestige_index >= 70 && report.revenue_verified_1M) {
          finalLeads.push(report);
        }
      }
    }

    return NextResponse.json(finalLeads);
  } catch (error) {
    console.error('API Error:', error.message);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}