# tmux Reference Guide

Detailed workflows, troubleshooting, and advanced usage for the tmux skill.

## Common Workflows

### Interactive Testing

```bash
PANE=$(tmux-ctl launch zsh)
tmux-ctl send "./installer.sh" --pane=$PANE
tmux-ctl wait-for "Enter name:" --pane=$PANE
tmux-ctl send "TestUser" --pane=$PANE
tmux-ctl wait-for "Confirm (y/n)" --pane=$PANE
tmux-ctl send "y" --pane=$PANE
tmux-ctl wait-idle --pane=$PANE
OUTPUT=$(tmux-ctl capture --pane=$PANE)
echo "$OUTPUT" | grep "Success"
tmux-ctl kill --pane=$PANE
```

### Parallel Command Execution

```bash
# Launch multiple panes
PANE1=$(tmux-ctl launch zsh)
PANE2=$(tmux-ctl launch zsh)
PANE3=$(tmux-ctl launch zsh)

# Run commands in parallel
tmux-ctl send "npm test" --pane=$PANE1
tmux-ctl send "npm run lint" --pane=$PANE2
tmux-ctl send "npm run build" --pane=$PANE3

# Wait for all to complete
tmux-ctl wait-idle --pane=$PANE1 --timeout=60
tmux-ctl wait-idle --pane=$PANE2 --timeout=60
tmux-ctl wait-idle --pane=$PANE3 --timeout=60

# Capture results
tmux-ctl capture --pane=$PANE1 | grep "passed"
tmux-ctl capture --pane=$PANE2 | grep "errors"
tmux-ctl capture --pane=$PANE3 | grep "built"

# Clean up
tmux-ctl kill --pane=$PANE1
tmux-ctl kill --pane=$PANE2
tmux-ctl kill --pane=$PANE3
```

### Database Interaction

```bash
PANE=$(tmux-ctl launch zsh)
tmux-ctl send "psql mydb" --pane=$PANE
tmux-ctl wait-for "mydb=#" --pane=$PANE
tmux-ctl send "SELECT * FROM users LIMIT 5;" --pane=$PANE
tmux-ctl wait-for "mydb=#" --pane=$PANE
tmux-ctl capture --pane=$PANE | grep -A10 "SELECT"
tmux-ctl send "\q" --pane=$PANE
tmux-ctl kill --pane=$PANE
```

### Python REPL Session

```bash
PANE=$(tmux-ctl launch zsh)
tmux-ctl send "PYTHON_BASIC_REPL=1 python3" --pane=$PANE
tmux-ctl wait-for ">>>" --pane=$PANE

# Import and test
tmux-ctl send "import sys" --pane=$PANE
tmux-ctl wait-for ">>>" --pane=$PANE
tmux-ctl send "print(sys.version)" --pane=$PANE
tmux-ctl wait-idle --pane=$PANE

# Capture output
tmux-ctl capture --pane=$PANE

# Exit
tmux-ctl send "exit()" --pane=$PANE
tmux-ctl kill --pane=$PANE
```

### Long-Running Server Development

```bash
# Start server
SERVER=$(tmux-ctl launch zsh)
tmux-ctl send "npm run dev" --pane=$SERVER
tmux-ctl wait-for "Server started on port" --pane=$SERVER --timeout=30

# Make code changes, restart on file change
# Server continues running in background

# Check server logs
tmux-ctl capture --pane=$SERVER | tail -20

# Stop when done
tmux-ctl interrupt --pane=$SERVER
tmux-ctl kill --pane=$SERVER
```

## Troubleshooting

### Pane Not Responding

```bash
# Check if pane exists
tmux-ctl list-panes | jq ".[] | select(.id == \"$PANE\")"

# Send interrupt
tmux-ctl interrupt --pane=$PANE

# Force kill
tmux-ctl kill --pane=$PANE
```

### Pattern Not Found

```bash
# Increase timeout
tmux-ctl wait-for "pattern" --pane=$PANE --timeout=60

# Check what's actually in the pane
tmux-ctl capture --pane=$PANE | tail -20

# Use wait-idle instead
tmux-ctl wait-idle --pane=$PANE
```

### State Out of Sync

```bash
# View actual tmux panes
tmux list-panes

# View tracked state
tmux-ctl state | jq '.sessions[].windows[].panes'

# Clean up dead panes manually if needed
tmux-ctl kill --pane=%XYZ
```

### Commands Not Executing

**Issue**: Commands sent but nothing happens
**Solution**: Always wait for prompts

```bash
# WRONG
tmux-ctl send "python3" --pane=$PANE
tmux-ctl send "2+2" --pane=$PANE  # Too fast!

# RIGHT
tmux-ctl send "python3" --pane=$PANE
tmux-ctl wait-for ">>>" --pane=$PANE
tmux-ctl send "2+2" --pane=$PANE
```

### Python REPL Not Working

**Issue**: Python REPL doesn't respond properly
**Solution**: Use `PYTHON_BASIC_REPL=1`

```bash
# WRONG
tmux-ctl send "python3" --pane=$PANE

# RIGHT
tmux-ctl send "PYTHON_BASIC_REPL=1 python3" --pane=$PANE
```

## Advanced Usage

### Multiple Sessions (Outside tmux)

When running outside tmux, `tmux-ctl` automatically creates sessions in `.claude/tmux/sockets/`:

```bash
# First pane creates "claude-main" session
PANE1=$(tmux-ctl launch zsh)

# Subsequent panes use the same session
PANE2=$(tmux-ctl launch zsh)

# All tracked in state
tmux-ctl state | jq '.sessions[].name'
```

### Attach to Remote Session

```bash
# View socket path
tmux-ctl state | jq -r '.sessions[].socket'

# Attach manually to observe
tmux -S .claude/tmux/sockets/claude-main attach
# Detach: Ctrl+B, D
```

### Variable Names for Clarity

Use descriptive variable names:

```bash
DB_PANE=$(tmux-ctl launch zsh)
SERVER_PANE=$(tmux-ctl launch zsh)
TEST_PANE=$(tmux-ctl launch zsh)

# Easy to track which is which
tmux-ctl send "psql mydb" --pane=$DB_PANE
tmux-ctl send "npm run dev" --pane=$SERVER_PANE
tmux-ctl send "npm test" --pane=$TEST_PANE
```

### Capturing Specific Output

```bash
PANE=$(tmux-ctl launch zsh)
tmux-ctl send "git log --oneline -n 10" --pane=$PANE
tmux-ctl wait-idle --pane=$PANE

# Capture and filter
OUTPUT=$(tmux-ctl capture --pane=$PANE)
echo "$OUTPUT" | grep "feat:" | head -5
```

### Interactive Debugging Session

```bash
DEBUG=$(tmux-ctl launch zsh)
tmux-ctl send "lldb ./myapp" --pane=$DEBUG
tmux-ctl wait-for "(lldb)" --pane=$DEBUG

# Set breakpoint
tmux-ctl send "breakpoint set -n main" --pane=$DEBUG
tmux-ctl wait-for "(lldb)" --pane=$DEBUG

# Run
tmux-ctl send "run" --pane=$DEBUG
tmux-ctl wait-for "stop reason" --pane=$DEBUG

# Step through
tmux-ctl send "next" --pane=$DEBUG
tmux-ctl wait-for "(lldb)" --pane=$DEBUG

# Inspect variables
tmux-ctl send "frame variable" --pane=$DEBUG
tmux-ctl wait-idle --pane=$DEBUG
tmux-ctl capture --pane=$DEBUG

# Continue
tmux-ctl send "continue" --pane=$DEBUG
```

## Integration Examples

### With File Operations

```bash
# Edit file
# (use Edit tool to modify code)

# Test in pane
PANE=$(tmux-ctl launch zsh)
tmux-ctl send "node modified-script.js" --pane=$PANE
tmux-ctl wait-idle --pane=$PANE
tmux-ctl capture --pane=$PANE | grep "Success"
```

### With Git Operations

```bash
PANE=$(tmux-ctl launch zsh)

# Run git commands
tmux-ctl send "git status" --pane=$PANE
tmux-ctl wait-idle --pane=$PANE
STATUS=$(tmux-ctl capture --pane=$PANE)

# Analyze output
echo "$STATUS" | grep "modified:" | wc -l
```

### Multi-Agent Workflow

```bash
# Launch another Claude instance for specialized help
HELPER=$(tmux-ctl launch zsh)
tmux-ctl send "claude" --pane=$HELPER
tmux-ctl wait-for ">" --pane=$HELPER

# Ask specialized question
tmux-ctl send "Help me optimize this regex: ^[a-z]+$" --pane=$HELPER
tmux-ctl wait-idle --pane=$HELPER --timeout=30
ADVICE=$(tmux-ctl capture --pane=$HELPER)
```

## Safety Best Practices

1. **Use descriptive variable names**: `DB_PANE`, `SERVER_PANE`, `TEST_PANE`
2. **Always capture output after operations** to verify success
3. **Set appropriate timeouts** based on expected command duration
4. **Clean up panes** when done to avoid clutter
5. **Check state** with `tmux-ctl state` to debug issues
6. **Use wait-idle** when you don't know the exact prompt pattern
7. **Launch shells first** for safety and flexibility

## State File Structure

`.claude/tmux/sessions.json`:
```json
{
  "project_path": "/path/to/project",
  "sessions": [
    {
      "name": "claude-main",
      "socket": ".claude/tmux/sockets/claude-main",
      "created_at": "2025-11-24T00:00:00Z",
      "last_active": "2025-11-24T01:00:00Z",
      "status": "active",
      "windows": [
        {
          "id": "@0",
          "name": "main",
          "panes": [
            {
              "id": "%1",
              "index": 0,
              "command": "zsh",
              "created_at": "2025-11-24T00:00:00Z",
              "active": false
            }
          ]
        }
      ]
    }
  ]
}
```

## Command Reference

### All Parameters

**launch**
- `<command>` - Command to run in pane

**send**
- `<text>` - Text to send
- `--pane=<id>` - Target pane ID
- `--no-enter` - Don't press Enter after text

**capture**
- `--pane=<id>` - Target pane ID

**wait-for**
- `<pattern>` - Pattern to wait for
- `--pane=<id>` - Target pane ID
- `--timeout=<seconds>` - Max wait time (default: 30)

**wait-idle**
- `--pane=<id>` - Target pane ID
- `--idle-time=<seconds>` - How long idle (default: 2)
- `--timeout=<seconds>` - Max wait time (default: 30)

**kill**
- `--pane=<id>` - Target pane ID (cannot kill current pane)

**interrupt/escape**
- `--pane=<id>` - Target pane ID
