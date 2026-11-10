# CONTENT-FACTORY Agent Guidelines

## Codebase Architecture & Graphify Navigation
This project has an AST-mapped knowledge graph at `graphify-out/graph.json` and an Obsidian vault at `graphify-out/obsidian/`.
- **Never guess imports, endpoints, or file relations.**
- Before modifying or auditing any code, query the graph with:
  `python -m graphify query "<concept or question>" --graph "D:\CONTENT-FACTORY\graphify-out\graph.json"`
- For function call tracing or cross-file connections, use:
  `python -m graphify path "<source_symbol>" "<target_symbol>" --graph "D:\CONTENT-FACTORY\graphify-out\graph.json"`
- After modifying or adding files, keep the graph synchronized with:
  `python -m graphify update D:\CONTENT-FACTORY`

## Director Second-Brain (Obsidian Vault)
- Director styles, hooks, sfx, and narrative patterns live in `D:\CONTENT-FACTORY\director_vault\`.
- Use `backend.engine.vault_graph.query_director_vault(prompt)` to retrieve relevant hook formulas and style guidelines (0 MB background RAM).
- All generated scripts are auto-logged to `director_vault/scripts/` to build persistent long-term memory.

## Storage & Resource Constraints
- `D:\` drive has limited free space. Temp video files must NEVER be accumulated.
- Audio and subtitle extraction must use stream pipes or immediate cleanup.
- Never write redundant `.gguf` copies or duplicate database files.
- Single source of truth database is `D:\CONTENT-FACTORY\vault.db`.
