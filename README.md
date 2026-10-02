# Adaptive Traffic Control — Research Workspace

Research and development workspace related to an adaptive traffic-signal control project.

The repository combines the traffic-control software itself with research references and a lightweight local LaTeX editor used to work with technical documentation.

## Main Project

The traffic-control implementation is located in:

```text
Diseño Software/
```

It contains the adaptive traffic-control stack, including:

- Computer-vision processing
- Adaptive and fuzzy control logic
- SUMO traffic simulation integration
- FastAPI backend services
- Web visualization
- Comparative traffic-control experiments

See [Diseño Software/README.md](Dise%C3%B1o%20Software/README.md) for execution details.

## Local LaTeX Utility

The repository root also contains a small local LaTeX editor built with Node.js and Express. It provides:

- File-tree navigation
- Source editing
- ZIP import
- PDF preview
- Local Tectonic / LaTeX compilation

### Run locally

```powershell
npm install
npm run install-tectonic
npm start
```

The server normally starts at:

```text
http://127.0.0.1:3042
```

Local working directories, generated PDFs, build files, logs and backup copies are intentionally excluded from Git.

## Repository Organization

```text
.
├── Diseño Software/                       # Adaptive traffic-control system
├── Ejemplos/                              # Supporting examples
├── REFERENCES.md                         # External research references
├── public/                                # Local LaTeX editor frontend
├── scripts/                               # Local tooling
├── server.js                              # Local editor server
└── package.json
```

## Research References

Third-party papers are referenced in [REFERENCES.md](REFERENCES.md) instead of being stored as PDF copies in the repository.

## Portfolio Context

This repository documents the broader research workspace around the adaptive traffic-control project. The cleaner implementation-focused repository is `ControladorSemaforicoTFC`.
