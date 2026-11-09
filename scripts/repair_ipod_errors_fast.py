#!/usr/bin/env python3
"""Match iPod missing-file errors against Music and optionally create a review playlist.
No deletions or download changes. Python 3.9+.
"""
import argparse
import csv
import re
import subprocess
from collections import Counter
from pathlib import Path

SCRIPT = r'''
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
                -- Do not silently swallow errors: Python logs them per title.
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

def parse_errors(path):
    raw = path.read_bytes()
    if raw.startswith((b'\xff\xfe', b'\xfe\xff')):
        text = raw.decode('utf-16')
    else:
        text = raw.decode('utf-8-sig')
    result = []
    for line in text.splitlines():
        if 'could not be found' not in line:
            continue
        m = re.search(r'[“"](.+?)[”"]\s+(?:was|were) not copied', line)
        if not m:
            m = re.search(r'including\s+[“"](.+?)[”"]', line)
        if m:
            result.append(m.group(1))
    return result

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('errors', type=Path)
    p.add_argument('--queue', action='store_true', help='Create a review playlist; does not delete or download anything')
    p.add_argument('--playlist', default='iPod Missing Files - Repair Queue')
    p.add_argument('--timeout', type=int, default=45, help='Seconds allowed per Music lookup')
    args = p.parse_args()
    names = parse_errors(args.errors)
    if not names:
        p.error('No missing-file error titles found')
    unique = list(dict.fromkeys(names))
    desktop = Path.home() / 'Desktop'
    desktop.mkdir(exist_ok=True)
    with (desktop / 'ipod_missing_titles.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Title', 'Error occurrences'])
        counts = Counter(names)
        writer.writerows((n, counts[n]) for n in unique)
    report = desktop / 'ipod_music_matches.csv'
    print(f'Parsed {len(names)} errors, {len(unique)} unique titles.', flush=True)
    print('Matching one title at a time. Press Ctrl+C to stop safely.', flush=True)
    with report.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Title', 'Status', 'Artist', 'Album', 'Persistent ID', 'Cloud status', 'Details'])
        for i, name in enumerate(unique, 1):
            print(f'[{i}/{len(unique)}] {name}', flush=True)
            try:
                proc = subprocess.run(['osascript', '-e', SCRIPT, name, args.playlist, 'yes' if args.queue else 'no'],
                                      capture_output=True, text=True, timeout=args.timeout)
                if proc.returncode:
                    writer.writerow([name, 'ERROR', '', '', '', '', proc.stderr.strip()])
                    print('  ERROR:', proc.stderr.strip()[:180], flush=True)
                elif not proc.stdout.strip():
                    writer.writerow([name, 'NOT_FOUND', '', '', '', '', ''])
                else:
                    for row in proc.stdout.strip().splitlines():
                        fields = (row.split('\t') + [''] * 4)[:4]
                        writer.writerow([name, 'MATCH', *fields, ''])
            except subprocess.TimeoutExpired:
                writer.writerow([name, 'TIMEOUT', '', '', '', '', f'Exceeded {args.timeout} seconds'])
                print('  TIMEOUT: Music did not respond in time', flush=True)
            f.flush()
    print(f'Done. Review {report}', flush=True)
    if args.queue:
        print(f'Playlist requested: {args.playlist}. Verify it in Music; inspect ERROR rows.', flush=True)
    else:
        print('Preview only; add --queue after reviewing the report.', flush=True)

if __name__ == '__main__':
    main()
