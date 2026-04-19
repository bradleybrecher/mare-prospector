"""
Build script for the before/after demo.

Reads _template.html, produces two files:
  - before.html: template with the SCHEMA_INJECTION_POINT marker removed
  - after.html:  template with the marker replaced by schema blocks

The only difference between the two outputs is the structured-data
<script> blocks. Run before each demo to ensure parity.

Usage:
    python build_demo.py
"""

from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "_template.html"
BEFORE = ROOT / "before.html"
AFTER = ROOT / "after.html"

MARKER = "<!-- SCHEMA_INJECTION_POINT -->"

# The schema blocks that go into the "after" version.
# Three linked entities (Organization / LocalBusiness / WebSite) plus an
# embedded FAQPage matching the six visible FAQ items on the page.
SCHEMA = """<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": "https://mareheadspa.com/#organization",
      "name": "MaRe Head Spa System",
      "url": "https://mareheadspa.com",
      "logo": {
        "@type": "ImageObject",
        "url": "https://mareheadspa.com/cdn/shop/files/logo.svg",
        "width": 512,
        "height": 512
      },
      "description": "A luxury head spa system combining AI-powered scalp diagnostics, standardized ritual protocols, and Italian biodynamic formulations from Philip Martin's.",
      "slogan": "Your Head. Your Way. Science Supported.",
      "founder": [
        {"@type": "Person", "name": "Rebecca Fishman", "jobTitle": "Co-Founder"},
        {"@type": "Person", "name": "Marianna Stiglitz", "jobTitle": "Co-Founder"}
      ],
      "sameAs": [
        "https://www.instagram.com/mareheadspa/",
        "https://www.linkedin.com/company/mare-head-spa-system/"
      ],
      "contactPoint": [{
        "@type": "ContactPoint",
        "telephone": "+1-305-915-0530",
        "email": "info@mareheadspa.com",
        "contactType": "customer service",
        "areaServed": "US",
        "availableLanguage": ["English"]
      }],
      "knowsAbout": [
        "head spa", "scalp health", "scalp analysis",
        "AI scalp diagnostics", "luxury hair care",
        "Philip Martin's haircare", "biodynamic hair care",
        "scalp treatment", "head wellness", "cognitive wellness"
      ]
    },
    {
      "@type": ["LocalBusiness", "HairSalon"],
      "@id": "https://mareheadspa.com/#flagship",
      "name": "MaRe Head Spa System \\u2014 Miami Flagship",
      "parentOrganization": {"@id": "https://mareheadspa.com/#organization"},
      "url": "https://mareheadspa.com",
      "telephone": "+1-305-915-0530",
      "email": "info@mareheadspa.com",
      "image": "https://mareheadspa.com/cdn/shop/files/logo.svg",
      "priceRange": "$$$",
      "address": {
        "@type": "PostalAddress",
        "addressLocality": "Miami",
        "addressRegion": "FL",
        "addressCountry": "US"
      },
      "areaServed": {"@type": "City", "name": "Miami"},
      "hasOfferCatalog": {
        "@type": "OfferCatalog",
        "name": "MaRe Head Spa Rituals",
        "itemListElement": [
          {"@type": "Offer", "itemOffered": {"@type": "Service",
            "name": "MaRe Express Ritual",
            "description": "35-minute head spa ritual with MaRe Eye scalp analysis and Philip Martin's biodynamic protocol."}},
          {"@type": "Offer", "itemOffered": {"@type": "Service",
            "name": "MaRe Signature Ritual",
            "description": "60-minute head spa ritual with MaRe Eye scalp analysis and Philip Martin's biodynamic protocol."}},
          {"@type": "Offer", "itemOffered": {"@type": "Service",
            "name": "MaRe Deep Ritual",
            "description": "90-minute head spa ritual with MaRe Eye scalp analysis and Philip Martin's biodynamic protocol."}}
        ]
      }
    },
    {
      "@type": "WebSite",
      "@id": "https://mareheadspa.com/#website",
      "url": "https://mareheadspa.com",
      "name": "MaRe Head Spa System",
      "publisher": {"@id": "https://mareheadspa.com/#organization"},
      "inLanguage": "en-US",
      "potentialAction": {
        "@type": "SearchAction",
        "target": {"@type": "EntryPoint",
                   "urlTemplate": "https://mareheadspa.com/search?q={search_term_string}"},
        "query-input": "required name=search_term_string"
      }
    },
    {
      "@type": "FAQPage",
      "@id": "https://mareheadspa.com/#faq",
      "mainEntity": [
        {
          "@type": "Question",
          "name": "What is a head spa?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "A head spa is a treatment focused on the scalp, hair, and nervous system, performed by a trained technician. Massage, specialized tools, heat, water, aromatics. Sessions run thirty-five to ninety minutes and move through three phases: diagnosis, the work itself, and the ritual that closes it. It is not a salon wash. The intent is different."
          }
        },
        {
          "@type": "Question",
          "name": "How is MaRe different from other head spa experiences?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "MaRe is a system, not a treatment. It pairs AI-powered scalp diagnostics with forty standardized protocols and Italian biodynamic formulations from Philip Martin's. Other head spas rely on the technician's intuition. MaRe relies on what the MaRe Eye sees. A session produces a diagnostic profile, a matched protocol, and a take-home routine drawn from the same data. Clients get the same quality of read at any MaRe location. Rare thing in this category."
          }
        },
        {
          "@type": "Question",
          "name": "What is the MaRe Eye scalp analysis?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "The MaRe Eye is a diagnostic camera with four kinds of light. White light for the surface: sebum, flakes, density. Polarized light for the things under the surface, like vascular activity, redness, and the beginnings of inflammation. UV for microbial presence and residue. A zoom lens for the hair shaft itself. The reading is combined with a questionnaire on medical history, hormones, sleep, and stress. Out of that, a protocol. Out of that, a routine for home."
          }
        },
        {
          "@type": "Question",
          "name": "How much does a MaRe head spa treatment cost?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "MaRe sessions start around $130, depending on ritual length and the partner venue. Most clients leave with a Philip Martin's take-home routine selected from their diagnostic report, priced separately."
          }
        },
        {
          "@type": "Question",
          "name": "What happens during a MaRe head spa session?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "A session starts with the questionnaire and the scan. The MaRe Eye captures the scalp under four lights, and the resulting profile pulls one of forty protocols. The treatment happens in the MaRe Capsule, reclined in a zero-gravity position modeled on NASA's Neutral Body Posture. A certified MaRe Master performs the protocol with Philip Martin's Italian biodynamic formulations, applied in timed steps through the capsule's micro-mist, steam, and massage systems. Clients leave with a Philip Martin's routine drawn from their own scalp data."
          }
        },
        {
          "@type": "Question",
          "name": "Does MaRe help with stress or sleep?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "MaRe is built around the scalp and the nervous system as a connected pair. The zero-gravity position activates the parasympathetic nervous system. The scalp massage and micro-mist reduce the physiological stress response. The ninety-minute Deep Ritual primes the body for sleep. Many clients report better sleep and sharper mental clarity alongside the scalp results. The cognitive dimension is part of the treatment, not a side effect."
          }
        }
      ]
    }
  ]
}
</script>"""


