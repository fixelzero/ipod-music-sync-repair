#!/usr/bin/env python3
"""Read-only library-wide match of leftover HLS packages; opt-in playlist creation.
Python 3.9+. Never deletes media or triggers downloads.
"""
import argparse, csv, re, subprocess, sys, unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path.home() / 'Desktop/iPod Repair Batches'
REPORT = ROOT / 'hls_leftovers_final_scan.csv'
OUT = ROOT / 'hls_leftovers_v6_matches.csv'
SEP = chr(30)
FIELDS = ['Package path','Artist from path','Album from path','Title from path','V6 status','Music title','Music artist','Music album','Persistent ID','Candidate count','Notes']

def norm(s):
    s = unicodedata.normalize('NFKC', s or '').casefold()
    s = s.replace('’', "'").replace('‘', "'")
    return re.sub(r'[^\w]+', '', s)

def applescript(code, args=(), timeout=240):
    p = subprocess.run(['osascript','-e',code,*args],capture_output=True,text=True,timeout=timeout)
    if p.returncode: raise RuntimeError('Music AppleScript error: '+p.stderr.strip()[:1200])
    return p.stdout

EXPORT = r'''
on run argv
    set fieldName to item 1 of argv
    tell application "Music"
        set lib to library playlist 1
        if fieldName is "name" then
            set vals to name of every track of lib
        else if fieldName is "artist" then
            set vals to artist of every track of lib
        else if fieldName is "album" then
            set vals to album of every track of lib
        else if fieldName is "pid" then
            set vals to persistent ID of every track of lib
        else
            error "Unknown field"
        end if
    end tell
    set outputItems to {}
    repeat with v in vals
        try
            set s to v as text
            set s to my replaceText(s, ASCII character 30, " ")
            set s to my replaceText(s, return, " ")
            set s to my replaceText(s, linefeed, " ")
        on error
            set s to ""
        end try
        set end of outputItems to s
    end repeat
    set AppleScript's text item delimiters to ASCII character 30
    set joined to outputItems as text
    set AppleScript's text item delimiters to ""
    return joined
end run
on replaceText(s, oldText, newText)
    set AppleScript's text item delimiters to oldText
    set parts to text items of s
    set AppleScript's text item delimiters to newText
    set s to parts as text
    set AppleScript's text item delimiters to ""
    return s
end replaceText
'''

