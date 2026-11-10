#!/usr/bin/env python3
"""iPod Music Repair V5. Python 3.9+. No deletion or download actions.

Usage:
 python3 -u ~/Downloads/ipod_music_repair_v5.py ~/Downloads/Errors.txt --preview
 python3 -u ~/Downloads/ipod_music_repair_v5.py ~/Downloads/Errors.txt
 python3 -u ~/Downloads/ipod_music_repair_v5.py --scan-hls
 python3 -u ~/Downloads/ipod_music_repair_v5.py --scan-hls --create-playlist
 Batch numbers continue from V4 history.
"""
import argparse
import csv
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path

APPLESCRIPT = r'''
on run argv
    set wantedName to item 1 of argv
    set queueName to item 2 of argv
    set addToQueue to (item 3 of argv is "yes")
    set recordRows to {}
    tell application "Music"
        set matchingTracks to (every track of library playlist 1 whose name is wantedName)
        if addToQueue then
            if not (exists user playlist queueName) then
                make new user playlist with properties {name:queueName}
            end if
            set targetPlaylist to user playlist queueName
        end if
        repeat with t in matchingTracks
            set artistText to ""
            set albumText to ""
            set trackID to ""
            set cloudText to ""
            try
                set artistText to artist of t as text
                set albumText to album of t as text
                set trackID to persistent ID of t as text
            end try
            try
                set cloudText to cloud status of t as text
            end try
            set end of recordRows to artistText & tab & albumText & tab & trackID & tab & cloudText
            if addToQueue then
                duplicate t to targetPlaylist
            end if
        end repeat
    end tell
    set AppleScript's text item delimiters to linefeed
    set outputText to recordRows as text
    set AppleScript's text item delimiters to ""
    return outputText
end run
'''

CHECK_PLAYLIST = r'''
on run argv
 tell application "Music"
  if exists user playlist (item 1 of argv) then return "EXISTS"
  return "MISSING"
 end tell
end run
'''


def run_script(script, *args, timeout=45):
    return subprocess.run(['osascript', '-e', script, '--', *args], text=True,
                          capture_output=True, timeout=timeout)


def parse_errors(path):
    raw = path.read_bytes()
    if raw.startswith((b'\xff\xfe', b'\xfe\xff')):
        text = raw.decode('utf-16')
    else:
        text = raw.decode('utf-8-sig')
    titles = []
    for line in text.splitlines():
        if 'could not be found' not in line:
            continue
        match = re.search(r'[“"](.+?)[”"]\s+(?:was|were) not copied', line)
        if not match:
            match = re.search(r'including\s+[“"](.+?)[”"]', line)
        if match:
            titles.append(match.group(1))
    return titles


