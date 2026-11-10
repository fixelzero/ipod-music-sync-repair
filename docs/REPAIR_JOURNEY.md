# Repair journey — case study

## 1. Original problem

A modified iPod Video 5.5 was syncing through Finder on macOS. Finder reported tracks that could not be copied because the files “could not be found.” The initial saved report contained 101 errors for 98 unique song titles. Different versions of a title and Unicode punctuation made matching nontrivial.

## 2. Fix the device connection separately

Earlier troubleshooting involved FAT32 disk errors and a Finder sync activation timeout/error 60. Restarting `AMPDeviceDiscoveryAgent`, `AMPDevicesAgent`, and Finder restored the Finder sync path in the documented test. An online `iTunesLock` suggestion was considered, but that file was **not present on the tested iPod**; do not credit its deletion as the fix.

## 3. Build error-driven review playlists

Early scripts parsed `Errors.txt`; V4 introduced numbered playlists, batch CSVs and persistent history. The initial errors were not the entire universe of failures: later Finder syncs exposed further songs. The roughly 99–100 errors seen per report were observational, not a verified Finder limit. Batch 5 revealed a bug with titles beginning with hyphens.

## 4. Discover the HLS download format problem

The Music library contained `.movpkg` HLS packages that could not be treated as normal iPod-compatible `.m4a` files. Music download quality was set to High Quality AAC 256 kbps; verified affected tracks were repaired manually with **Remove Download → Download**, never wholesale Delete from Library. This method cannot remove Apple Music subscription DRM.

## 5. Inventory and classify

V5.1 found 1,552 packages (60.86 GiB). Later scans found 803 (32.54 GiB). A read-only file-track audit classified 476 as referenced and 327 as not referenced by file tracks. Five repair playlists (100, 100, 100, 100, 76) were used for the 476; the file-track reference count subsequently reached zero.

## 6. Handle the 327 leftovers

V5.3.2 found 272 with no verified match, 37 potentially already converted to AAC, and 18 location mismatches. V6 expanded search to all 24,321 Music track objects: 49 exact matches, 26 title/artist-only, 22 ambiguous versions, 5 ambiguous exact, and 225 not found. Final Repair 01 contained 22 tracks and was repaired. Review 02 contained 25 unique tracks from 26 package rows; the user confirmed they were MP3/M4A. Review 03 contained 24 unique candidate tracks covering 27 ambiguous package rows and was reviewed.

## 7. Storage recovery

The package count remained 327 even after playlist review/redownload. The final file-track location audit returned zero `.movpkg` references, but this did **not** rule out references by other Music track types. The user opted to delete all 327, after the script confirmed an exact path-set match. The final output reported zero packages, and `df -h /` showed available space rising from 62 GiB to 76 GiB. At the start of broader storage troubleshooting, free space had been approximately 7 GiB; not all gains were attributable to this final deletion.

## 8. What is proven, and what is not

**Proven by reported commands:** playlist creation, observed Music metadata counts, file-track reference count, `.movpkg` package counts, final deletion, and measured free-space increase.

**Not proven:** that all 24,321 Music tracks are playable, that every iPod sync issue is fixed, that none of the other 14,077 track objects needed the deleted packages, or that all 225 unmatched packages were genuinely orphaned before deletion. Final playback and sync testing remained recommended.
