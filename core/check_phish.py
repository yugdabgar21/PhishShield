import sys
import re
import requests
import json
from urllib.parse import urlparse, quote
from datetime import datetime

#Configuration
# Replace with your actual Auth-Key from https://auth.abuse.ch/
URLHAUS_AUTH_KEY = "ENTER YOUR AUTH KEY"

# PhishStats API Configuration
PHISHSTATS_API_BASE = "https://api.phishstats.info/api/phishing"

#Heuristic Checks
def is_suspicous_heuristic(url):
    try:
        #Normal URL
        if not url.startswith(('https://','http://')):
            url = 'http://' + url
            parsed = urlparse(url)
            host = parsed.hostname or ''

        # 1. Check for @ in URL (e.g., http://paypal.com@evil.com)
        if '@' in url:
            return True

        # 2. Check for IP address as host
        if re.match(r'^\d+\.\d+\.\d+\.\d+$',host):
            return True

        # 3. Check for URL shorteners
        shortners = ['bit.ly','tinyurl.com','goo.gl','t.co','ow.ly','is.gd','chamjs.com','siegelpigeons.com','iber.5-juzeb-0-io.ru','greet4.0-we-fid-707-i.ru','flame4.tuful32io3.online','stI11.tuful32io3.online','mo0n.sys7yn0iy5.online','gr0w.sys7yn0iy5.online','softS.sys7yn0iy5.online']
        if any(shortner in host for shortner in shortners):
            return True

        # 4. Check for unusual TLDs or too many subdomains
        parts = host.split('.')
        if len(parts)>4:
            return True

        return False
    except:
        return False
#API Checks
def check_urlhaus(url):
    try:
        headers = {"Auth-Key": URLHAUS_AUTH_KEY}
        data = {"url": url}
        response = requests.post("https://urlhaus-api.abuse.ch/v1/url/",
                                 headers=headers,
                                 data=data,
                                 timeout=10
                                 )
        result = response.json()
        return result.get("query_status") == "ok"
    except Exception as e:
        print(f"URLhaus check failed: {e}",file=sys.stderr)
        return False

def check_phishstats(url):
    try:
        # Method 1: Search for exact URL in the database
        encoded_url = quote(url,safe='')
        query = f"{PHISHSTATS_API_BASE}?_where=(url,eq,{encoded_url})&_size=1"

        response = requests.get(query,timeout=10)

        if response.status_code == 200:
            results = response.json()
        # If we found an exact match, it's malicious
        if results and len(results) > 0:
            return True
        # Method 2: Search for URL using 'like' operator (partial match)
        # Extract domain from URL for broader search
        parsed = urlparse(url if url.startswith(('https://','https:/'))else'https://'+url)
        domain = parsed.hostname

        if domain:
            query = f"{PHISHSTATS_API_BASE}?_where=(url,like,{quote(domain,safe='')})&_size=10&_sort=-score"
            response = requests.get(query,timeout=10)

        if response.status_code == 200:
            results = response.json()
        # Check if any high-confidence matches exist
        for result in results:
            if result.get('score',0)>5:
                if domain in result.get('url',''):
                    return True

        return False

    except Exception as e:
        print(f"PhishStats check failed: {e}",file=sys.stderr)
        return False

def check_phishstats_advanced(url):
    try:
        parsed = urlparse(url if url.startswith(('http://','https://'))else'http://'+url)
        domain = parsed.hostname
        path = parsed.path

        checks = []

        # Check 1: Exact URL match
        exact_query = f"{PHISHSTATS_API_BASE}?_where=(url,like,{quote(url,safe='')})&_size=5"
        checks.append(exact_query)

        # Check 2: Domain match with high score
        if domain:
            domain_query = f"{PHISHSTATS_API_BASE}?_where=(url,like,{quote(domain,safe='')})~and(score,gt,5)&_size=10"
            checks.append(domain_query)

        # Check 3: Check for common phishing keywords in path
        phishing_keywords = ['login','verify','account','secure','update','confirm']
        if any(keyword in path.lower()for keyword in phishing_keywords):
            keyword_query = f"{PHISHSTATS_API_BASE}?_where=(url,like,{quote(domain,safe='')})~and(score,gt,3)&_size=5"
            checks.append(keyword_query)

        # Execute checks
        for query in checks:
            response = requests.get(query,timeout=10)
            if response.status_code == 200:
                results = response.json()
                if results and len(results)>0:
                    return True

        return False
    except Exception as e:
        print(f"PhishSTats advanced check failed: {e}",file=sys.stderr)
        return False

#Main Logic
def main():
    if len(sys.argv)<2:
        print("Usage: python check_phish.py <url>")
        print("SAFE")
        sys.exit(0)

    url = sys.argv[1].strip()

    # Run checks in order of speed (fastest first)
    # 1. Local heuristic checks (instant)
    if is_suspicous_heuristic(url):
        print("MALICIOUS")
        return

    # 2. URLhaus check
    if check_urlhaus(url):
        print("MALICIOUS")
        return

    # 3. PhishStats check (basic)
    if check_phishstats(url):
        print("MALICIOUS")
        return

    # 4. PhishStats advanced check
    if check_phishstats_advanced(url):
        print("MALICIOUS")
        return

    # If all checks pass, URL is safe
    print("SAFE")

if __name__ == "__main__":
    main()
