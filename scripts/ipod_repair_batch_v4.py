#!/usr/bin/env python3
"""iPod repair batch creator. Python 3.9+. No deletion or download actions.

Usage:
 python3 -u ~/Downloads/ipod_repair_batch_v4.py ~/Downloads/Errors.txt --batch 5
 Later: omit --batch to select the next batch from the local history file.
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
    return subprocess.run(['osascript', '-e', script, *args], text=True,
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
    p.add_argument('errors', type=Path, help='Latest Finder sync error text file')
    p.add_argument('--batch', type=int, help='Batch number (use 5 for your first run)')
    p.add_argument('--preview', action='store_true', help='Generate report without creating a playlist')
    p.add_argument('--timeout', type=int, default=45)
    args = p.parse_args()
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

if __name__ == '__main__':
    main()
