#!/usr/bin/env python3
"""Batch organizer for iPod HLS Repair V5.3.2. Python 3.9+.
Scans remaining inventory, excludes prior batch reports, creates playlists of <=100.
Never removes/downloads media. Resume by rerunning; scan and queue results are retained.
"""
import argparse, csv, re, subprocess, sys
from pathlib import Path
from collections import Counter

ROOT = Path.home() / 'Desktop/iPod Repair Batches'
BASE = Path.home() / 'Downloads/ipod_music_repair_v5_3_2.py'
INV = ROOT / 'hls_inventory_20261109_172133.csv'
FIELDS = ['Package path','Artist from path','Album from path','Title from path','Status','Music title','Music artist','Music album','Persistent ID','Cloud status','Music location','Notes']

def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

def call(args):
    print('\n$ '+ ' '.join(str(x) for x in args),flush=True)
    subprocess.run([str(x) for x in args],check=True)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--create-playlists',action='store_true',help='Explicit permission to create Music playlists after scans')
    ap.add_argument('--start',type=int,default=500,help='First unscanned inventory offset (default 500)')
    ap.add_argument('--scan-size',type=int,default=100)
    ap.add_argument('--playlist-size',type=int,default=100)
    ap.add_argument('--timeout',type=int,default=45)
    args=ap.parse_args()
    if args.start<0 or args.scan_size<1 or not 1<=args.playlist_size<=100: ap.error('Invalid batch sizes/offset')
    if not BASE.is_file() or not INV.is_file(): ap.error('Missing V5.3.2 script or HLS inventory')
    inventory=read(INV)
    total=len(inventory)
    if args.start>total: ap.error('Start beyond inventory')
    ROOT.mkdir(parents=True,exist_ok=True)
    # Include completed batch reports 01/02/03 when present; their IDs are excluded.
    used=set()
    for n in range(1,100):
        p=ROOT / ('hls_repair_batch_%02d_100.csv'%n)
        if not p.exists():
            if n<=2: ap.error('Missing completed report '+str(p))
            continue
        for r in read(p):
            pid=r.get('Persistent ID','').upper()
            if pid: used.add(pid)
    print('Previously reported persistent IDs excluded:',len(used),flush=True)
    # Reuse known scan reports, and scan the remaining inventory in bounded chunks.
    reports=[]
    known=[(0,50),(50,50),(100,150),(250,250)]
    for start,count in known:
        p=ROOT / f'hls_v531_start{start}_count{count}.csv'
        if p.exists(): reports.append(p)
        elif start < args.start: ap.error('Missing previous scan report: '+str(p))
    for start in range(args.start,total,args.scan_size):
        count=min(args.scan_size,total-start)
        p=ROOT / f'hls_v531_start{start}_count{count}.csv'
        if not p.exists():
            call([sys.executable,'-u',BASE,'scan',INV,'--start',start,'--limit',count,'--timeout',args.timeout])
        else:
            print('Reusing existing scan:',p.name,flush=True)
        reports.append(p)
    # Collect all eligible unique IDs not present in any completed batch report.
    eligible=[]; seen=set(used); status=Counter()
    for report in reports:
        for row in read(report):
            status[row.get('Status','UNKNOWN')]+=1
            pid=row.get('Persistent ID','').upper()
            if row.get('Status')!='VERIFIED_MATCHED_HLS' or not re.fullmatch('[0-9A-F]{16}',pid) or pid in seen: continue
            eligible.append(row); seen.add(pid)
    print('\nScan status totals:',dict(status),flush=True)
    print('New unique verified Matched HLS candidates:',len(eligible),flush=True)
    # Use the next unused batch number. A previous partial report is never overwritten.
    numbers=[]
    for p in ROOT.glob('hls_repair_batch_*_100.csv'):
        m=re.fullmatch(r'hls_repair_batch_(\d+)_100\.csv',p.name)
        if m: numbers.append(int(m.group(1)))
    next_number=max(numbers,default=0)+1
    if not eligible:
        print('Nothing new to queue. No media changed.')
        return
    for i in range(0,len(eligible),args.playlist_size):
        chunk=eligible[i:i+args.playlist_size]
        number=next_number+i//args.playlist_size
        report=ROOT / ('hls_repair_batch_%02d_100.csv'%number)
        if report.exists(): raise RuntimeError('Refusing to overwrite '+str(report))
        with report.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=FIELDS,extrasaction='ignore');w.writeheader();w.writerows(chunk)
        playlist='iPod HLS Repair - Batch %02d'%number
        print(f'\nPrepared {report.name}: {len(chunk)} tracks -> {playlist}',flush=True)
        if args.create_playlists:
            call([sys.executable,'-u',BASE,'queue',report,'--create-playlists','--playlist-name',playlist,'--batch-size',args.playlist_size,'--timeout',args.timeout])
        else:
            print('DRY RUN: playlist not created; rerun with --create-playlists ONLY AFTER reviewing reports.',flush=True)
    print('\nDone. Inspect each *_queue_results.csv for SKIP/ERROR and check playlist counts in Music.')
    print('No media files removed or downloaded. Do not delete .movpkg packages manually.')

if __name__=='__main__':
    try: main()
    except (OSError,ValueError,subprocess.CalledProcessError,RuntimeError) as e:
        print('ERROR:',e,file=sys.stderr);sys.exit(1)
