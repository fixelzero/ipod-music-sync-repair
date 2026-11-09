# Project log (through Batch 6)

1. **Initial issue:** Finder/iPod sync reported songs not copied because the source files could not be found.
2. **First error export:** 101 error entries, 98 unique song titles; multilingual and classical titles included.
3. **Initial prototype:** Parsed error file, but Apple Music automation appeared to hang during library matching.
4. **Diagnosis:** Terminal's basic AppleScript command (`tell application "Music" to get name`) returned `Music`, so basic automation was available. The initial matching approach was too slow in practice.
5. **Fast matcher:** Per-title queries with visible progress completed and produced a review playlist. Candidate matching returned multiple recordings for some titles.
6. **Manual repair:** Removing stale downloads and downloading again resolved some failures; new Finder error exports exposed additional songs.
7. **Batch workflow:** User renamed prior playlists and repeated sync → export → playlist → manual repair. Error lists appeared to contain around 99–100 titles per run; this is observational.
8. **V3 proposed:** Persistent-ID/local-file inspection, but not used in this workflow.
9. **V4 deployed:** Numbered playlist creation and CSV batch history, starting at Batch 5.
10. **Batch 5:** 100 unique titles processed; 134 `MATCH` rows and 3 `ERROR` rows. Three errors were for titles starting with hyphens (`-MC- End`, `-MC-`, `-VTR-`) because `osascript` treated them as options.
11. **Current status:** Batch 5 completed; Batch 6 underway. Total final repair rate and total number of affected tracks are not yet known.

## Outcome so far

The automation reliably produces review playlists and reports for many failed sync titles. Some music has been recovered through manual re-download. Full-library recovery is **not yet established**.
