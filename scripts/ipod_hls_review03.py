#!/usr/bin/env python3
"""Create a best-effort Music review playlist for 27 ambiguous HLS package matches.
Never deletes, removes downloads, or modifies media. Requires V6 report.
"""
import csv, importlib.util, re, sys
from collections import defaultdict
from pathlib import Path

base = Path.home() / 'Desktop/iPod Repair Batches'
report = base / 'hls_leftovers_v6_matches.csv'
v6path = Path.home() / 'Downloads/ipod_hls_v6_library_match.py'
if not report.is_file() or not v6path.is_file():
    sys.exit('STOP: Missing V6 report or original V6 script.')
spec = importlib.util.spec_from_file_location('ipod_v6', v6path)
v6 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v6)
with report.open(encoding='utf-8-sig',newline='') as f:
    rows=list(csv.DictReader(f))
statuses={'AMBIGUOUS_VERSIONS','AMBIGUOUS_EXACT'}
target=[r for r in rows if r['V6 status'] in statuses]
if len(target)!=27:
    sys.exit(f'STOP: Expected 27 ambiguous packages, found {len(target)}.')
print('Reading Music metadata for ambiguous candidate selection...',flush=True)
fields={}
for field in ('name','artist','album','pid'):
    fields[field]=v6.applescript(v6.EXPORT,[field],timeout=600).rstrip('\n').split(v6.SEP)
    print(field,len(fields[field]),flush=True)
if len({len(x) for x in fields.values()})!=1:
    sys.exit('STOP: Music library metadata counts differ.')
lookup=defaultdict(list)
for name,artist,album,pid in zip(fields['name'],fields['artist'],fields['album'],fields['pid']):
    if re.fullmatch(r'[0-9a-fA-F]{16}',pid):
        lookup[(v6.norm(name),v6.norm(artist))].append((name,artist,album,pid.upper()))
choices=[]; seen=set(); unresolved=[]
for r in target:
    matches=lookup.get((v6.norm(r['Title from path']),v6.norm(r['Artist from path'])),[])
    if not matches:
        unresolved.append(r);continue
    album_matches=[m for m in matches if v6.norm(m[2])==v6.norm(r['Album from path'])]
    pool=album_matches or matches
    # Deterministic choice: exact album first, then original Music library order.
    chosen=pool[0]
    if chosen[3] not in seen:
        seen.add(chosen[3]);choices.append((r,chosen,len(matches),len(album_matches)))
print(f'Packages: {len(target)}; unique candidate tracks: {len(choices)}; unmatched: {len(unresolved)}')
print('Selection is BEST EFFORT. Some tracks may be alternate editions or already downloaded.')
for r,m,total,exact in choices:
    print(f"{r['Artist from path']} - {r['Title from path']} | chose: {m[2]} | candidates={total}, exact-album={exact}")
if unresolved:
    sys.exit('STOP: Some previously ambiguous tracks now have no candidates. No playlist created.')
if not choices:
    sys.exit('STOP: No tracks to add.')
playlist='iPod HLS Leftovers - Final Review 03'
print('\nCreating playlist:',playlist,flush=True)
print(v6.applescript(v6.CREATE,[playlist,*[m[3] for _,m,_,_ in choices]],timeout=900).strip())
print('No media or download changes were made. The 225 NOT_FOUND packages cannot be added as Music tracks without a match.')
