# Auto-Memory: Post-Commit Instructions

This prompt is injected automatically after a git commit, merge, cherry-pick, or rebase when auto-memory is enabled.

## What to do

1. Extract the **commit message** from the most recent git operation using:
   ```bash
   git log -1 --pretty=format:"%H %s" 2>/dev/null
   ```

2. Get a brief **changed files summary**:
   ```bash
   git diff-tree --no-commit-id --name-status -r HEAD 2>/dev/null
   ```

3. Compose a memory string in this format:
   ```
   [commit <short-hash>] <commit message> | files: <A/M/D file1, file2, ...>
   ```

4. Store the memory using the transcendence-memory API:
   ```bash
   CONFIG="$HOME/.transcendence-memory/config.toml"
   ENDPOINT=$(grep '^endpoint' "$CONFIG" | sed 's/.*= *"//' | sed 's/".*//')
   API_KEY=$(grep '^api_key' "$CONFIG" | sed 's/.*= *"//' | sed 's/".*//')
   CONTAINER=$(grep '^container' "$CONFIG" | sed 's/.*= *"//' | sed 's/".*//')
   MEM_ID="commit-$(git log -1 --pretty=format:'%h')"

   curl -sS -X POST "${ENDPOINT}/ingest-memory/objects" \
     -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
     -d "{\"container\":\"${CONTAINER}\",\"objects\":[{\"id\":\"${MEM_ID}\",\"text\":\"<composed memory string>\",\"tags\":[\"auto-commit\"]}],\"auto_embed\":true}"
   ```

5. Report the result briefly in one line. Do NOT ask the user for confirmation.

## Important

- If the API call fails, report the error but do not retry.
- Keep the memory concise — one line, under 500 characters.
- Tag all auto-commit memories with `auto-commit` for easy filtering.
