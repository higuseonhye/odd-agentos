# AgentOS (ODD PLAYGROUND)

Self-evolving operating infrastructure for AI agents: replayable runs, policy gates, and human approvals. See `agentos_product_brief.md` for the full product spec.

## Quick start (development)

```powershell
cd c:\projects\odd-agentos
pip install -e ".[dev]"
pip install -e "./agentos-sdk[dev]"

# Terminal 1 — API
python -m agentos.server

# Terminal 2 — dashboard (proxies /api → localhost:8080)
cd dashboard
npm install
npm run dev
```

Open the Vite URL (e.g. http://localhost:5173). API health: http://localhost:8080/api/health

## CLI

```powershell
python -m agentos --help
python -m agentos run workflows/sample.yaml
```

## Tests

```powershell
python -m pytest tests agentos-sdk/tests -v
```

## Docker (production-style)

```powershell
make prod
# or: docker compose -f docker-compose.prod.yml up -d --build
```

## GitHub: first push

1. Create an empty repository on GitHub (same name as your folder, e.g. `odd-agentos`), **without** adding a README if you already committed locally.
2. Point `origin` at the correct URL (fix username/repo if needed):

   ```powershell
   git remote set-url origin https://github.com/<YOUR_USER>/odd-agentos.git
   ```

3. Push (HTTPS may require a [Personal Access Token](https://github.com/settings/tokens) instead of a password):

   ```powershell
   git push -u origin main
   ```

If you see `Repository not found`, the repo does not exist yet, the URL is wrong, or you are not authenticated.

## License

Proprietary / ODD PLAYGROUND — adjust as needed.