def load_history(path):
    if not path.exists():
        return []
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('errors', type=Path, nargs='?', help='Latest Finder sync error text file')
    p.add_argument('--batch', type=int, help='Batch number (use 5 for your first run)')
    p.add_argument('--preview', action='store_true', help='Generate report without creating a playlist')
    p.add_argument('--timeout', type=int, default=45)
    p.add_argument('--scan-hls', action='store_true', help='Scan Music tracks for HLS-backed locations (read-only by default)')
    p.add_argument('--create-playlist', action='store_true', help='For --scan-hls, create a playlist of eligible HLS tracks')
    p.add_argument('--include-uploaded', action='store_true', help='Include Uploaded tracks in the HLS repair playlist')
    p.add_argument('--media-root', type=Path, default=Path.home() / 'Music/iTunes Music/Media.localized')
    p.add_argument('--scan-timeout', type=int, default=900)
    args = p.parse_args()
    if args.scan_hls:
        scan_hls(args, p)
        return
    if args.create_playlist or args.include_uploaded:
        p.error('--create-playlist and --include-uploaded require --scan-hls')
    if args.errors is None:
        p.error('Supply Errors.txt, or use --scan-hls for HLS inspection')
    if not args.errors.is_file():
        p.error('Error list not found: ' + str(args.errors))
    titles = parse_errors(args.errors)
    if not titles:
        p.error('No "could not be found" errors found in the input')
    unique = list(dict.fromkeys(titles))
    outdir = Path.home() / 'Desktop' / 'iPod Repair Batches'
    outdir.mkdir(parents=True, exist_ok=True)
    history_file = outdir / 'batch_history.csv'
    history = load_history(history_file)
    previous_batches = sorted({int(r['Batch']) for r in history if r.get('Batch', '').isdigit()})
    batch = args.batch if args.batch is not None else max(previous_batches + [4]) + 1
    if batch < 1:
        p.error('Batch must be positive')
    playlist = 'iPod Repair - Batch {:02d}'.format(batch)
    report = outdir / 'batch_{:02d}_matches.csv'.format(batch)
    if report.exists():
        p.error('Report already exists: {}. Choose another --batch number.'.format(report))
    try:
        existing = run_script(CHECK_PLAYLIST, playlist, timeout=args.timeout)
    except subprocess.TimeoutExpired:
        p.error('Music did not respond when checking playlist name')
    if existing.returncode:
        p.error('Could not check Music playlists: ' + existing.stderr.strip())
    if existing.stdout.strip() == 'EXISTS' and not args.preview:
        p.error('Playlist "{}" already exists. Rename it or choose another batch number.'.format(playlist))

    seen_titles = {r.get('Title', '') for r in history}
    previous_for_title = {}
    for r in history:
        previous_for_title.setdefault(r.get('Title', ''), set()).add(r.get('Batch', ''))
    print('Batch {} | {} errors | {} unique titles'.format(batch, len(titles), len(unique)), flush=True)
    print('Playlist: {}'.format(playlist), flush=True)
    print('Titles seen in saved V4 history: {} (older batches 1-4 are not in this history)'.format(
        sum(t in seen_titles for t in unique)), flush=True)
    print('Matching by TITLE only; review artists/recordings before changing downloads.', flush=True)
    counts = Counter(titles)
    columns = ['Batch', 'Title', 'Occurrences in error log', 'Previously in V4 batches',
               'Status', 'Artist', 'Album', 'Persistent ID', 'Cloud status', 'Details']
    rows = []
    for index, title in enumerate(unique, 1):
        print('[{}/{}] {}'.format(index, len(unique), title), flush=True)
        prior = ','.join(sorted(previous_for_title.get(title, []), key=lambda x: int(x) if x.isdigit() else 0))
        try:
            result = run_script(APPLESCRIPT, title, playlist,
                                'no' if args.preview else 'yes', timeout=args.timeout)
            if result.returncode:
                print('  ERROR: {}'.format(result.stderr.strip()[:200]), flush=True)
                matches = [['ERROR', '', '', '', '', result.stderr.strip()]]
            elif not result.stdout.strip():
                matches = [['NOT_FOUND', '', '', '', '', '']]
            else:
                matches = [['MATCH'] + (line.split('\t') + [''] * 4)[:4] + ['']
                           for line in result.stdout.strip().splitlines()]
        except subprocess.TimeoutExpired:
            print('  TIMEOUT', flush=True)
            matches = [['TIMEOUT', '', '', '', '', 'Music lookup exceeded {} seconds'.format(args.timeout)]]
        for fields in matches:
            rows.append([batch, title, counts[title], prior] + fields)
        # Save progress after every title; an interruption won't lose completed work.
        with report.open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)

    if not args.preview:
        timestamp = datetime.now().isoformat(timespec='seconds')
        new_history = history + [dict(Batch=str(batch), Title=title, Date=timestamp,
                                      Status=('MATCH' if any(r[1] == title and r[4] == 'MATCH' for r in rows) else 'CHECK_REPORT'))
                                 for title in unique]
        with history_file.open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['Batch', 'Title', 'Date', 'Status'])
            writer.writeheader()
            writer.writerows(new_history)
    statuses = Counter(r[4] for r in rows)
    print('\nFinished. Match rows: {}'.format(dict(statuses)), flush=True)
    print('Report: {}'.format(report), flush=True)
    if args.preview:
        print('Preview only: no playlist created.', flush=True)
    else:
        print('Playlist requested: {}. Verify in Music; check ERROR/TIMEOUT rows.'.format(playlist), flush=True)
        print('Next time, omit --batch to use the next number automatically.', flush=True)
    print('No downloads were removed and no library tracks were deleted.', flush=True)

