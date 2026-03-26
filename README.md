# AgentOS (ODD PLAYGROUND)

Self-evolving operating infrastructure for AI agents: replayable runs, policy gates, and human approvals. See `agentos_product_brief.md` for the full product spec.

## Golden path (about 5 minutes, local)

Do these steps **in order** from the repo root (`odd-agentos`). Use **two terminals**.

### 1. Install Python deps

```powershell
cd c:\projects\odd-agentos
pip install -e ".[dev]"
pip install -e "./agentos-sdk[dev]"
```

### 2. Terminal A — API on port 8080

```powershell
cd c:\projects\odd-agentos
python -m agentos.server
```

Leave this running. Check: [http://localhost:8080/api/health](http://localhost:8080/api/health) should return JSON with `"status":"ok"`.

### 3. Terminal B — dashboard (Vite proxies `/api` → `localhost:8080`)

```powershell
cd c:\projects\odd-agentos\dashboard
npm install
npm run dev
```

Open the URL Vite prints (usually **http://localhost:5173**).

### 4. Run the demo

1. In the UI, click **New run** and keep the default workflow path **`workflows/sample.yaml`** (or enter that exact path). Start the run.
2. You should land on the run detail page. **Step 1** (`greet`) completes automatically; **Step 2** (`summarize`) waits for **approval**.
3. Click **Approve** (and **System MRI** if you want a diagnosis JSON).
4. **Runs** list should show the run as **completed**; **Audit log** shows `events.jsonl`-style events.

**CLI equivalent (optional):**

```powershell
cd c:\projects\odd-agentos
python -m agentos run workflows/sample.yaml
```

If the run stops at approval, use the dashboard to approve, or use the API (`POST /api/runs/.../approve/...`).

### Optional: real OpenAI for step outputs

If **`OPENAI_API_KEY`** is set in the environment, workflow steps use the **OpenAI API** (model `gpt-4o-mini` by default). Set **`AGENTOS_FORCE_STUB=true`** to always use the deterministic stub (no network). See `.env.example`.

## Quick start (short)

```powershell
cd c:\projects\odd-agentos
pip install -e ".[dev]"
pip install -e "./agentos-sdk[dev]"

# Terminal 1 — API
python -m agentos.server

# Terminal 2 — dashboard
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

In containers, use workflow paths under **`/app/workflows/...`** (see `Dockerfile.api`).

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
