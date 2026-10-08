# Railway deployment

Deploy the complete repository with `railway.toml` and `infra/Dockerfile`. The Docker command binds to `0.0.0.0` and Railway's injected `PORT`. The configured health check is `/api/health`, and the app uses one replica with one worker.

## Service settings

1. Create a Railway project and a service for `Dpkch06/supportjudge` using the integrated deployment commit.
2. Mount a persistent Railway volume at `/data`.
3. Set `SUPPORTJUDGE_DB=/data/supportjudge.db` and `SUPPORTJUDGE_CONFIG=openrouter.json`.
4. Set `OPENROUTER_API_KEY` privately in Railway variables. Do not commit it or include it in build arguments.
5. Deploy, wait for the health check, and generate a public domain targeting the app's port.
6. Verify `/api/health`, the homepage, `/api/datasets`, and model selection before submitting a live experiment.

The volume preserves experiments, cached calls, and human reviews across deployments. An empty volume starts with no saved experiments. The developer's local SQLite database is not uploaded by this deployment.

The current app has no authentication. Anyone who can reach the public app can submit paid model calls and review data. Model credentials remain on the server. This deployment does not add an access-control system.

## Current status

The integrated checkout passed all 31 tests. Railway project creation was attempted on October 8, 2026, but the account returned `Free plan resource provision limit exceeded`. No project, service, domain, or public deployment was created by that attempt. Deployment requires available capacity in the Railway workspace.

## References

- [Railway Dockerfiles](https://docs.railway.com/builds/dockerfiles)
- [Railway health checks and PORT](https://docs.railway.com/deployments/healthchecks)
- [Railway services and persistent storage](https://docs.railway.com/services)
