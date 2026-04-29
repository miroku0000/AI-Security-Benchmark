# wordlists

## `xato-net-10-million-passwords-10000.txt`

Top 10,000 most common passwords from the xato.net 10-million-passwords
corpus, vendored from SecLists for offline demo use.

- **Upstream:** https://github.com/danielmiessler/SecLists/blob/master/Passwords/Common-Credentials/xato-net-10-million-passwords-10000.txt
- **License:** MIT (SecLists)
- **Original source:** https://xato.net/today-i-am-releasing-ten-million-passwords-f6078bba6b0
- **Size:** ~76 KB / 9,999 unique entries
- **Use here:** Online brute-force target list for the AI's login endpoint
  in `demos/rate-limit-bruteforce/`. Alice's seeded password (`sunshine`)
  appears at line 49.

This is a public, widely-used wordlist included to keep the demo
self-contained — `./run-demo.sh` does not need to fetch anything from
the network. To swap in a different wordlist (e.g. rockyou.txt, SecLists
Top 1M), edit `WORDLIST` in `exploit.py`.
