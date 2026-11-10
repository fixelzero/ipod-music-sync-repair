# iPod Music Sync Repair

**macOS Apple Music + Finder + classic iPod troubleshooting toolkit** · Python 3.9+ · unofficial project

Turn Finder's *“could not be found”* sync errors into review playlists, inventory HLS `.movpkg` packages, and match leftover package metadata against Apple Music. **No included mainline tool deletes music or bypasses DRM.** Download repair is manual in Music.

> **Project status:** Successfully used in one iPod Video 5.5 repair journey, November 2026. Scripts are workflow-specific and not a generally validated consumer application. The reported results below describe one Mac, not a universal guarantee.

## Results from the documented repair

| Observation | Result |
| --- | ---: |
| Apple Music library | 24,321 track objects |
| File tracks | 10,244 |
| Other track objects | 14,077 (not necessarily all cloud-only) |
| Initial HLS inventory | 1,552 `.movpkg` packages, 60.86 GiB |
| Intermediate inventory | 803 packages, 32.54 GiB |
| Final leftover inventory | 327 packages, 14.22 GiB |
| Final file-track `.movpkg` references | 0 |
| Final V6 match classifications | 49 exact; 26 title/artist; 22 ambiguous versions; 5 ambiguous exact; 225 not found |
| Final Repair 01 | 22 tracks queued and repaired by user |
| Review 02 | 25 unique tracks reviewed, already MP3/M4A |
| Review 03 | 24 unique tracks reviewed |
| Final package cleanup | 327 deleted manually after path-set validation; 0 remaining |
| Available storage | 62 GiB → 76 GiB after final cleanup |

The cleanup **did not demonstrate** that all other Music track types were independent of those files. File-track reference checks covered only the 10,244 file tracks. After deletion, playback and iPod sync should be retested. The project does not claim every track in the library was proven playable or syncable.

## What is included

| Script | Purpose |
| --- | --- |
| `scripts/ipod_repair_batch_v4.py` | Parse Finder sync-error text, create numbered review playlists and batch reports |
| `scripts/ipod_music_repair_v5_1.py` | Read-only `.movpkg` inventory with sizes and paths |
| `scripts/ipod_music_repair_v5_3_2.py` | Bounded HLS classification; separately opted-in playlist queue |
| `scripts/ipod_hls_finish_all.py` | Batch organizer for the V5.3.2 workflow; see hardcoded paths in source |
| `scripts/ipod_hls_v6_library_match.py` | Bulk metadata matching across all Music track objects; optional exact-match playlist |
| `scripts/ipod_hls_review03.py` | Best-effort ambiguous-version review playlist; see dependency note below |
| `scripts/legacy/` | Earlier iterations retained for historical study; **not the recommended entry point** |

## Requirements

- macOS with the Music app and Finder-based iPod syncing
- Python 3.9 or later; no third-party Python packages required for these scripts
- Permission for Terminal to control Music: System Settings → Privacy & Security → Automation
- Backups of important library databases, playlists, original audio and metadata

## Quick start: Finder missing-file errors

Save a plain-text Finder sync error report as `~/Downloads/Errors.txt`. Copy the scripts you need into `~/Downloads/`, or adapt their hardcoded paths before running.

```bash
python3 -u ~/Downloads/ipod_repair_batch_v4.py ~/Downloads/Errors.txt --preview --batch 5
python3 -u ~/Downloads/ipod_repair_batch_v4.py ~/Downloads/Errors.txt --batch 5
```

The batch number `5` is an **example from the documented repair**, not a requirement for new users. Pick an unused number. Review each `iPod Repair - Batch NN` playlist; V4 matches by title and can include wrong versions.

## Quick start: read-only HLS inventory

```bash
python3 -u ~/Downloads/ipod_music_repair_v5_1.py --scan-hls
```

This creates `~/Desktop/iPod Repair Batches/hls_inventory_YYYYMMDD_HHMMSS.csv`. HLS package count is **not** a count of unique songs.

## Scan packages against Music (V5.3.2)

```bash
python3 -u ~/Downloads/ipod_music_repair_v5_3_2.py scan \
  "$HOME/Desktop/iPod Repair Batches/hls_inventory_YYYYMMDD_HHMMSS.csv" \
  --start 0 --limit 25
```

Use your actual inventory filename. Review the resulting CSV before running `queue --help` and opting into playlist creation. `scan` is read-only.

## Library-wide matching (V6)

V6 was designed specifically for the **327-package leftover report** named `hls_leftovers_final_scan.csv` in `~/Desktop/iPod Repair Batches/`. It requires that report and expects exactly 327 rows. It is **not** a general-purpose command for arbitrary inventories without editing the script.

```bash
python3 -u ~/Downloads/ipod_hls_v6_library_match.py --report-only
# After inspecting hls_leftovers_v6_matches.csv:
python3 -u ~/Downloads/ipod_hls_v6_library_match.py --create-playlists
```

V6 performs four bulk Music metadata queries (name, artist, album, persistent ID) and applies Unicode/case/punctuation normalization. `--create-playlists` uses exact title+artist+album matches and excludes previously identified AAC entries; it **does not independently validate all current download formats**. If the report already exists, report-only mode refuses to overwrite it. Playlist names are fixed and cannot be reused without editing the script.

`ipod_hls_review03.py` requires both the V6 report and `~/Downloads/ipod_hls_v6_library_match.py`. It selects one candidate per ambiguous package on a **best-effort** basis, which can select an alternate album or recording. Treat the playlist as a review aid, not a verified repair list.

## Repair method (manual)

1. Review matched tracks in Music, including artist, album, cloud status, and current file location.
2. For tracks already playable as MP3/M4A, leave them alone.
3. For cloud-available tracks without a local copy, download normally.
4. For a verified stale download, use **Remove Download**, not **Delete from Library**, then download again. Set Music's download quality to AAC 256 kbps where appropriate.
5. Test playback and iPod sync again; do not infer success from playlist creation alone.

**Apple Music subscription DRM:** Subscription-protected downloads are not converted to portable files by these scripts. AAC 256 kbps settings do not grant ownership or remove DRM. Only sync content you are entitled to transfer.

## Important caveats

- `.movpkg` directories can be referenced by track types not covered by a `file track` location audit.
- Finder may surface additional failures after earlier errors are resolved; there is no verified 99/100-error cap.
- Earlier V4 has a known `osascript` argument issue for titles beginning with `-` (e.g. `-MC-`).
- Album editions, live versions, Unicode normalization, and duplicate persistent IDs require manual judgment.
- V6 report matches do not prove a song is downloaded, AAC, playable, or syncable.
- **Do not run cleanup/deletion based solely on matching results.** The final 327-package deletion was a separate, explicitly confirmed, user-specific operation, and is intentionally **not included** as a reusable script.
- If macOS Finder stalls during sync, inspect device services, cable, disk health and mount state before changing Music data. The user's device did not have an `iTunesLock` file in the documented mount troubleshooting.

See [CHANGELOG.md](CHANGELOG.md), [docs/REPAIR_JOURNEY.md](docs/REPAIR_JOURNEY.md), [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md), and [docs/SAFETY.md](docs/SAFETY.md).

## Privacy

No real sync-error exports, real playlist CSVs, listening history, library persistent IDs, personal directory paths, or external-drive names are bundled. The sample input is synthetic. Review source scripts for fixed filenames before running or publishing forks.

## License

MIT. Unofficial project; not affiliated with Apple.