def verify_parity(before_text: str, after_text: str) -> None:
    """Ensure the only diff between before/after is the schema block."""
    b_lines = before_text.splitlines(keepends=True)
    a_lines = after_text.splitlines(keepends=True)
    diff = list(difflib.unified_diff(b_lines, a_lines, lineterm=""))

    # Every diff line should be either metadata ("---", "+++", "@@"),
    # an added line (starts with "+"), or unchanged context (" ").
    # The marker line (SCHEMA_INJECTION_POINT) is expected to be removed
    # — that IS the replacement point. All other removals are failures.
    removed = [
        line for line in diff
        if line.startswith("-")
        and not line.startswith("---")
        and MARKER not in line
    ]
    if removed:
        print("PARITY FAIL: after.html removes content from before.html")
        for line in removed[:10]:
            print(f"  {line.rstrip()}")
        sys.exit(1)

    # Also: every added line should be inside the schema block (heuristic:
    # contains ld+json, or schema.org, or is JSON-ish syntax).
    added = [
        line for line in diff
        if line.startswith("+") and not line.startswith("+++")
    ]
    # We expect ~30-80 added lines (the schema block). Flag extremes.
    if len(added) < 10:
        print(f"PARITY WARN: only {len(added)} added lines; schema may be missing")
    if len(added) > 300:
        print(f"PARITY WARN: {len(added)} added lines; more than expected")


def main() -> int:
    if not TEMPLATE.exists():
        print(f"ERROR: template not found: {TEMPLATE}")
        return 1

    template = TEMPLATE.read_text(encoding="utf-8")
    if MARKER not in template:
        print(f"ERROR: marker not found in template: {MARKER}")
        return 1

    # before.html: leave the marker comment in place. It's already an HTML
    # comment, so it's invisible in the rendered page. The marker doubles
    # as documentation of where schema would go.
    before = template

    # after.html: replace marker with the schema block.
    after = template.replace(
        MARKER,
        SCHEMA,
    )

    BEFORE.write_text(before, encoding="utf-8")
    AFTER.write_text(after, encoding="utf-8")

    # Parity sanity check.
    verify_parity(before, after)

    # Summary
    before_bytes = len(before.encode("utf-8"))
    after_bytes = len(after.encode("utf-8"))
    schema_bytes = after_bytes - before_bytes

    print(f"built: before.html ({before_bytes:,} bytes)")
    print(f"built: after.html  ({after_bytes:,} bytes)")
    print(f"schema payload:    {schema_bytes:,} bytes "
          f"({schema_bytes / after_bytes * 100:.1f}% of after)")
    print()
    print("diff: the only change from before to after is the schema block.")
    print()
    print("validate:")
    print("  before.html -> expected 0 items")
    print("  after.html  -> expected 4 items (Organization, LocalBusiness, WebSite, FAQPage)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
