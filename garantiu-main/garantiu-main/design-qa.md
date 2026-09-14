# Design QA — Garantiu Risk Map

## Comparison target

- Source visual truth: `C:\Users\muril\.codex\generated_images\01a088a8-2c0c-7050-a501-b53569ded2e3\exec-d584037d-58f5-418c-b3d6-e844e2f6c644.png`
- Source pixels: `1487 × 1058`.
- Intended CSS viewport: `1440 × 1024`, desktop, device scale factor 1.
- Implementation: Streamlit app at `http://127.0.0.1:8501`.
- Implementation screenshot: unavailable because this Codex session exposes no in-app, Chrome, or Edge browser surface.
- State intended for comparison: analyzed release, “Visão Geral do Risco”, dark theme.

## Findings

- [P1] Browser-rendered comparison is unavailable.
  - Location: full application viewport.
  - Evidence: the selected source image was opened at original resolution, the Streamlit health endpoint returned HTTP 200, and the complete AppTest suite exercised the application; however, no browser surface is connected to capture the rendered implementation.
  - Impact: typography, exact spacing, CSS selector compatibility, overflow, responsive behavior, focus appearance, and visual fidelity cannot be approved from code or AppTest output.
  - Fix: open the running application in an available browser at a `1440 × 1024` viewport, analyze a release, capture “Visão Geral do Risco”, and compare that capture with the selected source in one visual input.

## Required fidelity surfaces

- Fonts and typography: implemented with system sans and Cascadia/Consolas mono fallbacks; browser fidelity not visually verified.
- Spacing and layout rhythm: implemented with a 1240 px content container, persistent 270 px sidebar, 12 px radii, responsive breakpoints at 900 px and 560 px; browser fidelity not visually verified.
- Colors and visual tokens: implemented with ink/navy surfaces, cobalt action blue, coral/amber/green risk semantics, and slate borders; rendered contrast and target matching not visually verified.
- Image quality and asset fidelity: the selected screen contains no photography or illustration. The wordmark remains live text and UI controls remain framework-native; browser rendering not visually verified.
- Copy and content: Brazilian Portuguese product copy reflects actual implemented capabilities. No deploy, authentication, confidence percentage, coverage percentage, or analysis timestamp was invented.

## Full-view comparison evidence

Blocked. The source visual was opened and inspected, but the implementation could not be captured in a browser. HTTP health and automated tests are not substitutes for visual evidence.

## Focused region comparison evidence

Blocked for the same reason. The priority regions for a later pass are the sidebar/navigation, risk hero, factor bars, module table, focus panel, and responsive collapse.

## Interaction and runtime evidence

- Streamlit health endpoint: HTTP 200 (`ok`).
- Automated application suite: all seven screens, real analysis pipeline, empty/error states, persistent decisions/outcomes, GitHub source flow, and the risk-overview CTA are exercised with Streamlit AppTest.
- Primary CTA: “Preparar teste manual” transitions from risk overview to the manual test guide in AppTest.
- Browser console: not checked because no browser surface is available.

## Comparison history

- Initial pass: blocked before visual comparison; no implementation screenshot was available.
- P0/P1/P2 fixes from visual evidence: none can be claimed without a rendered capture.

## Implementation checklist

1. Capture the analyzed risk overview at 1440 × 1024 in a connected browser.
2. Compare source and implementation together, including focused crops for navigation, score/factors, and table/focus panel.
3. Correct every observed P0/P1/P2 mismatch.
4. Repeat capture and comparison until the report can truthfully say `passed`.

## Follow-up polish

No P3 polish is classified until the blocking visual comparison is complete.

final result: blocked
