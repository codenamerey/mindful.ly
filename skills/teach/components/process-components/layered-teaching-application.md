# Layered Teaching Application

Use this layout once a workspace has automated grading, generation, authentication, profiles, or multiple teacher workflows:

```text
app.py
learning/
  bootstrap.py
  domain/
  application/
  infrastructure/
  interfaces/http/
tests/
```

Keep curriculum, progression, evidence, revision, and review rules in `domain/`. Coordinate one use case per application service through injected ports. Put SQLite, files, uploads, authentication, and provider SDKs in `infrastructure/`. Let HTTP blueprints translate transport values only. Wire collaborators in `bootstrap.py`; keep `app.py` as a compatibility and execution facade.
