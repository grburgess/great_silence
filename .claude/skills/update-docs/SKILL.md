---
name: update-docs
description: Regenerate and rebuild the Astro Starlight documentation in docs/ after code changes (new features, API changes, new modules). Use when documentation needs updating to reflect code behavior.
---

# Update Docs

Regenerate the API documentation and rebuild the Astro Starlight site in `docs/`.

## Steps

1. Regenerate API docs from source docstrings:
   ```bash
   micromamba run -n galaticbot python docs/scripts/generate-api-docs.py
   ```

2. Update relevant guide/tutorial MDX pages in `docs/src/content/docs/` if behavior changed.

3. Build to verify (run from the `docs/` directory):
   ```bash
   cd docs && npm run build
   ```

## Gotchas

- Links in MDX files must **NOT** include the `/great_silence/` base path prefix — Astro
  adds it automatically. Writing the prefix produces broken links.
- For major documentation rewrites, prefer the `code-documentor` agent.
- The generator reads docstrings from `great_silence/` — keep physical units documented in
  docstrings so they surface in the generated API pages.
