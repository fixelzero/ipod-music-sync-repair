#!/usr/bin/env python3
"""V5.2: review HLS inventory against Music in bounded, resumable batches.
Python 3.9+. Read-only: NEVER changes Music playlists, downloads or audio.
"""
import argparse
import csv
import re
import subprocess
from pathlib import Path

SCRIPT = r'''
on run argv
    set targetTitle to text 2 thru -1 of item 1 of argv
    set rowList to {}
    set sep to character id 31
    tell application "Music"
        set matches to (every track of library playlist 1 whose name is targetTitle)
        repeat with t in matches
            set a to ""
            set b to ""
            set pid to ""
            set cloud to ""
            set loc to ""
            try
                set a to artist of t as text
                set b to album of t as text
                set pid to persistent ID of t as text
            end try
            try
                set cloud to cloud status of t as text
            end try
            try
                set f to location of t
                if f is not missing value then set loc to POSIX path of f
            end try
            set end of rowList to a & sep & b & sep & pid & sep & cloud & sep & loc
        end repeat
    end tell
    set AppleScript's text item delimiters to linefeed
    set resultText to rowList as text
    set AppleScript's text item delimiters to ""
    return resultText
end run
'''
FIELDS = ['Package path','Artist from path','Album from path','Title from path',
          'Status','Music artist','Music album','Persistent ID','Cloud status','Music location','Notes']

def norm(s):
    return re.sub(r'[^\w]+', '', s.casefold())

def title_from_stem(stem):
    return re.sub(r'^\d+-\d+\s+', '', stem).strip()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('inventory', type=Path, help='V5.1 hls_inventory_*.csv')
    p.add_argument('--limit', type=int, default=25, help='Packages to process this run (default 25)')
    p.add_argument('--start', type=int, default=0, help='Zero-based package offset for next run')
    p.add_argument('--timeout', type=int, default=35, help='Timeout per title lookup')
    p.add_argument('--output', type=Path, default=None)
    args = p.parse_args()
    if args.limit < 1 or args.start < 0:
        p.error('--limit must be positive and --start nonnegative')
    if not args.inventory.is_file():
        p.error('Inventory CSV not found')
    with args.inventory.open(encoding='utf-8-sig', newline='') as f:
        entries = list(csv.DictReader(f))
    if not entries or 'Package path' not in entries[0]:
        p.error('Not a V5.1 inventory CSV')
    subset = entries[args.start:args.start+args.limit]
    if not subset:
        p.error('No packages at this offset')
    output = args.output or args.inventory.with_name('hls_music_review_start{}_count{}.csv'.format(args.start,len(subset)))
    print('Read-only Music matching: packages {} through {} of {}'.format(args.start+1,args.start+len(subset),len(entries)),flush=True)
    cache = {}
    with output.open('w',newline='',encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(FIELDS)
        for n, item in enumerate(subset,1):
            path = Path(item['Package path'])
            title = title_from_stem(path.stem)
            artist = path.parent.parent.name
            album = path.parent.name
            # Some nested layouts vary: always review path-derived metadata.
            print('[{}/{}] {} / {} / {}'.format(n,len(subset),artist,album,title),flush=True)
            if title not in cache:
                try:
                    # Prefix title with X to prevent leading hyphens being treated as options.
                    proc = subprocess.run(['osascript','-e',SCRIPT,'X'+title],capture_output=True,text=True,timeout=args.timeout)
                    if proc.returncode:
                        cache[title] = ('ERROR',proc.stderr.strip()[:300])
                    else:
                        matches=[]
                        for line in proc.stdout.splitlines():
                            fields=(line.split('\x1f')+['']*5)[:5]
                            matches.append(fields)
                        cache[title]=('OK',matches)
                except subprocess.TimeoutExpired:
                    cache[title]=('TIMEOUT','Music did not answer within {} seconds'.format(args.timeout))
            status, result = cache[title]
            base=[str(path),artist,album,title]
            if status != 'OK':
                writer.writerow(base+[status,'','','','','',result])
            else:
                exact=[m for m in result if norm(m[0])==norm(artist) and norm(m[1])==norm(album)]
                if not exact:
                    writer.writerow(base+['NO_EXACT_MATCH','','','','','',
                                          '{} same-title candidate(s); check album/artist manually'.format(len(result))])
                elif len(exact)>1:
                    writer.writerow(base+['AMBIGUOUS','','','','','',
                                          '{} matching Music entries; no automatic decision'.format(len(exact))])
                else:
                    m=exact[0]
                    cloud=m[3].casefold()
                    # Report only. Never create playlist or change downloads.
                    label='MATCHED_REVIEW' if cloud=='matched' else ('UPLOADED_REVIEW' if cloud=='uploaded' else 'OTHER_CLOUD_REVIEW')
                    notes='Cloud status alone does not prove portability or permission to remove download'
                    writer.writerow(base+[label]+m+[notes])
            f.flush()
    print('\nReport:',output)
    print('Next offset:',args.start+len(subset))
    print('Read-only: no playlists, downloads, or media changed.')

if __name__=='__main__':
    main()
