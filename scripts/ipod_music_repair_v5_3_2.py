#!/usr/bin/env python3
"""iPod Music Repair V5.3.2: bounded HLS classification and opt-in playlist creation.

Python 3.9+. Never deletes media or changes download settings. The scan is read-only.
Playlist creation requires a separate explicit --create-playlists command.
"""
import argparse
import csv
import re
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

SEP = '\x1f'
FIELDS = ['Package path', 'Artist from path', 'Album from path', 'Title from path',
          'Status', 'Music title', 'Music artist', 'Music album', 'Persistent ID',
          'Cloud status', 'Music location', 'Notes']

LOOKUP = r'''
on run argv
    set wantedTitle to text 2 thru -1 of item 1 of argv
    set resultRows to {}
    set sep to character id 31
    tell application "Music"
        set candidates to (every track of library playlist 1 whose name is wantedTitle)
        repeat with t in candidates
            set tName to ""
            set tArtist to ""
            set tAlbum to ""
            set tPid to ""
            set tCloud to ""
            set tLocation to ""
            try
                set tName to name of t as text
                set tArtist to artist of t as text
                set tAlbum to album of t as text
                set tPid to persistent ID of t as text
            end try
            try
                set tCloud to cloud status of t as text
            end try
            try
                set tFile to location of t
                if tFile is not missing value then set tLocation to POSIX path of tFile
            end try
            set end of resultRows to tName & sep & tArtist & sep & tAlbum & sep & tPid & sep & tCloud & sep & tLocation
        end repeat
    end tell
    set AppleScript's text item delimiters to linefeed
    set resultText to resultRows as text
    set AppleScript's text item delimiters to ""
    return resultText
end run
'''

# Only one playlist is touched per invocation, with the explicit --create-playlists flag.
# Every queued track is revalidated by persistent ID, cloud status, and on-disk HLS location.
QUEUE = r'''
on run argv
    set wantedPid to text 2 thru -1 of item 1 of argv
    set wantedPath to text 2 thru -1 of item 2 of argv
    set playlistName to text 2 thru -1 of item 3 of argv
    tell application "Music"
        set candidates to (every track of library playlist 1 whose persistent ID is wantedPid)
        if (count of candidates) is not 1 then return "SKIP: persistent ID not unique or missing"
        set t to item 1 of candidates
        try
            set currentCloud to cloud status of t as text
            if currentCloud is not "matched" then return "SKIP: cloud status changed to " & currentCloud
            set f to location of t
            if f is missing value then return "SKIP: track has no file location"
            set currentPath to POSIX path of f
            if currentPath is not wantedPath and currentPath is not (wantedPath & "/") then return "SKIP: location changed"
            if currentPath does not contain ".movpkg" then return "SKIP: no longer HLS"
            if not (exists user playlist playlistName) then
                make new user playlist with properties {name:playlistName}
            end if
            set targetPlaylist to user playlist playlistName
            -- Music may reject a bulk persistent-ID query for playlist tracks.
            -- Read each track separately; empty playlists work as well.
            set existingTracks to every track of targetPlaylist
            repeat with existingTrack in existingTracks
                try
                    if (persistent ID of existingTrack as text) is wantedPid then return "ALREADY_QUEUED"
                end try
            end repeat
            duplicate t to targetPlaylist
            return "QUEUED"
        on error errText
            return "ERROR: " & errText
        end try
    end tell
end run
'''


def normalized(value):
    value = unicodedata.normalize('NFKC', value or '').casefold()
    return re.sub(r'[^\w]+', '', value)


def clean_path(path):
    return str(path).rstrip('/')


def title_variants(stem):
    title = re.sub(r'^\d+(?:-\d+)?\s+', '', stem).strip()
    variants = [title]
    # macOS Music replaces some filename-forbidden punctuation with underscores.
    if '_' in title:
        for replacement in ('?', ':', '/', '*', '"', ''):
            candidate = title.replace('_', replacement)
            if candidate not in variants:
                variants.append(candidate)
    return title, variants


