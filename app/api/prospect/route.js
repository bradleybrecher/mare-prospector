import { auditSalon } from '../../lib/auditSalon.js';
import { discoverSalons } from '../../lib/discoverSalons.js';
import { NextResponse } from 'next/server';

export async function POST(req) {
  try {
    console.log('--- API: Prospect POST called ---');
    const { city, state } = await req.json();
    console.log('Received city:', city, 'state:', state);
    const query = `expensive luxury hair salons in ${city} ${state}`;

    // Step 1: Discover URLs
    console.log('Starting Firecrawl search with query:', query);
    const discoveredUrls = await discoverSalons(query, 7);
    console.log('Discovered URLs:', discoveredUrls);

    const finalLeads = [];
    let timedOut = false;
    const timeoutPromise = new Promise(resolve => {
      setTimeout(() => {
        timedOut = true;
        console.log('⏰ Timeout reached, returning partial results:', finalLeads);
        resolve(finalLeads);
      }, 10000); // 10 seconds
    });

    const auditPromise = (async () => {
      for (const url of discoveredUrls) {
        if (timedOut) break;
        const isJunk = ["yelp", "instagram", "facebook", "modernluxury", "timeout", "expertise"].some(j => url.includes(j));
        console.log('Auditing URL:', url, 'isJunk:', isJunk);
        if (!isJunk) {
          console.log('Calling auditSalon for:', url);
          const report = await auditSalon(url);
          console.log('auditSalon result:', report);
          if (report && report.prestige_index >= 70 && report.revenue_verified_1M) {
            finalLeads.push(report);
            console.log('Added to finalLeads:', url);
          } else {
            console.log('Skipped (did not meet criteria):', url);
          }
        } else {
          console.log('Skipped junk URL:', url);
        }
      }
      return finalLeads;
    })();

    // Whichever finishes first: audits or timeout
    let result = await Promise.race([auditPromise, timeoutPromise]);
    // Wait for both to finish to ensure we always return the most complete results
    await Promise.allSettled([auditPromise, timeoutPromise]);
    // result may be partial if timeout fired first, but finalLeads will always have the most complete set
    console.log('Returning (possibly partial) finalLeads:', finalLeads);
    return NextResponse.json(finalLeads);
  } catch (error) {
    console.error('API Error:', error.message, error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}