HLS_SCAN_APPLESCRIPT = r'''
on run argv
    set doQueue to (item 1 of argv is "yes")
    set queueName to item 2 of argv
    set allowUploaded to (item 3 of argv is "yes")
    set rowList to {}
    set US to character id 31
    tell application "Music"
        set sourceTracks to every track of library playlist 1
        if doQueue then
            if not (exists user playlist queueName) then
                make new user playlist with properties {name:queueName}
            end if
            set targetPlaylist to user playlist queueName
        end if
        repeat with t in sourceTracks
            set titleText to ""
            set artistText to ""
            set albumText to ""
            set pidText to ""
            set cloudText to ""
            set kindText to ""
            set pathText to ""
            set artText to "UNKNOWN"
            try
                set titleText to name of t as text
                set artistText to artist of t as text
                set albumText to album of t as text
                set pidText to persistent ID of t as text
            end try
            try
                set cloudText to cloud status of t as text
            end try
            try
                set kindText to kind of t as text
            end try
            try
                set fileLocation to location of t
                if fileLocation is not missing value then
                    set pathText to POSIX path of fileLocation
                end if
            end try
            try
                if (count of artworks of t) > 0 then
                    set artText to "YES"
                else
                    set artText to "NO"
                end if
            end try
            ignoring case
                set isHLS to (pathText contains ".movpkg" or kindText contains "hls")
            end ignoring
            if isHLS then
                set queueStatus to "NOT_QUEUED"
                set eligible to (cloudText is "matched" or (allowUploaded and cloudText is "uploaded"))
                if doQueue and eligible then
                    try
                        duplicate t to targetPlaylist
                        set queueStatus to "QUEUED"
                    on error errText
                        set queueStatus to "ERROR: " & errText
                    end try
                else if not eligible then
                    set queueStatus to "REVIEW_CLOUD_STATUS"
                end if
                set end of rowList to titleText & US & artistText & US & albumText & US & pidText & US & cloudText & US & kindText & US & pathText & US & artText & US & queueStatus
            end if
        end repeat
    end tell
    set AppleScript's text item delimiters to linefeed
    set outputText to rowList as text
    set AppleScript's text item delimiters to ""
    return outputText
end run
'''


def scan_hls(args, parser):
    import os
    outdir = Path.home() / 'Desktop' / 'iPod Repair Batches'
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report = outdir / ('v5_hls_tracks_' + stamp + '.csv')
    packages = outdir / ('v5_hls_packages_' + stamp + '.csv')
    playlist = 'iPod Repair V5 - HLS AAC Queue ' + stamp
    if args.create_playlist and args.preview:
        parser.error('Use either --preview or --create-playlist, not both')
    if args.create_playlist:
        print('Creating a playlist for Matched HLS tracks only (Uploaded if --include-uploaded).', flush=True)
    else:
        print('Read-only scan. No playlists or downloads will be changed.', flush=True)
    print('Inspecting Music library tracks; this may take several minutes...', flush=True)
    try:
        result = run_script(HLS_SCAN_APPLESCRIPT,
                            'yes' if args.create_playlist else 'no', playlist,
                            'yes' if args.include_uploaded else 'no', timeout=args.scan_timeout)
    except subprocess.TimeoutExpired:
        parser.error('Music scan timed out. No report created; if playlist mode was used, check Music for a partial playlist.')
    if result.returncode:
        parser.error('Music scan failed: ' + result.stderr.strip()[:1200])
    columns = ['Title', 'Artist', 'Album', 'Persistent ID', 'Cloud status', 'Kind', 'Location', 'Artwork in Music', 'Queue status']
    rows = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        fields = line.split(chr(31))
        if len(fields) == len(columns):
            rows.append(fields)
        else:
            print('Warning: skipping malformed scan row', flush=True)
    with report.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(columns)
        w.writerows(rows)
    print('Music tracks with HLS locations/kinds: {}'.format(len(rows)), flush=True)
    print('Track report: {}'.format(report), flush=True)
    if args.create_playlist:
        print('Playlist: {} (verify entries in Music)'.format(playlist), flush=True)
        print('Queue statuses: {}'.format(dict(Counter(r[-1] for r in rows))), flush=True)
    # Supplementary read-only filesystem inventory. HLS assets need not map 1:1 to Music tracks.
    root = args.media_root.expanduser()
    inventory = []
    if root.is_dir():
        for directory, subdirs, files in os.walk(root):
            for d in list(subdirs):
                if d.lower().endswith('.movpkg'):
                    full = Path(directory) / d
                    inventory.append([str(full), 'movpkg directory'])
                    subdirs.remove(d)
            for name in files:
                if name.lower().endswith(('.m3u8', '.frag', '.initfrag')):
                    # Count these in summary, not individually in a huge CSV.
                    pass
        with packages.open('w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f)
            w.writerow(['Path', 'Type'])
            w.writerows(inventory)
        print('HLS package directory inventory: {} ({} packages)'.format(packages, len(inventory)), flush=True)
    print('Note: Music may not expose a file location for every HLS download. An empty report does not prove there are no HLS assets.', flush=True)
    print('No downloads or tracks were removed.', flush=True)


if __name__ == '__main__':
    main()
