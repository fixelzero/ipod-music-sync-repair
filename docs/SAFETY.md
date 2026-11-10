# Safety, privacy, and scope

- Back up the Music library database, original audio, playlists and other personal data before changing downloads or deleting files.
- The mainline scripts in this repository do not remove downloads, delete library tracks, or delete `.movpkg` packages. Playlist creation is opt-in where supported.
- Never treat `NOT_IN_FILE_TRACK_REFERENCES` as proof that a package is unreferenced by all Music track types.
- Verify media paths are within the intended media root before any manual cleanup. Prefer reversible moves or verified backups when possible.
- Never publish your real `Errors.txt`, music inventory CSV, Apple Music persistent IDs, device identifiers, external drive names, or personal paths.
- Subscription downloads may be DRM protected and cannot be made iPod-compatible by merely changing download quality.
- The final 327-package deletion was an explicit, one-off user choice; no general deletion utility is distributed here.
- These scripts use AppleScript automation; review and test them with small batches, and stop if Music behaves unexpectedly.
