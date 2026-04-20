import { firecrawl } from './firecrawl.js';

export async function discoverSalons(query, limit = 12) {
    const searchResponse = await firecrawl.search(query, { limit });
    const resultsArray = searchResponse.web || [];
    return resultsArray.map(result => result.url);
}