def run_osascript(script, args, timeout):
    # Prefix each user-derived arg to avoid osascript interpreting leading '-' as an option.
    command = ['osascript', '-e', script] + ['X' + str(arg) for arg in args]
    result = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr.strip()[:400] or 'osascript exited {}'.format(result.returncode))
    return result.stdout.strip()


def lookup(title, variants, cache, timeout):
    collected = {}
    errors = []
    for variant in variants:
        if variant not in cache:
            try:
                output = run_osascript(LOOKUP, [variant], timeout)
                matches = []
                for line in output.splitlines():
                    cells = (line.split(SEP) + [''] * 6)[:6]
                    if cells[3]:
                        matches.append(cells)
                cache[variant] = matches
            except (subprocess.TimeoutExpired, RuntimeError) as exc:
                cache[variant] = exc
        result = cache[variant]
        if isinstance(result, Exception):
            errors.append('{}: {}'.format(variant, result))
        else:
            for match in result:
                collected[match[3]] = match
        # Exact title results are usually sufficient; alternatives only needed if no candidate.
        if collected:
            break
    return list(collected.values()), errors


def scan(args):
    with args.inventory.open(encoding='utf-8-sig', newline='') as handle:
        entries = list(csv.DictReader(handle))
    if not entries or 'Package path' not in entries[0]:
        raise ValueError('Not a V5.1 HLS inventory CSV')
    if args.start >= len(entries):
        raise ValueError('--start is beyond the end of the inventory')
    selected = entries[args.start:args.start + args.limit]
    output = args.output or args.inventory.with_name('hls_v531_start{}_count{}.csv'.format(args.start, len(selected)))
    if output.exists() and not args.overwrite:
        raise ValueError('Report already exists: {} (use --overwrite to replace it)'.format(output))
    cache = {}
    counts = Counter()
    with output.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for index, entry in enumerate(selected, 1):
            path = Path(entry['Package path'])
            title, variants = title_variants(path.stem)
            artist, album = path.parent.parent.name, path.parent.name
            row = dict.fromkeys(FIELDS, '')
            row.update({'Package path': str(path), 'Artist from path': artist,
                        'Album from path': album, 'Title from path': title})
            print('[{}/{}] {} / {} / {}'.format(index, len(selected), artist, album, title), flush=True)
            matches, errors = lookup(title, variants, cache, args.timeout)
            # Match artist, album, and exact current location. The filename title may differ.
            candidates = [m for m in matches if normalized(m[1]) == normalized(artist)
                          and normalized(m[2]) == normalized(album)]
            exact = [m for m in candidates if clean_path(m[5]) == clean_path(path)]
            if len(exact) == 1:
                m = exact[0]
                row.update(dict(zip(FIELDS[5:11], m)))
                cloud = m[4].casefold().strip()
                if cloud == 'matched':
                    row['Status'] = 'VERIFIED_MATCHED_HLS'
                    row['Notes'] = 'Exact Music location and matched cloud status; eligible for opt-in playlist only'
                elif cloud == 'uploaded':
                    row['Status'] = 'UPLOADED_REVIEW'
                    row['Notes'] = 'Do not automatically replace uploaded files'
                else:
                    row['Status'] = 'OTHER_CLOUD_REVIEW'
                    row['Notes'] = 'Do not automatically replace subscription or unknown tracks'
            elif len(exact) > 1:
                row['Status'] = 'AMBIGUOUS'
                row['Notes'] = '{} tracks share this location'.format(len(exact))
            elif candidates:
                # A candidate may be an AAC file now, but a package's continued presence
                # does not establish that the package is unused or safe to delete.
                aac = [m for m in candidates if m[5] and
                       Path(clean_path(m[5])).suffix.lower() in ('.m4a', '.mp3', '.aac', '.alac')]
                if len(candidates) == 1 and len(aac) == 1:
                    m = aac[0]
                    row.update(dict(zip(FIELDS[5:11], m)))
                    row['Status'] = 'POSSIBLY_CONVERTED_AAC'
                    row['Notes'] = 'Music currently points to a conventional audio file; HLS package remains unverified, NOT safe to delete'
                else:
                    row['Status'] = 'LOCATION_CHANGED_OR_MISMATCH'
                    row['Notes'] = '{} artist/album candidates, none at package location; inspect manually'.format(len(candidates))
            elif errors and not matches:
                row['Status'] = 'LOOKUP_ERROR'
                row['Notes'] = '; '.join(errors)[:500]
            else:
                row['Status'] = 'NO_VERIFIED_MATCH'
                row['Notes'] = 'No same-title artist/album/location match; review manually; package NOT safe to delete'
            writer.writerow(row)
            handle.flush()
            counts[row['Status']] += 1
    print('\nReport:', output)
    print('Status counts:', ', '.join('{}={}'.format(k, v) for k, v in sorted(counts.items())))
    print('Next offset:', args.start + len(selected), 'of', len(entries))
    print('Read-only: no playlists, downloads, or media changed.')
    print('WARNING: Unmatched/converted packages are NOT proven unused or safe to delete.')


