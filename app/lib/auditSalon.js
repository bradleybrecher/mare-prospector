import { ai } from './genai.js';
import { firecrawl } from './firecrawl.js';
import { auditPrompt } from './auditPrompt.js';

export async function auditSalon(url) {
    try {
        const scrapeResult = await firecrawl.scrape(url, {
            formats: ['markdown'],
            onlyMainContent: true
        });
        if (!scrapeResult || scrapeResult.success === false) {
            throw new Error("Firecrawl returned empty data. The site might be blocking scrapers.");
        }
        const prompt = auditPrompt.replace('{{DATA}}', scrapeResult.markdown.substring(0, 15000));
        const response = await ai.models.generateContent({
            model: 'gemini-2.5-flash',
            contents: prompt,
            config: { responseMimeType: 'application/json' }
        });
        const analysis = JSON.parse(response.text);
        return { url, ...analysis };
    } catch (error) {
        console.error(`❌ Error at ${url}:`, error.message);
        return null;
    }
}
