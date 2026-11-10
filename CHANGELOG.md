# Changelog

Development chronology reconstructed from source scripts, supplied output, and the documented repair session. Dates are November 2026 where known; not every historical prototype has a verified release date. Version names refer to workflow iterations, **not** audited production releases.

## [V6.1 workflow / Final Review 03] — 2026-11-09

- Added `ipod_hls_review03.py` to resolve 27 ambiguous package rows using best-effort metadata selection.
- Created `iPod HLS Leftovers - Final Review 03` with 24 unique Music tracks; all 27 package rows had candidate matches.
- Known limitation: some selections came from different album editions (e.g. Linkin Park compilation/EP versions). User reviewed playlist; no automated downloads or media changes.

## [V6 / Library-wide matcher] — 2026-11-09

- Added four bulk Music metadata exports (title, artist, album, persistent ID) across 24,321 track objects.
- Added Unicode/case/punctuation-normalized matching, match-status CSV, and explicit playlist opt-in.
- Results on 327 leftovers: 49 exact, 26 title+artist only, 22 ambiguous versions, 5 ambiguous exact, 225 not found.
- Created Final Repair 01 with 22 unique eligible tracks, excluding previously identified AAC IDs; user repaired them.
- A separate manual script created Review 02 with 25 unique tracks from 26 package rows; two BTS `Boy With Luv` package rows shared one Music persistent ID. Those 25 tracks were reviewed as MP3/M4A.

## [V5.3.2 / Bounded classifier] — 2026-11-09

- Added read-only bounded HLS scanning and separate opt-in playlist queueing.
- Addressed prior playlist matching/persistent-ID handling issues through V5.3 → V5.3.1 → V5.3.2 iterations.
- Scanned 327 leftovers: 272 `NO_VERIFIED_MATCH`, 37 `POSSIBLY_CONVERTED_AAC`, 18 `LOCATION_CHANGED_OR_MISMATCH`.
- Confirmed 37 candidate tracks with persistent IDs and `.m4a` locations.
- Used multiple repair playlists for previously referenced HLS tracks; 476 referenced packages were queued across five playlists (100/100/100/100/76).

## [V5.2 / HLS matching] — November 2026

- Added bounded, read-only comparisons between package metadata and Music artist/album/title/location/cloud status.
- Added slice offsets and per-lookup timeouts.

## [V5.1 / Inventory] — 2026-11-09

- Added read-only `.movpkg` package inventory with per-package file counts and logical sizes.
- Initial inventory: 1,552 packages, 60.86 GiB.
- Intermediate inventory: 803 packages, 32.54 GiB; 476 referenced by Music file tracks and 327 not in file-track references.
- Reaffirmed that unreferenced by *file tracks* is not proof of safe deletion.

## [V5 / HLS investigation] — November 2026

- Extended sync-error matching with HLS inspection and optional playlist workflows.
- Added review-oriented reports and cloud-status information.

## [V4 / Batch workflow] — November 2026

- Added numbered `iPod Repair - Batch NN` playlists, CSV match reports, persistent batch history, and progress output.
- Parsed Finder missing-file errors, deduplicated titles, and tracked previously processed titles.
- Known bug: leading-hyphen titles passed to `osascript` could be interpreted as options.

## [V1–V3 / Prototypes] — Earlier in the project

- Iterated from parsing Finder missing-song errors to faster Music lookups and optional playlists.
- V3 included experimental download-related code; intentionally omitted from the recommended release package.

## [Final storage cleanup] — 2026-11-09 (manual operation, not a tool release)

- After a final file-track reference audit returned zero, user explicitly authorized permanent deletion of the 327 leftover `.movpkg` packages.
- The deletion script verified the exact 327 package paths against the V6 report, then deleted those directories after typed confirmation.
- A first attempt failed safely due to `input()` receiving EOF from a Python heredoc; a TextEdit-created RTF script also failed; saving a plain-text `.py` file resolved execution.
- Deletion completed with zero packages remaining; free space rose from 62 GiB to 76 GiB (~14 GiB recovered).
- Playback/iPod sync after this final deletion was recommended but not confirmed in the available conversation.
