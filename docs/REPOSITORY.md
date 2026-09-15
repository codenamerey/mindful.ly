# Repository structure

This repository uses npm workspaces to keep the frontend and backend in one
repository while giving each application its own package.

```text
apps/
  backend/              NestJS modular monolith
  frontend/             Frontend application workspace placeholder
docs/
  REPOSITORY.md          Repository layout and development commands
```

## Backend

The NestJS modular monolith lives in `apps/backend`. It runs as one HTTP process
and groups business capabilities into feature modules under `src/modules`.
The health and teaching capabilities are independent Nest modules composed by
the root application module.

The backend listens on `HOST` and `PORT`, defaulting to `0.0.0.0:4000`. Use
`GET /health` for health checks and `POST /teach` with a `topic` in the JSON body
to start a teaching session.

## Development

Use Node.js `24.21.0` (`nvm use` with the included `.nvmrc`), then install
dependencies from the repository root:

```sh
npm install
npm run dev:backend
```

Build the backend with `npm run build`. The workspace scripts target the
`@mindfully/backend` package in `apps/backend`.

Nx Console can open this repository root as an Nx workspace. The root
`nx.json` enables Nx task caching, and `npx nx show projects` lists detected
projects. Run an inferred package script through Nx with
`npx nx run @mindfully/backend:build`.
