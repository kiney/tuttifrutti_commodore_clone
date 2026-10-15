# Project instructions

## Product language

- All player-facing text in the game and its website must be in English, regardless of the language used in chat.
- This includes menus, controls, instructions, mission descriptions, overlays, high scores, status messages, accessibility labels, fallback text, and page metadata.
- Do not switch the product language to German when the user chats in German.
- Conversation and repository documentation may remain in the user's preferred language unless requested otherwise.

## Implementation

- Keep the browser game fully client-side and deployable to static web hosting.
- Avoid external runtime dependencies, remote assets, and CDNs.
- When changing the shipped website, regenerate the upload archive with `python3 tools/package_web.py`.

## Communication preferences

For longer responses, always start with an "Executive Summary". It should state the important conclusions, decisions, recommendations, and tradeoffs so that reading only that section is sufficient to understand the main outcome. Do not add an Executive Summary for short or trivial responses.
