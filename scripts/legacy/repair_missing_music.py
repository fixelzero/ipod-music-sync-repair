#!/usr/bin/env python3
"""Find missing local Music tracks, report them, and put them in a repair playlist.
Does not delete library entries or source files.
"""
import argparse
import csv
import subprocess
import sys
from pathlib import Path

SCRIPT = r'''
on run argv
    set playlistName to item 1 of argv
    set shouldCreate to (item 2 of argv is "yes")
    set outLines to {}
    set AppleScript's text item delimiters to tab
    tell application "Music"
        set libraryTracks to every file track of library playlist 1
        if shouldCreate then
            if not (exists user playlist playlistName) then
                make new user playlist with properties {name:playlistName}
            end if
            set targetPlaylist to user playlist playlistName
        end if
        repeat with tr in libraryTracks
            try
                set loc to location of tr
                set isMissing to false
                if loc is missing value then
                    set isMissing to true
                else
                    try
                        set locAlias to loc as alias
                    on error
                        set isMissing to true
                    end try
                end if
                if isMissing then
                    set tid to persistent ID of tr
                    set tname to name of tr
                    set tartist to artist of tr
                    set talbum to album of tr
                    set end of outLines to tid & tab & tname & tab & tartist & tab & talbum
                    if shouldCreate then
                        try
                            duplicate tr to targetPlaylist
                        end try
                    end if
                end if
            end try
        end repeat
    end tell
    set AppleScript's text item delimiters to linefeed
    return outLines as text
end run
'''

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Create a playlist of missing tracks (no deletion)')
    parser.add_argument('--playlist', default='Missing Files - Repair Queue')
    parser.add_argument('--report', type=Path, default=Path.home() / 'Desktop' / 'missing_music_tracks.csv')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        sys.exit('This script requires macOS with the Music app.')
    print('Scanning Apple Music library; large libraries may take several minutes...', flush=True)
    p = subprocess.run(['osascript', '-', args.playlist, 'yes' if args.apply else 'no'],
                       input=SCRIPT, text=True, capture_output=True)
    if p.returncode:
        sys.exit('Music automation failed:\n' + p.stderr)
    rows = []
    for line in p.stdout.splitlines():
        fields = line.split('\t')
        if len(fields) == 4:
            rows.append(fields)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Persistent ID', 'Title', 'Artist', 'Album'])
        writer.writerows(rows)
    print(f'Found {len(rows)} tracks without an accessible local file.')
    print(f'Report: {args.report}')
    if args.apply:
        print(f'Playlist: {args.playlist}')
        print('In Music, open that playlist, select all, then choose File > Library > Download (if available).')
        print('Check cloud status for tracks that cannot be downloaded; do not delete their library entries.')
    else:
        print('Preview only. Run with --apply to create the repair playlist.')

if __name__ == '__main__':
    main()
