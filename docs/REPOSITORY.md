# Repository structure

This repository uses npm workspaces to keep frontend and microservice code in
one repository while giving each application and service its own package.

```text
apps/
  frontend/             Frontend application workspace placeholder
microservices/
  aiservice/             NestJS TCP microservice
docs/
  REPOSITORY.md           Repository layout and development commands
```

## AI microservice

The NestJS service lives in `microservices/aiservice`. It uses TCP transport and
listens on `MICROSERVICE_HOST` and `MICROSERVICE_PORT`, defaulting to
`0.0.0.0:4001`. Its starter message handler responds to `health.check`.

## Development

Use Node.js `24.21.0` (`nvm use` with the included `.nvmrc`), then install
dependencies from the repository root:

```sh
npm install
npm run dev:aiservice
```

Build the AI microservice with `npm run build`. The workspace scripts target
the `@mindfully/aiservice` package in `microservices/aiservice`.

Nx Console can open this repository root as an Nx workspace. The root
`nx.json` enables Nx task caching, and `npx nx show projects` lists detected
projects. Run an inferred package script through Nx with
`npx nx run @mindfully/aiservice:build`.