def queue(args):
    with args.report.open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    if not rows or not set(FIELDS).issubset(rows[0]):
        raise ValueError('Not a V5.3 report')
    selected = [row for row in rows if row['Status'] == 'VERIFIED_MATCHED_HLS']
    if not selected:
        print('No VERIFIED_MATCHED_HLS tracks to queue.')
        return
    if len(selected) > args.batch_size:
        raise ValueError('Report has {} eligible tracks, exceeds --batch-size {}. Use a smaller scan batch.'.format(len(selected), args.batch_size))
    if not re.fullmatch(r'[A-Za-z0-9 _-]{1,90}', args.playlist_name):
        raise ValueError('Playlist name must use letters, numbers, spaces, underscores, hyphens')
    output = args.report.with_name(args.report.stem + '_queue_results.csv')
    if output.exists() and not args.overwrite:
        raise ValueError('Queue results already exist; use --overwrite only after reviewing existing playlist')
    print('Playlist:', args.playlist_name)
    print('Eligible rows:', len(selected))
    print('Only this playlist may be created/updated. Downloads and files are untouched.')
    print('You explicitly requested playlist creation with --create-playlists.\n')
    with output.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['Persistent ID', 'Title', 'Queue result'])
        for i, row in enumerate(selected, 1):
            pid = row['Persistent ID']
            if not re.fullmatch(r'[0-9A-Fa-f]{16}', pid):
                result = 'SKIP: invalid persistent ID'
            else:
                try:
                    result = run_osascript(QUEUE, [pid, row['Package path'], args.playlist_name], args.timeout)
                except (subprocess.TimeoutExpired, RuntimeError) as exc:
                    result = 'ERROR: {}'.format(exc)
            print('[{}/{}] {}: {}'.format(i, len(selected), row['Title from path'], result), flush=True)
            writer.writerow([pid, row['Title from path'], result])
            handle.flush()
    print('\nQueue results:', output)
    print('No downloads were removed or initiated.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    s = sub.add_parser('scan', help='Read-only match a slice of the V5.1 inventory')
    s.add_argument('inventory', type=Path)
    s.add_argument('--start', type=int, default=0)
    s.add_argument('--limit', type=int, default=50)
    s.add_argument('--timeout', type=int, default=40)
    s.add_argument('--output', type=Path)
    s.add_argument('--overwrite', action='store_true')
    q = sub.add_parser('queue', help='Create playlist from verified V5.3.2 report')
    q.add_argument('report', type=Path)
    q.add_argument('--create-playlists', action='store_true', required=True,
                   help='Explicitly authorize creating/updating one Music playlist')
    q.add_argument('--playlist-name', required=True)
    q.add_argument('--batch-size', type=int, default=50)
    q.add_argument('--timeout', type=int, default=40)
    q.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    try:
        if args.mode == 'scan':
            if args.start < 0 or args.limit < 1 or args.timeout < 1:
                parser.error('start >= 0, limit > 0, timeout > 0 required')
            if not args.inventory.is_file():
                parser.error('Inventory not found')
            scan(args)
        else:
            if args.batch_size < 1 or args.timeout < 1:
                parser.error('batch-size and timeout must be positive')
            if not args.report.is_file():
                parser.error('Report not found')
            queue(args)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))

if __name__ == '__main__':
    main()
