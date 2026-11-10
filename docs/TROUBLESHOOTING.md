# Troubleshooting

## Finder sync never advances / activation timeout

Check the iPod mount, cable, disk health, and Finder/Music state. The documented case included FAT32 issues and error 60; restarting the Apple device discovery/agent processes and Finder helped. Do not assume `iTunesLock` exists or that removing it is appropriate.

## Finder says a song “could not be found”

Export errors as plain text, use V4 to generate a review playlist, inspect actual title/artist/album and file locations, then repair downloads manually. Re-sync and collect a fresh report. A matching title alone is not sufficient evidence of the same recording.

## `.movpkg` package vs `.m4a`

A `.movpkg` package is not an ordinary portable AAC track. A Music download setting of AAC 256 kbps can help with eligible downloads, but not with subscription DRM. Do not convert or rename package directories to `.m4a`.

## No verified match

V5.3.2 relies on conservative file-track location/metadata checks. V6 broadens to all Music track objects. `NOT_FOUND` means the script did not find a match under its rules; it does not prove the original song is absent from every source.

## Duplicate title / album / persistent ID

V6 can find multiple editions. Review before redownloading. Two package paths may resolve to the same persistent ID, so deduplicate playlist entries. Review 03 deliberately uses best-effort selections and can choose the wrong edition.

## macOS Terminal `zsh: parse error near '}'`

Usually means a fragment of Python or a malformed shell paste was entered at the zsh prompt. Paste the entire heredoc including terminator, or save a plain-text `.py` file. Use Control+C to exit a dangling `>` continuation prompt.

## Python `SyntaxError` begins with `{\rtf1`

TextEdit saved Rich Text rather than plain text. Use Format → Make Plain Text before saving, or create the `.py` file with `cat > file.py <<'PY'` in Terminal.

## `EOFError` at `input()` inside `python3 - <<'PY'`

The heredoc consumes standard input, so interactive `input()` may reach EOF. Run a saved Python file normally if it needs confirmation input.

## Disk free space differs from expected

Check `df -h /` before and after. APFS snapshots, purgeable space and filesystem accounting can affect the displayed amount. Do not interpret the system volume `Used` column alone as total data volume usage.
