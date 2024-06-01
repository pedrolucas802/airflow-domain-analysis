import requests
import csv
from pathlib import Path
from os.path import join
from datetime import datetime
from airflow.models import BaseOperator  # Correct import statement
from flask import request
import hashlib
import whois
import dns.resolver
import socket
from whois.exceptions import WhoisException

class DomainAnalysisOperator(BaseOperator):
    @staticmethod
    def check_domain_exists(domain):
        try:
            dns.resolver.resolve(domain, 'A')
            return True
        except dns.resolver.NXDOMAIN:
            return False
        except dns.resolver.Timeout:
            return False

    @staticmethod
    def get_favicon_hash(url):
        protocols = ["http://", "https://"]
        for protocol in protocols:
            full_url = f"{protocol}{url}"
            try:
                response = requests.head(full_url, timeout=5)
                if response.status_code in [200, 301, 302]:
                    favicon_response = requests.get(f"{full_url}/favicon.ico", timeout=5)
                    r = requests.get(full_url, timeout=5)
                    cl = len(r.content)
                    if favicon_response.status_code == 200:
                        return {
                            "alive": True,
                            "Content-Length": cl,
                            "favicon_hash": hashlib.md5(favicon_response.content).hexdigest(),
                            "url_with_schema": full_url
                        }
                    else:
                        return {
                            "alive": True,
                            "error": "Failed to download favicon.ico.",
                            "url_with_schema": full_url
                        }
            except requests.exceptions.RequestException:
                pass
        return {"alive": False, "error": f"Website {url} is not alive."}

    @staticmethod
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
        except WhoisException as e:
            if 'No match' in str(e):
                return {"alive": False, "error": f"Domain {domain} not found."}
            else:
                return {"error": f"WHOIS error: {str(e)}"}

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def calculate_score(domain_info):
        score = 100

        creation_date = domain_info.get('creation_date')
        if creation_date:
            if isinstance(creation_date, str):
                creation_date = datetime.strptime(creation_date, "%Y-%m-%d %H:%M:%S")
            if creation_date < datetime(2010, 1, 1):
                score += 10
            elif creation_date < datetime(2020, 1, 1):
                score += 5
            elif creation_date < datetime.now():
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

    @staticmethod
    def query_domain(domain):
        if not domain:
            return {"error": "Domain parameter is required."}

        # domain_creation_date = DomainAnalysisOperator.get_domain_creation_date(domain)
        # if 'error' in domain_creation_date:
        #     return domain_creation_date
        mx_dns = DomainAnalysisOperator.check_mx_dns(domain)
        a_record = DomainAnalysisOperator.check_a_record(domain)
        cname_record = DomainAnalysisOperator.check_cname(domain)
        domain_info = {"domain": domain}
        # domain_info.update(domain_creation_date)
        domain_info.update(mx_dns)
        domain_info.update(a_record)
        domain_info.update(cname_record)
        return domain_info

    @staticmethod
    def query_ip():
        ip = request.args.get('ip')
        if not ip:
            return {"error": "IP parameter is required."}

        ip_owner = DomainAnalysisOperator.get_ip_owner(ip)
        return ip_owner

    @staticmethod
    def query_url():
        url = request.args.get('url')
        if not url:
            return {"error": "URL parameter is required."}

        favicon_result = DomainAnalysisOperator.get_favicon_hash(url)
        if 'error' in favicon_result:
            return favicon_result
        else:
            return {
                "alive": True,
                "Content-Length": favicon_result['Content-Length'],
                "url": favicon_result['url_with_schema'],
                "favicon_hash": favicon_result['favicon_hash']
            }

    @staticmethod
    def query_all():
        domain = request.args.get('domain')
        if not domain:
            return {"error": "Domain parameter is required."}

        domain_with_www = f"www.{domain}"
        favicon_result = DomainAnalysisOperator.get_favicon_hash(domain)
        if 'error' in favicon_result:
            favicon_result = DomainAnalysisOperator.get_favicon_hash(domain_with_www)

        if 'error' in favicon_result:
            return favicon_result

        try:
            ip_addresses = socket.gethostbyname(domain)
            ip_owner_results = []
            ip_owner = DomainAnalysisOperator.get_ip_owner(ip_addresses)
            ip_owner_results.append(ip_owner)
        except Exception as e:
            ip_owner_results = [{"error": f"Failed to resolve IP address for domain: {str(e)}"}]

        domain_info = {}
        domain_creation_date = DomainAnalysisOperator.get_domain_creation_date(domain)
        if 'error' in domain_creation_date:
            return domain_creation_date
        domain_info.update(domain_creation_date)

        mx_dns = DomainAnalysisOperator.check_mx_dns(domain)
        domain_info.update(mx_dns)

        cname_record = DomainAnalysisOperator.check_cname(domain)
        domain_info.update(cname_record)

        if 'alive' in favicon_result and favicon_result['alive']:
            result = {
                "domain": domain,
                "alive": True,
                "favicon_hash": favicon_result['favicon_hash'],
                "Content-Length": favicon_result['Content-Length'],
                "ip_owner_results": ip_owner_results,
                "domain_info": domain_info
            }
        else:
            result = {
                "alive": False
            }

        return result
