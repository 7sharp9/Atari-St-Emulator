"""Run REPL lines against a snapshot: repl.py <snap> <script.txt|-> ; prints the REPL output tail."""
import os, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__)); root = here
while not os.path.exists(os.path.join(root, 'tools', 'rdis.py')): root = os.path.dirname(root)
WORK = os.path.join(root, 'scratchpad', 'midwinter')
DISK = os.path.join(WORK, 'zuul067.st')
DLL = os.path.join(root, 'bin', 'Debug', 'net8.0', 'M68000.dll')

def run(snap, lines):
    p = subprocess.run(['dotnet', 'exec', DLL, 'resume', snap, 'repl', '--disk-a', DISK],
                       input='\n'.join(lines + ['q']) + '\n', capture_output=True, text=True, cwd=root,
                       env=dict(os.environ, ATARI_NOTRACE='1'))
    return p.stdout + p.stderr

if __name__ == '__main__':
    src = sys.stdin if sys.argv[2] == '-' else open(sys.argv[2])
    out = run(sys.argv[1], [l.rstrip('\n') for l in src if l.strip() and not l.startswith('#')])
    print(out[-int(os.environ.get('TAIL', '3000')):])
