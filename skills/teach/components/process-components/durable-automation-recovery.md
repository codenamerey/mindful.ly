# Durable Automation Recovery

Persist every review, teacher question, and generation job before launching its worker. Run one guarded recovery pass per process startup:

1. Resume pending and explicitly recoverable failed reviews.
2. Resume pending teacher questions.
3. Resume pending lesson generations from the validated plan.
4. Recheck the completed curriculum frontier.

Use conditional terminal writes against pending state. Duplicate workers may perform provider work, but only one may commit. Never overwrite pass, fail, or completed-generation state.
