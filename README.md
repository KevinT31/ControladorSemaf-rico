<div align="center">

# Adaptive Traffic Control — Research Workspace

### Thesis Workspace · Simulation · Security Experiments · Documentation Tooling

</div>

---

## Purpose

This repository is the **broader research workspace** around an adaptive traffic-signal control project.

It intentionally contains more than the clean implementation:

- the traffic-control software under **Diseño Software/**
- experimental SUMO scenarios and comparison outputs
- thesis-oriented research material
- security/authentication experiments
- a local LaTeX/documentation utility
- references and supporting tooling

For the cleaner implementation-focused repository, use:

**[ControladorSemaforicoTFC](https://github.com/KevinT31/ControladorSemaforicoTFC)**

## Workspace Map

~~~text
.
├── Diseño Software/   adaptive traffic-control research implementation
├── Ejemplos/          supporting examples
├── REFERENCES.md      external research references
├── public/             local LaTeX editor frontend
├── scripts/            local tooling
├── server.js           local editor server
└── package.json
~~~

## Main Research System

The project under **Diseño Software/** extends the adaptive traffic-control work with research-oriented capabilities and experiments around:

- computer vision
- congestion estimation
- fuzzy/adaptive traffic control
- SUMO / TraCI
- comparative simulation
- FastAPI services
- web visualization
- functional-safety checks
- authentication/RBAC experiments
- auditability and traceability
- broader Lima scenarios

See [Diseño Software/README.md](Dise%C3%B1o%20Software/README.md) for implementation notes.

## Security Hygiene

This public workspace does **not** hardcode demo passwords or a fixed JWT signing key.

The demo-oriented authentication layer expects local environment configuration derived from the included environment template.

The repository also excludes local backups, runtime artifacts, model binaries and generated workspace files from normal version control.

## Research References

Third-party research papers are not stored as bundled PDFs.

[REFERENCES.md](REFERENCES.md) keeps traceable external references instead, reducing repository weight and avoiding unnecessary redistribution of third-party documents.

## Local Documentation Utility

The repository root contains a lightweight local LaTeX editor built with Node.js and Express.

Capabilities include:

- file-tree navigation
- source editing
- ZIP import
- PDF preview
- local Tectonic / LaTeX compilation

### Run locally

~~~powershell
npm install
npm run install-tectonic
npm start
~~~

Default local address:

~~~text
http://127.0.0.1:3042
~~~

## Why This Repo Exists Separately

The research workspace preserves context that would make the implementation repository unnecessarily noisy:

- experiments
- thesis-specific material
- presentation/demo workflows
- security extensions
- comparison outputs
- supporting documentation tools

That separation keeps **ControladorSemaforicoTFC** easier to evaluate as a software project while retaining the broader research history here.

## Repository Boundaries

This is not a production traffic-management system.

The project is research/simulation oriented and should not be interpreted as field-certified infrastructure or a safety-certified traffic controller.

---

### What this workspace demonstrates

**Research engineering · experiment organization · simulation workflows · software/security prototyping · technical documentation discipline**