CREATE = r'''
on run argv
    set playlistName to item 1 of argv
    set ids to items 2 thru -1 of argv
    tell application "Music"
        if (count of (user playlists whose name is playlistName)) > 0 then error "Playlist already exists: " & playlistName
        set dest to make new user playlist with properties {name:playlistName}
        set added to 0
        repeat with pid in ids
            set hits to every track of library playlist 1 whose persistent ID is (pid as text)
            if (count of hits) is not 1 then error "Expected exactly one track for persistent ID " & pid
            duplicate (item 1 of hits) to dest
            set added to added + 1
        end repeat
        return "Created " & playlistName & ": " & added & " tracks"
    end tell
end run
'''

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--create-playlists',action='store_true',help='Opt in to playlist creation AFTER inspecting the report')
    ap.add_argument('--report-only',action='store_true',help='Never create playlists (default)')
    args=ap.parse_args()
    if not REPORT.is_file(): ap.error('Missing '+str(REPORT))
    with REPORT.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    if len(rows)!=327: ap.error('Expected 327 scan rows; found '+str(len(rows)))
    if not args.create_playlists and OUT.exists():
        ap.error('Report already exists; move/rename it before rescanning: '+str(OUT))
    if args.create_playlists:
        if not OUT.is_file(): ap.error('First run without --create-playlists and review report')
        with OUT.open(encoding='utf-8-sig',newline='') as f: matched=list(csv.DictReader(f))
        ids=[]; seen=set()
        for r in matched:
            if r['V6 status']!='EXACT_TITLE_ARTIST_ALBUM': continue
            pid=r['Persistent ID'].strip().upper()
            if not re.fullmatch(r'[0-9A-F]{16}',pid) or pid in seen: continue
            ids.append(pid);seen.add(pid)
        # Existing AAC entries from prior scan are excluded, plus any other confirmed AAC IDs.
        already_aac={r['Persistent ID'].strip().upper() for r in rows if r['Status']=='POSSIBLY_CONVERTED_AAC' and r['Music location'].lower().endswith('.m4a')}
        ids=[pid for pid in ids if pid not in already_aac]
        if not ids:
            print('No eligible exact matches to queue. Nothing changed.');return
        print('Creating playlists for',len(ids),'exact title+artist+album matches (excluding known AAC).')
        for i in range(0,len(ids),75):
            name='iPod HLS Leftovers - Final Repair %02d'%(i//75+1)
            print(applescript(CREATE,[name,*ids[i:i+75]],timeout=900).strip(),flush=True)
        print('Review playlists in Music before Remove Download -> Download. Original files untouched.')
        return
    print('Reading Music library metadata (4 bulk queries). This may take a few minutes...',flush=True)
    fields={}
    for field in ('name','artist','album','pid'):
        raw=applescript(EXPORT,[field],timeout=600).rstrip('\n')
        fields[field]=raw.split(SEP)
        print(field,len(fields[field]),flush=True)
    lengths={k:len(v) for k,v in fields.items()}
    if len(set(lengths.values()))!=1 or not 20000<=len(fields['pid'])<=100000:
        raise RuntimeError('Library field counts inconsistent: '+str(lengths)+'; no report written')
    tracks=[]; by_ta=defaultdict(list)
    for name,artist,album,pid in zip(fields['name'],fields['artist'],fields['album'],fields['pid']):
        if not re.fullmatch('[0-9A-Fa-f]{16}',pid): continue
        t={'name':name,'artist':artist,'album':album,'pid':pid.upper()}
        tracks.append(t);by_ta[(norm(name),norm(artist))].append(t)
    output=[]
    for r in rows:
        title=r['Title from path'];artist=r['Artist from path'];album=r['Album from path']
        candidates=by_ta.get((norm(title),norm(artist)),[])
        exact=[t for t in candidates if norm(t['album'])==norm(album)]
        if len(exact)==1: status='EXACT_TITLE_ARTIST_ALBUM'; choice=exact[0]; note='One exact normalized title/artist/album match'
        elif len(exact)>1: status='AMBIGUOUS_EXACT';choice=None;note='Multiple same title/artist/album entries'
        elif len(candidates)==1: status='TITLE_ARTIST_ONLY_REVIEW';choice=candidates[0];note='Unique title/artist, album differs; manual review'
        elif len(candidates)>1: status='AMBIGUOUS_VERSIONS';choice=None;note='Multiple title/artist matches across albums'
        else: status='NOT_FOUND';choice=None;note='No normalized title/artist match among Music tracks'
        output.append({'Package path':r['Package path'],'Artist from path':artist,'Album from path':album,'Title from path':title,
                       'V6 status':status,'Music title':choice['name'] if choice else '',
                       'Music artist':choice['artist'] if choice else '', 'Music album':choice['album'] if choice else '',
                       'Persistent ID':choice['pid'] if choice else '', 'Candidate count':len(candidates),'Notes':note})
    with OUT.open('x',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(output)
    print('\nResults:',dict(Counter(r['V6 status'] for r in output)))
    print('Report:',OUT)
    print('READ ONLY. Inspect the report before running --create-playlists.')
    print('WARNING: Playlist creation does not remove old orphaned .movpkg files.')

if __name__=='__main__':
    try: main()
    except (OSError,RuntimeError,subprocess.TimeoutExpired) as e:
        print('STOP:',e,file=sys.stderr);sys.exit(1)
