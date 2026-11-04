# Other machines

`hc machine ls` lists them. Your own file and shell tools only touch the machine you run
on; everything else goes through hc.

```sh
hc exec --on box --cwd /srv/app git status            # one command, exact output
hc exec --on box sh -c 'cd ~/app && make test 2>&1 | tail -20'
hc file read --on box /srv/app/src/x.rs --offset 200 --limit 100
hc file edit --on box /srv/app/src/x.rs --old 'exact text' --new 'replacement'
hc file write --on box /srv/app/notes.md < notes.md
hc run --bg --on box --cwd /srv/app --name build cargo build   # address: box/tN
hc wait box/tN; hc read box/tN --lines 40
```

- `exec` runs with the remote core's minimal PATH: tools from nix, devbox or `~/.local`
  aren't found. Go through `sh -c` with full paths or an explicit `PATH=…`.
- Remote paths start at that machine's home unless `--cwd` is set.
- `file edit` needs the old text exactly once; add context until it's unique. Several
  `--old`/`--new` pairs apply all or nothing.
- A machine link can hang while `hc machine ls` still says connected. If a remote command
  stalls, tell the person; don't retry in a loop.
- Long or heavy remote work goes in a remote terminal (`hc run --bg --on`), not `exec`.
