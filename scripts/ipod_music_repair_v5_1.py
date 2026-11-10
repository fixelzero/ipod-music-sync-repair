#!/usr/bin/env python3
"""iPod Music Repair V5.1: fast, read-only HLS package inventory + original V4 workflow.
Python 3.9+. Does not delete, move, download, or change Apple Music playlists.
"""
import argparse
import csv
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

DEFAULT_MEDIA = Path.home() / 'Music/iTunes Music/Media.localized'
DEFAULT_REPORTS = Path.home() / 'Desktop/iPod Repair Batches'


def scan(media, output):
    if not media.is_dir():
        raise SystemExit('Media folder not found: {}'.format(media))
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report = output / ('hls_inventory_' + stamp + '.csv')
    summary = Counter()
    total_bytes = 0
    with report.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Package path', 'Relative path', 'Package name', 'Parent folder',
                         'Files', 'Bytes (logical)', 'GiB (logical)', 'Manifests',
                         'Fragments', 'Initialization fragments', 'Other files'])
        for root, dirs, files in os.walk(str(media), followlinks=False):
            packages = [d for d in dirs if d.lower().endswith('.movpkg')]
            for name in packages:
                pkg = Path(root) / name
                counts = Counter()
                size = 0
                for subroot, subdirs, subfiles in os.walk(str(pkg), followlinks=False):
                    for filename in subfiles:
                        p = Path(subroot) / filename
                        try:
                            if p.is_symlink():
                                continue
                            size += p.stat().st_size
                            counts[p.suffix.lower()] += 1
                        except OSError:
                            summary['unreadable_files'] += 1
                nfiles = sum(counts.values())
                writer.writerow([str(pkg), str(pkg.relative_to(media)), name, str(pkg.parent),
                                 nfiles, size, '{:.4f}'.format(size / 1024**3),
                                 counts['.m3u8'], counts['.frag'], counts['.initfrag'],
                                 nfiles - counts['.m3u8'] - counts['.frag'] - counts['.initfrag']])
                summary['packages'] += 1
                summary['files'] += nfiles
                total_bytes += size
                if summary['packages'] % 100 == 0:
                    print('Scanned {} HLS packages...'.format(summary['packages']), flush=True)
            # Do not recursively visit package contents twice.
            dirs[:] = [d for d in dirs if not d.lower().endswith('.movpkg')]
    print('\nHLS packages: {}'.format(summary['packages']))
    print('Files inside packages: {}'.format(summary['files']))
    print('Logical package size: {:.2f} GiB'.format(total_bytes / 1024**3))
    if summary['unreadable_files']:
        print('Unreadable files: {}'.format(summary['unreadable_files']))
    print('CSV inventory: {}'.format(report))
    print('Read-only: no Apple Music library or media files were changed.')
    print('NOTE: Packages are NOT proven duplicates or safe-to-remove files.')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scan-hls', action='store_true', help='Inventory .movpkg folders without contacting Music')
    parser.add_argument('--media', type=Path, default=DEFAULT_MEDIA)
    parser.add_argument('--output', type=Path, default=DEFAULT_REPORTS)
    parser.add_argument('--errors', type=Path, help='Run the original V4 Finder missing-file workflow')
    parser.add_argument('--batch', type=int, help='Pass batch number to V4')
    parser.add_argument('--preview', action='store_true', help='Pass preview mode to V4')
    parser.add_argument('--v4-script', type=Path, default=Path(__file__).with_name('ipod_repair_batch_v4.py'))
    args = parser.parse_args()
    if not args.scan_hls and not args.errors:
        parser.error('Choose --scan-hls and/or --errors PATH')
    if args.scan_hls:
        scan(args.media, args.output)
    if args.errors:
        if not args.v4_script.is_file():
            parser.error('Original V4 script not found: {}. Use --v4-script PATH'.format(args.v4_script))
        cmd = [sys.executable, '-u', str(args.v4_script), str(args.errors)]
        if args.batch is not None:
            cmd += ['--batch', str(args.batch)]
        if args.preview:
            cmd.append('--preview')
        print('Launching original V4 workflow (unchanged): {}'.format(args.v4_script), flush=True)
        raise SystemExit(subprocess.call(cmd))


if __name__ == '__main__':
    main()
