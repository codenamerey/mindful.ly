# Authenticated Learner Profiles

Treat authenticated teacher access as visible application state. Keep the tracker readable while signed out, but make review, Ask teacher, generation, and lesson revision explain that authentication is required.

Derive a stable opaque profile key with a one-way hash of the provider identity. Store it in an HTTP-only, SameSite cookie and isolate each profile in its own migrated database or namespace. Transfer anonymous progress once into an empty authenticated profile. Logout clears the session cookie and provider session without deleting progress.

Expose checking, signed-out, pending, authenticated, and error states. Keep pending and failed login recoverable.
