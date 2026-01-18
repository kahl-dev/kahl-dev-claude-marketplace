# Beyond MCP Pattern

This marketplace uses the **Beyond MCP** pattern for Claude Code skills - achieving 90%+ context savings compared to traditional MCP servers.

## The Problem with MCP

MCP (Model Context Protocol) servers are powerful but expensive:

- **~10,000 tokens** just to load tool definitions
- Background process that must run continuously
- Complex setup and configuration
- State management overhead

For many use cases, this is overkill.

## The Solution: Progressive Disclosure

Instead of loading everything upfront, we use **progressive disclosure**:

1. **SKILL.md** - A concise guide (~800 tokens) that tells Claude which script to use
2. **Scripts** - Self-contained Python files with UV inline dependencies
3. **--help** - Detailed usage loaded only when needed

```
Traditional MCP:
┌─────────────────────────────────────────┐
│ Load all tools (~10,000 tokens)         │
│ Start server process                     │
│ Maintain connection                      │
└─────────────────────────────────────────┘

Beyond MCP:
┌─────────────────────────────────────────┐
│ Load SKILL.md (~800 tokens)             │
│ Run script when needed                   │
│ No background process                    │
└─────────────────────────────────────────┘
```

## Context Savings

| Approach | Tokens | % of 100k Context |
|----------|--------|-------------------|
| MCP Server | ~10,000 | 10% |
| Beyond MCP | ~800 | 0.8% |
| **Savings** | **~9,200** | **90%+** |

## Script Architecture

Each script is self-contained:

```python
#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx>=0.27.0",
#     "click>=8.1.7",
# ]
# ///

"""
Script description and usage.
"""

import click
import httpx

@click.command()
def main():
    # Implementation
    pass

if __name__ == "__main__":
    main()
```

Key features:
- **UV inline dependencies** - No virtual env setup
- **Click CLI** - Consistent interface with `--help`
- **Dual output** - Human-readable by default, `--json` for automation
- **Self-contained** - Intentional code duplication for isolation

## When to Use Beyond MCP

✅ **Good fit:**
- API integrations (REST, GraphQL)
- CLI tool wrappers
- File operations
- One-shot operations

❌ **Consider MCP instead:**
- Real-time streaming data
- Complex state management
- Bidirectional communication
- Requires persistent connection

## Implementation Guide

1. **Create SKILL.md** with:
   - Frontmatter (name, description, triggers)
   - Quick reference table
   - Links to scripts

2. **Create scripts** with:
   - UV inline dependencies
   - Click CLI interface
   - Dual output (human + JSON)
   - Clear `--help` documentation

3. **Organize**:
   ```
   skills/
   └── your-skill/
       ├── SKILL.md
       └── scripts/
           ├── operation-1.py
           ├── operation-2.py
           └── ...
   ```

## Real-World Example

The `homeassistant` plugin has 22 scripts covering:
- Entity control (6 scripts)
- Automation management (4 scripts)
- Scene operations (2 scripts)
- Config deployment (5 scripts)
- And more...

All accessible through a single 800-token SKILL.md guide.
