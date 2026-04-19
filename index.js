import fs from 'fs';
import 'dotenv/config';
import { auditSalon } from './src/auditSalon.js';
import { discoverSalons } from './src/discoverSalons.js';

// 1. The Autonomous Execution Loop
(async () => {
    // Prompt user for city and state
    const readline = await import('readline');
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout
    });

    function ask(question) {
        return new Promise(resolve => rl.question(question, resolve));
    }

    const city = await ask('Enter the city: ');
    const state = await ask('Enter the state: ');
    rl.close();

    console.log(`\n🌍 PHASE 1: Deploying 'MaRe Radar' to find targets in ${city}, ${state}...`);
    const finalLeads = [];

    try {
        // Search for salons
        const query = `expensive luxury hair salons in ${city} ${state}`;
        const discoveredUrls = await discoverSalons(query, 7);
        
        console.log(`🎯 Radar found ${discoveredUrls.length} total links. Filtering for actual salon websites...`);

        // PHASE 2: Filter & Audit
        for (const url of discoveredUrls) {
            // Block Yelp, Instagram, Facebook, and Magazine articles
            const isJunk = ["yelp", "instagram", "facebook", "modernluxury", "timeout", "expertise"].some(junk => url.includes(junk));
            
            if (!isJunk) {
                const report = await auditSalon(url);
                // Only keep actual luxury matches!
                if (report && report.prestige_index >= 70) {
                    finalLeads.push(report);
                } else if (report) {
                    console.log(`⚠️ Skipped ${url}: Prestige Index too low (${report.prestige_index})`);
                }
            } else {
                console.log(`⏭️ Skipped Directory/Article: ${url}`);
            }
        }

        console.log("\n💎 MARE GROWTH ENGINE: AUDIT COMPLETE");
        if (finalLeads.length > 0) {
            console.table(finalLeads);
            
            // Generate the JSON file for your UI Partner
            const jsonOutput = JSON.stringify(finalLeads, null, 2);
            fs.writeFileSync('output/leads.json', jsonOutput);
            console.log("💾 SUCCESS: Saved highly qualified leads to 'output/leads.json'");
            
        } else {
            console.log("No leads passed the strict MaRe Luxury criteria this round.");
        }

    } catch (error) {
        console.error("❌ Discovery Phase Failed:", error.message);
    }
})();