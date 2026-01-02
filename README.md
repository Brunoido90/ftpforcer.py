Practical Examples:

    Basic Usage:
    code

python ftp_bruteforcer.py 192.168.1.1 -p 2121 -u users.txt -w passwords.txt -t 20

Generate Wordlists:
code
python ftp_bruteforcer.py 192.168.1.1 -g -t 15

Hybrid Mode (Default):
code
python ftp_bruteforcer.py 192.168.1.1 -m hybrid -t 12

CPU Mode Only:
code
python ftp_bruteforcer.py 192.168.1.1 -m cpu -t 8
