# Project Roadmap

## Overview

This document outlines the 8-week development roadmap for the **Canvas LMS Quiz Generator** app. It details prioritized features, milestones, and timelines to ensure clear goals and smooth progress.

---

## Timeline & Milestones

| Week | Dates                | Milestone / Goal                                                         |
|-------|----------------------|-------------------------------------------------------------------------|
| 1     | 2025-06-16 to 2025-06-22 | Initial Setup and Canvas Login Integration completed                   |
| 2–3   | 2025-06-23 to 2025-07-06 | MVP: Fetch course content using Canvas API, display UI, parse modules for LLM input |
| 4–5   | 2025-07-07 to 2025-07-20 | LLM setup: Parse generated questions, preview questions, export to Canvas |
| 6     | 2025-07-21 to 2025-07-27 | LLM polish: Edit answers and question text, add extra context for generation, export in JSON format |
| 7–8   | 2025-07-28 to 2025-08-10 | Final polish: Draft saving, multiple LLM models support, more question types, documentation & demo |

---

## Prioritized Feature Breakdown

### Core Functionality (Weeks 1–3)

- Canvas OAuth login and secure authentication  
- Fetch and display courses and module content from Canvas API  
- Parse module content into formats suitable for LLM question generation  

### LLM Integration & Export (Weeks 4–6)

- Integrate LLM to generate multiple-choice questions from parsed content  
- Provide UI to preview and edit generated questions  
- Export generated questions back into Canvas modules/quizzes, including JSON export  

### Enhancements & Stretch Goals (Weeks 7–8)

- Ability to customize question answers and text post-generation  
- Add extra context input before question generation  
- Save drafts of generated quizzes for later editing  
- Support multiple LLM providers/models  
- Expand question types beyond multiple-choice  
- Complete documentation, testing, and final demo preparation  

---

## Risk Management

- If development delays occur, focus first on completing Core Functionality and basic LLM Integration.  
- Postpone enhancements and stretch goals if needed to meet MVP deadlines.  
- Implement graceful error handling for API or LLM failures.  
- Keep regular checkpoints to adjust priorities as needed.

---

## Tracking & Updates

- The roadmap will be regularly updated based on development progress.  
- Use GitHub Projects and Issues to track feature progress and tasks.  
- Link to GitHub Project board: [insert your project board link here]

---

## Contribution

Contributions and feedback are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

*Last updated: 2025-06-12*