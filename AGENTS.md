# Project instructions

## Artifact language

- All project artifacts must be in English, regardless of the language used in chat. This includes the game, website, README, other documentation, pseudocode, source comments, explanatory identifiers, analysis reports, tool output, and generated files.
- This includes menus, controls, instructions, mission descriptions, overlays, high scores, status messages, accessibility labels, fallback text, and page metadata.
- Do not switch the product language to German when the user chats in German.
- Keep artifact filenames and references in English as well. Update generators so regenerated artifacts remain in English.
- Preserve original binary/reference data byte-for-byte; translate the explanatory material around it.
- Conversation may remain in the user's preferred language. German chat does not authorize German artifacts.

## Implementation

- Keep the browser game fully client-side and deployable to static web hosting.
- Avoid external runtime dependencies, remote assets, and CDNs.
- When changing the shipped website, regenerate the upload archive with `python3 tools/package_web.py`.

## Communication preferences

For longer responses, always start with an "Executive Summary". It should state the important conclusions, decisions, recommendations, and tradeoffs so that reading only that section is sufficient to understand the main outcome. Do not add an Executive Summary for short or trivial responses.
