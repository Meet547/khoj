# Synthetic sample-record portraits

Created with the built-in image-generation tool specifically for the KHOJ agent demo. None depicts a real missing person. No input photograph or face-matching model was used.

Final project assets: `frontend/public/sample-people/adult.png`, `adult.webp`, `child.png`, `child.webp`, `senior.png`, and `senior.webp`. Original images are 1448 × 1086 pixels, each containing a strict 4-column × 3-row grid of twelve portraits (six fictional people in two views). Optimized WebP copies preserve the originals. `frontend/src/features/search/AgentSearch.tsx` displays cells in SVG viewports; images are not individually edited.

## Final prompt set

The same prompt below was issued three times with these age lists: adult = **24, 38, and 48**; child = **8, 10, and 12**; senior = **64, 69, and 75**.

Use case: photorealistic-natural. Asset type: fictional sample-record portrait contact sheet for a missing-person website frontend DEMO, no real person. Create a LANDSCAPE 4-column by 3-row strict uniform grid of twelve individual realistic studio identification-style head-and-shoulders photos of SIX distinct fictional Indian people, ages [AGE LIST]. Each row contains ONE male person twice (column 1 front-facing, column 2 three-quarter view), and ONE female person twice (column 3 front-facing, column 4 three-quarter view). Row 1 people age [FIRST AGE], row 2 middle listed age, row 3 oldest listed age. Keep each person's facial identity and clothing consistent across their two photos, with clearly distinct identities between rows and sexes. Natural Indian skin tones, black or grey hair appropriate to age. Row 1 wears a plain medium-blue shirt or blue top; row 2 wears a light-blue shirt or top; row 3 wears a cream or white shirt or top. Modest everyday clothing, neutral calm expressions. All twelve photos have the SAME warm light-grey seamless backdrop and identical framing from chest up, generous margin above hair. Every cell exactly one-quarter of image width and one-third height, hard rectangular crop, no spacing, no borders. Photographic realism, natural even lighting. No text, names, labels, numbers, watermarks, documents, signage, police symbols, posters, injuries, distress, or dramatic setting. These are synthetic sample portraits, not real people and not actual missing-person records.

Original PNG exports are retained locally. The published frontend uses optimized WebP/AVIF runtime assets; generated originals are excluded from Git.
