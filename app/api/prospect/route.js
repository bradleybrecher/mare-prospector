import { auditSalon } from '../../lib/auditSalon.js';
import { discoverSalons } from '../../lib/discoverSalons.js';
import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const CACHE_FILE = path.join(process.cwd(), 'output', 'cache.json');
const MAX_RESULTS = 12;
const CACHE_TTL_MS = 24 * 60 * 60 * 1000;

const createEmptyCache = () => ({
  queries: {},
  audits: {}
});

const isFresh = (timestamp) => {
  if (!timestamp) return false;
  return Date.now() - timestamp < CACHE_TTL_MS;
};

const normalizeCache = (rawCache) => {
  if (!rawCache || typeof rawCache !== 'object' || Array.isArray(rawCache)) {
    return createEmptyCache();
  }

  if (rawCache.queries || rawCache.audits) {
    return {
      queries: rawCache.queries || {},
      audits: rawCache.audits || {}
    };
  }

  // Backward compatibility for the old { cacheKey: [...] } format.
  const migratedQueries = Object.fromEntries(
    Object.entries(rawCache).map(([key, value]) => [key, { timestamp: Date.now(), results: value }])
  );

  return {
    queries: migratedQueries,
    audits: {}
  };
};

const readCache = () => {
  try {
    if (fs.existsSync(CACHE_FILE)) {
      const rawCache = JSON.parse(fs.readFileSync(CACHE_FILE, 'utf8'));
      return normalizeCache(rawCache);
    }
  } catch (e) { console.error('Cache read error:', e); }
  return createEmptyCache();
};

const writeCache = (cacheData) => {
  try {
    const dir = path.dirname(CACHE_FILE);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(CACHE_FILE, JSON.stringify(cacheData, null, 2));
  } catch (e) { console.error('Cache write error:', e); }
};

const buildPayload = (results, error = null, cacheStatus = 'miss', fallback = null) => ({
  results,
  error,
  cacheStatus,
  fallback
});

export async function POST(req) {
  try {
    const { location, state } = await req.json();
    const cacheKey = `${location}_${state}`.toLowerCase().replace(/\s+/g, '_');
    const cache = readCache();
    const cachedQuery = cache.queries[cacheKey];
    const staleResults = cachedQuery?.results?.slice(0, MAX_RESULTS) || [];

    if (cachedQuery && isFresh(cachedQuery.timestamp)) {
      return NextResponse.json(buildPayload(cachedQuery.results.slice(0, MAX_RESULTS), null, 'hit'), {
        headers: { 'x-mare-cache': 'hit' }
      });
    }

    const query = `expensive luxury hair salons in ${location} ${state}`;

    let discoveredUrls = [];

    try {
      // Search up to 12 URLs and dedupe before auditing.
      discoveredUrls = [...new Set(await discoverSalons(query, MAX_RESULTS))].slice(0, MAX_RESULTS);
    } catch (error) {
      console.error('Discover salons error:', error.message);

      if (staleResults.length > 0) {
        return NextResponse.json(buildPayload(
          staleResults,
          `Firecrawl search failed. Showing cached results instead. ${error.message}`,
          'stale',
          'discover-failed'
        ), {
          headers: {
            'x-mare-cache': 'stale',
            'x-mare-fallback': 'discover-failed'
          }
        });
      }

      return NextResponse.json(buildPayload(
        [],
        `Firecrawl search failed and no cached results were available. ${error.message}`,
        'empty',
        'discover-failed'
      ), {
        headers: {
          'x-mare-cache': 'empty',
          'x-mare-fallback': 'discover-failed'
        }
      });
    }

    const results = (await Promise.all(
      discoveredUrls.map(async (url) => {
        const isJunk = ["yelp", "instagram", "facebook", "modernluxury", "timeout"].some(j => url.includes(j));
        if (isJunk) return null;

        const cachedAudit = cache.audits[url];
        if (cachedAudit && isFresh(cachedAudit.timestamp)) {
          return {
            ...cachedAudit.result,
            search_location: location,
            search_state: state
          };
        }

        const report = await auditSalon(url);
        if (!report || report.prestige_index < 60) {
          return null;
        }

        cache.audits[url] = {
          timestamp: Date.now(),
          result: report
        };

        return {
          ...report,
          search_location: location,
          search_state: state
        };
      })
    )).filter(Boolean);

    cache.queries[cacheKey] = {
      timestamp: Date.now(),
      results: results.slice(0, MAX_RESULTS)
    };

    writeCache(cache);

    return NextResponse.json(buildPayload(cache.queries[cacheKey].results, null, 'miss'), {
      headers: { 'x-mare-cache': 'miss' }
    });
  } catch (error) {
    console.error('API Error:', error.message);
    return NextResponse.json(buildPayload(
      [],
      `Prospect scan failed. ${error.message}`,
      'empty',
      'unexpected-error'
    ), {
      headers: {
        'x-mare-cache': 'empty',
        'x-mare-fallback': 'unexpected-error'
      }
    });
  }
}