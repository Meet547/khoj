# KHOJ Indian human character artwork

Created with the built-in image-generation tool for this revision. No reference-brand animal artwork is rendered by the current landing page.

Assets:

- `public/characters/indian-crowd.png` — original 1536 × 1024 crowd artwork.
- `public/characters/indian-crowd.webp` — optimized browser asset.
- `public/characters/indian-people-sheet.png` — original transparent 1536 × 1024 six-illustration sheet.
- `public/characters/indian-people-sheet.webp` — optimized browser asset, preserving alpha.

The sheet is displayed using six SVG viewports in `src/components/illustrations/HumanArt.tsx`. Its cells contain a woman with a magnifier, a man writing, a grandmother waving, a woman at a laptop, a family, and a volunteer with a clipboard. Characters are decorative illustrations, not record photos.

## Final generation prompts

### Crowd

Use case: illustration-story. Asset type: seamless illustrated crowd background for KHOJ, an Indian missing-person support website. Create an original dense edge-to-edge crowd of friendly diverse INDIAN HUMAN CARTOON CHARACTERS, hand-inked clean black outlines, cream/off-white fills, bold black hair and occasional black clothing. Exactly human people, NO animals, no mascots. Portraits from shoulders up overlap densely in staggered rows like a delightful editorial doodle wall. Include young adults, parents, elderly women and men, contemporary shirts and spectacles alongside saris, salwar kameez, kurtas, a Sikh turban, a woman with a small bindi, different hairstyles and beards; variety across India, respectful and natural, not caricatures of ethnicity. Rounded charming expressive faces, simple eyes and smiles, adult proportions cartooned with large heads. Warm community atmosphere. Uniform line weight, black and cream ONLY. No words, no logos, no colored backgrounds, no gradient, no shadows, no frames. At least 40 distinct people across 7 densely packed rows. Portraits extend beyond all four edges to make a repeatable pattern. Landscape composition.

### Supporting character sheet

Use case: illustration-story. Asset type: original six-illustration sprite sheet for an Indian community support website, black and cream line cartoon style. Transparent background. Arrange EXACTLY six separate illustrations on a strict 3 column by 2 row uniform grid, each illustration fully contained centered in its own equal cell, wide transparent margins around each figure. Cell top left: young Indian woman in salwar kameez holding a large magnifying glass, standing. Top center: Indian man in kurta and trousers writing on a notebook. Top right: Indian grandmother in a sari and glasses waving kindly. Bottom left: Indian woman with a braid sitting at a laptop. Bottom center: friendly Indian family of three standing together, mother in sari, father in shirt, child between them. Bottom right: Indian male community volunteer with beard, glasses, casual shirt holding a clipboard. Simple playful rounded HUMAN cartoon characters, black confident outlines, cream-white body fills, flat black hair and occasional clothes, very limited soft warm beige on skin, minimal hand drawn editorial illustration. Human faces, South Asian hairstyles, natural respectful diversity, charming small facial expressions, no animals. No words, no letters, no labels, no icons outside figures, no background scenes. Consistent drawing style and scale across all six cells. Landscape canvas.

Original PNG exports are retained locally. The published frontend uses optimized WebP/AVIF runtime assets; generated originals are excluded from Git.
