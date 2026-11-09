# iPod Music Sync Repair

A macOS utility for turning Finder/iPod **“could not be found”** sync errors into reviewable Apple Music playlists, one batch at a time.

**Status:** Work in progress — currently using **Batch 6**. The batch workflow has created playlists successfully, but the entire library has **not** been verified as repaired.

> **Safety:** The scripts in this repository do not delete songs, remove downloads, or bypass Apple Music DRM. They match tracks and build playlists. Download repair and library cleanup are manual, review-first operations.

## Why this exists

When syncing a modified iPod Video 5.5 with Finder on macOS, some tracks in the Music library failed with messages such as:

```text
“Example Song” was not copied to the iPod “My iPod” because it could not be found.
```

The library contains personally ripped music, iTunes Match **Matched** and **Uploaded** entries, and some Apple Music subscription entries. Some missing files could be recovered by removing stale downloads and downloading again. Other tracks continued to fail. Apple Music subscription downloads are generally DRM-protected and not usable on a classic iPod; this tool does not convert them.

The original sync-error report contained 101 error entries / 98 unique titles. Later reports surfaced further failures after earlier ones were addressed. In this user's testing, reports appeared to show roughly 99–100 titles at a time; **this is an observation, not a verified Finder limit**.

## Requirements

- macOS with the **Music** app and Finder-based iPod syncing
- Python **3.9+** (tested for syntax with Python 3.9-compatible features; real-world use reported on Python 3.9.6)
- Terminal permission to control Music under **System Settings → Privacy & Security → Automation**
- A plain-text Finder sync-error export (`Errors.txt`)
- Backups of your Music library database and original audio files before any manual library changes

No third-party Python packages are required.

## Quick start — current batch workflow (V4)

1. Sync your iPod in Finder and save the **latest** missing-song error text as `~/Downloads/Errors.txt`.
2. Put [`scripts/ipod_repair_batch_v4.py`](scripts/ipod_repair_batch_v4.py) in `~/Downloads/`.
3. For a first run on an existing four-batch workflow, explicitly start at batch 5:

   ```bash
   python3 -u ~/Downloads/ipod_repair_batch_v4.py ~/Downloads/Errors.txt --batch 5
   ```

4. For later runs, omit `--batch`:

   ```bash
   python3 -u ~/Downloads/ipod_repair_batch_v4.py ~/Downloads/Errors.txt
   ```

5. In Music, review the playlist named `iPod Repair - Batch 05`, `Batch 06`, etc. **Matches are by title only**, so they may include other artists or recordings with identical titles.
6. Review cloud status before taking action. Keep owned **Matched**, **Uploaded**, and **Purchased** tracks. Subscription tracks can be removed manually from the library **only if you explicitly want them removed**, understanding that removal propagates to other synced devices and playlists.
7. For verified missing owned tracks with recoverable cloud copies, try downloading again. Do not bulk-delete original files or library entries.
8. Sync the iPod again, save a fresh error report, and repeat as needed.

### Preview without creating a playlist

```bash
python3 -u ~/Downloads/ipod_repair_batch_v4.py ~/Downloads/Errors.txt --preview --batch 7
```

Choose a batch number whose report does not already exist. Preview writes a report but not history, so an existing preview report will block reuse of that number until it is intentionally moved or renamed.

## Files and output

V4 creates `~/Desktop/iPod Repair Batches/` containing:

| File | Purpose |
| --- | --- |
| `batch_05_matches.csv` | Per-title match results, artist, album, persistent ID, cloud status, error details |
| `batch_history.csv` | Batch/title history used for next-batch numbering and duplicate-title detection |

Possible status values include `MATCH`, `NOT_FOUND`, `ERROR`, and `TIMEOUT`. **MATCH does not prove that the exact failed recording was found or that the audio file is healthy.** A playlist request also does not guarantee every matching track was added; verify the playlist in Music.

V4 starts its saved history at the first V4 batch; earlier V1/V2-era batches are not imported automatically. Never overwrite a previous batch report accidentally.

## Development history

| Version | What changed | Status |
| --- | --- | --- |
| Initial prototype | Parsed Finder error titles into a CSV; basic Music matching | Superseded |
| Fast matcher | Per-title Music lookups, progress output, optional `--queue` playlist | Used successfully |
| V3 inspection | Experimental persistent-ID and local-path inspection, optional download request | **Not used/tested in the reported workflow** |
| V4 batch manager | Numbered playlists, saved reports, persistent batch history, cloud-status reporting | **Current working version; Batch 6 in progress** |

The earlier fast matcher is included under `scripts/` for historical reference. V3 is included as **experimental only**; do not run its download mode without reviewing the implementation and testing on a disposable subset.

## Known limitations

- **Title-only matching:** An error log usually provides song titles, not artist or persistent ID. Duplicate names may produce false-positive playlist entries. The first matching report had 166 candidate library tracks for 98 titles, not 166 confirmed failures.
- **Hyphen-prefixed titles:** V4 passes title arguments to `osascript` in a way that causes titles such as `-MC-`, `-MC- End`, and `-VTR-` to be treated as command options. These produced three `ERROR` rows in Batch 5. This is a known script bug, **not evidence of bad music files**.
- **Partial operations:** A per-title AppleScript operation may add some songs before failing or timing out. Reports and playlists should be checked manually.
- **No automatic file repair:** V4 creates review playlists only; it cannot prove iCloud availability or successfully redownload audio.
- **No verified 99-song cap:** Repeated reports of ~99–100 failures suggest batching in the observed workflow, but no documented hard cap has been established.
- **Cloud status isn't ownership proof:** Confirm a track's provenance before deleting anything. Do not delete `Matched`/`Uploaded` entries merely because a sync fails.
- **iTunes Match limitations:** Matched cloud copies can differ from original rips. Keep backups of the original recordings.

## Troubleshooting

**No playlist appears:** Verify the command completed, then run:

```bash
osascript -e 'tell application "Music" to get name'
osascript -e 'tell application "Music" to get name of every user playlist'
```

If Music automation hangs, check Automation permissions, Music dialogs, and retry only after stopping the old process (`Control+C`).

**Error rows:** Open `batch_XX_matches.csv` and inspect the `Details` column. Do not assume the last songs printed are the error rows.

**Playlist has too many songs:** V4 includes *all* library matches for a title. Verify artists/recordings before removing or redownloading anything.

**A song keeps failing:** Stop repeating bulk re-downloads for that song. Check file location, cloud status, file kind/DRM, and whether the original rip is still available in a backup.

## Privacy and publishing

The repository intentionally **does not include** personal `Errors.txt` files, real batch reports, playlists, or persistent IDs. Those can reveal listening history, account/library metadata, and device names. Use the synthetic example in `examples/` when demonstrating the tool publicly.

## Future improvements

- Fix hyphen-prefixed `osascript` arguments.
- More reliable identification using artist/album when source reports provide them.
- Track recurring failures across batches using persistent IDs when possible.
- Explicit audit of subscription vs matched/uploaded/purchased tracks.
- Verify actual downloaded file paths before reporting a repair successful.

## Disclaimer

Unofficial personal utility, not affiliated with Apple. Use at your own risk. Back up your library and music files. Apple Music subscription downloads are not made iPod-compatible by this project.

## License

MIT — see [LICENSE](LICENSE).
