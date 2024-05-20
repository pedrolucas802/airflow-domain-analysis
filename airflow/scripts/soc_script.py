from flask import Flask, request, jsonify
import requests
import hashlib
import whois
import dns.resolver
import sqlite3
import os
import datetime
import socket

app = Flask(__name__)

def connect_to_database():
    db_path = os.path.join(os.getcwd(), 'local_database.db')
    if not os.path.exists(db_path):
        create_database(db_path)
    conn = sqlite3.connect(db_path)
    return conn

def create_database(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS domain_table (
                     id TEXT PRIMARY KEY,
                    creation_date TEXT,
                    mx TEXT,
                    a_record TEXT,
                    cname TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS ip_table (
                      id TEXT PRIMARY KEY,
                      owner TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS url_table (
                      id TEXT PRIMARY KEY,
                      favicon_hash TEXT)''')
    conn.commit()
    conn.close()

def check_domain_in_db(domain):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM domain_table WHERE id=?", (domain,))
    result = cursor.fetchone()
    conn.close()
    return result

def check_ip_in_db(ip):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT owner FROM ip_table WHERE id=?", (ip,))
    result = cursor.fetchone()
    conn.close()
    return result

def check_url_in_db(url):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("SELECT favicon_hash FROM url_table WHERE id=?", (url,))
    result = cursor.fetchone()
    conn.close()
    return result

def add_domain_to_db(domain, creation_date, mx, a_record=None, cname=None):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO domain_table (id, creation_date, mx, a_record, cname) VALUES (?, ?, ?, ?, ?)", (domain, creation_date, mx, a_record, cname))
    conn.commit()
    conn.close()

def add_ip_to_db(ip, owner):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO ip_table (id, owner) VALUES (?, ?)", (ip, owner))
    conn.commit()
    conn.close()

def add_url_to_db(url, favicon_hash):
    conn = connect_to_database()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO url_table (id, favicon_hash) VALUES (?, ?)", (url, favicon_hash))
    conn.commit()
    conn.close()

def check_domain_exists(domain):
    try:
        dns.resolver.resolve(domain, 'A')
        return True  
    except dns.resolver.NXDOMAIN:
        return False  
    except dns.resolver.Timeout:
        return False  

'''
[] OLD LOGIC -> BACK IF NEEDED
def get_favicon_hash_backup(url):
    protocols = ["http://", "https://"]
    domain = url

    try:
        for protocol in protocols:
            for www in ["", "www."]:
                full_url = f"{protocol}{www}{domain}"
                try:
                    response = requests.head(full_url, timeout=5)
                    if response.status_code == 200 or response.status_code == 301 or response.status_code == 302:
                        favicon_response = requests.get(f"{full_url}/favicon.ico", timeout=5)
                        if favicon_response.status_code == 200:
                            return {"alive": True, "favicon_hash": hashlib.md5(favicon_response.content).hexdigest()}
                        else:
                            return {"alive": True, "error": "Failed to download favicon.ico."}
                except requests.exceptions.RequestException:
                    pass
                

        for protocol in protocols:
            full_url = f"{protocol}{domain}"
            try:
                response = requests.head(full_url, timeout=5)
                if response.status_code == 200 or response.status_code == 301 or response.status_code == 302:
                    favicon_response = requests.get(f"{full_url}/favicon.ico", timeout=5)
                    if favicon_response.status_code == 200:
                        return {"alive": True, "favicon_hash": hashlib.md5(favicon_response.content).hexdigest()}
                    else:
                        return {"alive": True, "error": "Failed to download favicon.ico."}
            except requests.exceptions.RequestException:
                pass

        return {"alive": False, "error": f"Website {domain} is not alive."}
        
    except requests.exceptions.RequestException:
        return {"alive": True, "error": "Connection error during favicon download."}
'''

def get_favicon_hash(url):
    protocols = ["http://", "https://"]
    domain = url

    try:
        for protocol in protocols:
            full_url = f"{protocol}{domain}"
            try:
                response = requests.head(full_url, timeout=5)
                if response.status_code == 200 or response.status_code == 301 or response.status_code == 302:
                    favicon_response = requests.get(f"{full_url}/favicon.ico", timeout=5)
                    r = requests.get(full_url, timeout=5)
                    cl = len(r.content)
                    if favicon_response.status_code == 200:
                        return {"alive": True, "Content-Length": cl, "favicon_hash": hashlib.md5(favicon_response.content).hexdigest()}
                    else:
                        return {"alive": True, "error": "Failed to download favicon.ico."}
            except requests.exceptions.RequestException:
                pass

        for protocol in protocols:
            full_url = f"{protocol}www.{domain}"
            try:
                response = requests.head(full_url, timeout=5)
                if response.status_code == 200 or response.status_code == 301 or response.status_code == 302:
                    favicon_response = requests.get(f"{full_url}/favicon.ico", timeout=5)
                    r = requests.get(full_url, timeout=5)
                    cl = len(r.content)
                    if favicon_response.status_code == 200:
                        return {"alive": True, "Content-Length": cl, "favicon_hash": hashlib.md5(favicon_response.content).hexdigest()}
                    else:
                        return {"alive": True, "error": "Failed to download favicon.ico."}
            except requests.exceptions.RequestException:
                pass

        return {"alive": False, "error": f"Website {domain} is not alive."}
        
    except requests.exceptions.RequestException:
        return {"alive": True, "error": "Connection error during favicon download."}



def get_domain_creation_date(domain):
    try:
        domain_info = whois.whois(domain)
        if domain_info.creation_date:
            if isinstance(domain_info.creation_date, list):
                creation_date = domain_info.creation_date[0]
            else:
                creation_date = domain_info.creation_date
            return {"creation_date": creation_date}
        else:
            return {"error": "Creation date not found."}
    except whois.parser.PywhoisError as e:
        if 'No match' in str(e):
            return {"alive": False, "error": f"Domain {domain} not found."}
        else:
            return {"error": f"WHOIS error: {str(e)}"}

def get_ip_owner(ip):
    try:
        response = requests.get(f"http://ipinfo.io/{ip}/json")
        if response.status_code == 200:
            data = response.json()
            return {"ip_owner": data.get('org', "Owner information not found.")}
        else:
            return {"error": "Owner information not found."}
    except Exception as e:
        return {"error": f"Error retrieving IP owner information: {str(e)}"}

def check_mx_dns(domain):
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        if mx_records:
            return {"mx": "true"}
        else:
            return {"mx": "false"}
    except dns.resolver.NoAnswer:
        return {"mx": "false"}
    except dns.resolver.NXDOMAIN:
        return {"mx": "false"}
    except dns.resolver.Timeout:
        return {"mx": "false"}

def check_a_record(domain):
    try:
        a_records = dns.resolver.resolve(domain, 'A')
        if a_records:
            ip_addresses = [record.address for record in a_records]
            return {"a_record": ", ".join(ip_addresses)}
        else:
            return {"a_record": "false"}
    except dns.resolver.NoAnswer:
        return {"a_record": "false"}
    except dns.resolver.NXDOMAIN:
        return {"a_record": "false"}
    except dns.resolver.Timeout:
        return {"a_record": "false"}

def check_cname(domain):
    try:
        cname_records = dns.resolver.resolve(domain, 'CNAME')
        if cname_records:
            cnames = [record.target.to_text() for record in cname_records]
            return {"cname": ", ".join(cnames)}
        else:
            return {"cname": "false"}
    except dns.resolver.NoAnswer:
        return {"cname": "false"}
    except dns.resolver.NXDOMAIN:
        return {"cname": "false"}
    except dns.resolver.Timeout:
        return {"cname": "false"}

def calculate_score(domain_info):
    score = 100

    creation_date = domain_info.get('creation_date')
    if creation_date:
        if isinstance(creation_date, str):
            creation_date = datetime.datetime.strptime(creation_date, "%Y-%m-%d %H:%M:%S")
        if creation_date < datetime.datetime(2010, 1, 1):
            score += 10
        elif creation_date < datetime.datetime(2020, 1, 1):
            score += 5
        elif creation_date < datetime.datetime.now():
            score += 2

    if domain_info.get('contact_info'):
        score += 5

    if domain_info.get('ssl_certificate'):
        score += 5

    if domain_info.get('ip'):
        ip_reputation = check_ip_in_db(domain_info['ip'])
        if ip_reputation and ip_reputation[0] == "Malicious":
            score -= 10

    if domain_info.get('mx'):
        if domain_info['mx'] == "false":
            score -= 10

    return score


def query_domain_airflow(domain):
    if not domain:
        return jsonify({"error": "Domain parameter is required."}), 200
    if check_domain_exists:
        domain_in_db = check_domain_in_db(domain)
        if domain_in_db:
            domain_info = {"domain": domain, "creation_date": domain_in_db[1], "mx": domain_in_db[2], "a_record": domain_in_db[3], "cname": domain_in_db[4]}
            score = calculate_score(domain_info)
            domain_info["score"] = score
            return jsonify(domain_info)
        else:
            domain_creation_date = get_domain_creation_date(domain)
            if 'error' in domain_creation_date:
                return jsonify(domain_creation_date)
            mx_dns = check_mx_dns(domain)
            a_record = check_a_record(domain)
            cname_record = check_cname(domain)
            add_domain_to_db(domain, domain_creation_date['creation_date'], mx_dns['mx'], a_record['a_record'], cname_record['cname'])
            domain_info = {"domain": domain}
            domain_info.update(domain_creation_date)
            domain_info.update(mx_dns)
            #domain_info.update(a_record)
            domain_info.update(cname_record)
            #score = calculate_score(domain_info)
            #domain_info["score"] = score
            return jsonify(domain_info)
    else:
        return {"alive": False}

def query_url_airflow():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL parameter is required."}), 200
    
    favicon_result = get_favicon_hash(url)
    if 'error' in favicon_result:
        return jsonify(favicon_result), 200
    else:
        return jsonify({"alive":True, "Content-Length":favicon_result['Content-Length'], "url": url, "favicon_hash": favicon_result['favicon_hash']}), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
