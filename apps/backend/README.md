# Backend

NestJS modular monolith. The application runs as one HTTP process while each
business capability lives in its own feature module under `src/modules`.

The backend listens on `HOST` and `PORT` (defaults: `0.0.0.0:4000`) and exposes:

- `GET /health` for health checks
- `POST /teach` with a JSON body shaped as `{ "topic": "..." }`

Run it from the repository root with `npm run dev:backend`.
