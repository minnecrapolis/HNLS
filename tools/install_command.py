#!/usr/bin/env python3
"""Print real release installer commands after choosing a GitHub repository."""
import argparse
from pathlib import Path
from bootstrap_release import command

def main():
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository',required=True,help='Your actual OWNER/REPOSITORY')
    parser.add_argument('--version',default=(root/'VERSION').read_text().strip())
    args=parser.parse_args()
    try:
        print('After publishing hnls-setup.sh, the source ZIP and SHA256SUMS.txt to this release:')
        print('Main Pi: '+command(args.repository,args.version))
        print('Additional Pi: '+command(args.repository,args.version,'receiver'))
    except ValueError as error:parser.error(str(error))
if __name__=='__main__':main()
