import { auditSalon } from '../../lib/auditSalon.js';
import { discoverSalons } from '../../lib/discoverSalons.js';
import { NextResponse } from 'next/server';

export async function POST(req) {
  try {
    const { location, state } = await req.json();
    const query = `expensive luxury hair salons in ${location} ${state}`;

    // Step 1: Discover URLs (Limited to 4 for faster live demo performance)
    const discoveredUrls = await discoverSalons(query, 4);

    // Step 2: Parallel Audit
    const auditPromises = discoveredUrls.map(async (url) => {
      const isJunk = ["yelp", "instagram", "facebook", "modernluxury", "timeout", "expertise"].some(j => url.includes(j));
      if (!isJunk) {
        const report = await auditSalon(url);
        // Apply strict MaRe Scale-Up thresholds
        if (report && report.prestige_index >= 70) {
          return report;
        }
      }
      return null;
    });

    const results = await Promise.all(auditPromises);
    const finalLeads = results.filter(lead => lead !== null);

    return NextResponse.json(finalLeads);
  } catch (error) {
    console.error('API Error:', error.message);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}