#!/usr/bin/env python3
"""
Tool to investigate and document retailer APIs
"""
import requests
import json
import re
from urllib.parse import urljoin, urlparse, parse_qs
from typing import Dict, List, Optional
import time
from bs4 import BeautifulSoup


class APIInvestigator:
    """Investigate retailer websites for API endpoints"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        })
    
    def investigate_zooplus(self) -> Dict:
        """Investigate Zooplus for API endpoints"""
        print("🔍 Investigating Zooplus API...")
        
        findings = {
            'base_url': 'https://www.zooplus.co.uk',
            'api_endpoints': [],
            'search_patterns': [],
            'ajax_calls': [],
            'structured_data': {},
            'recommendations': []
        }
        
        # Test main search page
        search_url = 'https://www.zooplus.co.uk/shop/dogs/dry_dog_food'
        try:
            response = self.session.get(search_url)
            if response.status_code == 200:
                print("✅ Main search page accessible")
                
                # Look for API calls in HTML/JavaScript
                api_patterns = [
                    r'api[/.]([^"\']+)',
                    r'ajax[/.]([^"\']+)', 
                    r'/api/v\d+/([^"\']+)',
                    r'fetch\([\'"]([^\'"]+)[\'"]',
                    r'\.get\([\'"]([^\'"]+)[\'"]',
                ]
                
                for pattern in api_patterns:
                    matches = re.findall(pattern, response.text, re.IGNORECASE)
                    for match in matches:
                        if 'api' in match.lower():
                            findings['api_endpoints'].append(match)
                
                # Look for structured data
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # JSON-LD structured data
                json_ld_scripts = soup.find_all('script', type='application/ld+json')
                for script in json_ld_scripts:
                    try:
                        data = json.loads(script.string)
                        findings['structured_data']['json_ld'] = data
                    except:
                        pass
                
                # Look for product data in page
                product_elements = soup.find_all(['div', 'article'], class_=re.compile(r'product', re.I))
                if product_elements:
                    print(f"📦 Found {len(product_elements)} product elements")
            
        except Exception as e:
            print(f"❌ Error accessing search page: {e}")
        
        # Test search functionality
        search_terms = ['Royal Canin', 'Hills', 'Purina']
        for term in search_terms:
            print(f"🔎 Testing search for: {term}")
            search_results = self._test_search(findings['base_url'], term)
            if search_results:
                findings['search_patterns'].extend(search_results)
        
        # Try to find API documentation or developer resources
        api_docs_paths = [
            '/api',
            '/api/docs', 
            '/api/v1',
            '/api/v2',
            '/developers',
            '/partner',
            '/affiliate'
        ]
        
        for path in api_docs_paths:
            try:
                url = urljoin(findings['base_url'], path)
                response = self.session.get(url)
                if response.status_code == 200 and 'api' in response.text.lower():
                    findings['api_endpoints'].append(path)
                    print(f"🎯 Found potential API endpoint: {path}")
            except:
                pass
        
        # Generate recommendations
        findings['recommendations'] = self._generate_zooplus_recommendations(findings)
        
        return findings
    
    def _test_search(self, base_url: str, search_term: str) -> List[str]:
        """Test search functionality and look for API calls"""
        search_patterns = []
        
        # Common search URL patterns
        search_urls = [
            f"{base_url}/shop/search?q={search_term}",
            f"{base_url}/search?query={search_term}",
            f"{base_url}/api/search?q={search_term}",
            f"{base_url}/api/products/search?query={search_term}"
        ]
        
        for url in search_urls:
            try:
                response = self.session.get(url)
                if response.status_code == 200:
                    # Check if response is JSON (likely API)
                    try:
                        json_data = response.json()
                        search_patterns.append({
                            'url': url,
                            'type': 'api',
                            'response': 'json',
                            'sample_data': str(json_data)[:200]
                        })
                        print(f"🎯 Found JSON API endpoint: {url}")
                    except:
                        # HTML response
                        if search_term.lower() in response.text.lower():
                            search_patterns.append({
                                'url': url,
                                'type': 'html',
                                'response': 'html',
                                'contains_results': True
                            })
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                print(f"❌ Error testing {url}: {e}")
        
        return search_patterns
    
    def _generate_zooplus_recommendations(self, findings: Dict) -> List[str]:
        """Generate recommendations based on findings"""
        recommendations = []
        
        if findings['api_endpoints']:
            recommendations.append("✅ API endpoints found - try API-first approach")
            recommendations.append(f"🔗 Test these endpoints: {', '.join(findings['api_endpoints'][:3])}")
        else:
            recommendations.append("❌ No clear API endpoints found")
            recommendations.append("🕸️ Use web scraping with structured data parsing")
        
        if findings['structured_data']:
            recommendations.append("📊 Structured data available - can extract from HTML")
        
        if findings['search_patterns']:
            recommendations.append("🔍 Search functionality identified")
            api_searches = [p for p in findings['search_patterns'] if p.get('type') == 'api']
            if api_searches:
                recommendations.append(f"🎯 Use API search: {api_searches[0]['url']}")
            else:
                recommendations.append("🕸️ Use HTML scraping for search results")
        
        return recommendations
    
    def investigate_fressnapf(self) -> Dict:
        """Investigate Fressnapf for API endpoints"""
        print("🔍 Investigating Fressnapf API...")
        
        findings = {
            'base_url': 'https://www.fressnapf.de',
            'api_endpoints': [],
            'graphql_endpoint': None,
            'recommendations': []
        }
        
        # Check for GraphQL (common in modern e-commerce)
        graphql_paths = ['/graphql', '/api/graphql', '/gql']
        for path in graphql_paths:
            try:
                url = urljoin(findings['base_url'], path)
                response = self.session.post(url, json={'query': '{__schema{types{name}}}'})
                if response.status_code == 200 and 'data' in response.text:
                    findings['graphql_endpoint'] = url
                    print(f"🎯 Found GraphQL endpoint: {url}")
                    break
            except:
                pass
        
        # Check main page for API patterns
        try:
            response = self.session.get(findings['base_url'])
            if response.status_code == 200:
                # Look for API patterns
                api_matches = re.findall(r'["\']([^"\']*api[^"\']*)["\']', response.text, re.IGNORECASE)
                findings['api_endpoints'] = list(set(api_matches[:10]))  # Limit to 10 unique
        except Exception as e:
            print(f"❌ Error accessing Fressnapf: {e}")
        
        findings['recommendations'] = self._generate_fressnapf_recommendations(findings)
        return findings
    
    def _generate_fressnapf_recommendations(self, findings: Dict) -> List[str]:
        recommendations = []
        
        if findings['graphql_endpoint']:
            recommendations.append("✅ GraphQL API found - use for structured queries")
            recommendations.append("📋 Develop GraphQL queries for product search")
        elif findings['api_endpoints']:
            recommendations.append("✅ REST API endpoints found")
        else:
            recommendations.append("❌ No APIs found - use web scraping")
            recommendations.append("🕸️ Focus on structured HTML parsing")
        
        return recommendations
    
    def generate_report(self, retailers: List[str] = None) -> Dict:
        """Generate comprehensive API investigation report"""
        if retailers is None:
            retailers = ['zooplus', 'fressnapf']
        
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'retailers': {},
            'summary': {},
            'next_steps': []
        }
        
        print("🚀 Starting API Investigation...")
        
        for retailer in retailers:
            if retailer == 'zooplus':
                report['retailers']['zooplus'] = self.investigate_zooplus()
            elif retailer == 'fressnapf':
                report['retailers']['fressnapf'] = self.investigate_fressnapf()
        
        # Generate summary
        total_endpoints = sum(len(data.get('api_endpoints', [])) for data in report['retailers'].values())
        has_graphql = any('graphql_endpoint' in data and data['graphql_endpoint'] for data in report['retailers'].values())
        
        report['summary'] = {
            'total_api_endpoints': total_endpoints,
            'has_graphql': has_graphql,
            'retailers_with_apis': len([r for r in report['retailers'].values() if r.get('api_endpoints')])
        }
        
        # Generate next steps
        if total_endpoints > 0:
            report['next_steps'].append("1. Implement API connectors for retailers with endpoints")
            report['next_steps'].append("2. Test authentication requirements")
            report['next_steps'].append("3. Implement rate limiting")
        else:
            report['next_steps'].append("1. Implement web scrapers with BeautifulSoup")
            report['next_steps'].append("2. Use structured data extraction")
            report['next_steps'].append("3. Implement anti-bot measures")
        
        return report
    
    def save_report(self, report: Dict, filename: str = 'api_investigation_report.json'):
        """Save investigation report to file"""
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"📋 Report saved to {filename}")


if __name__ == "__main__":
    investigator = APIInvestigator()
    report = investigator.generate_report()
    investigator.save_report(report)
    
    # Print summary
    print("\n" + "="*50)
    print("API INVESTIGATION SUMMARY")
    print("="*50)
    
    for retailer, data in report['retailers'].items():
        print(f"\n{retailer.upper()}:")
        print(f"  API Endpoints: {len(data.get('api_endpoints', []))}")
        if data.get('recommendations'):
            print("  Recommendations:")
            for rec in data['recommendations'][:3]:
                print(f"    - {rec}")
    
    print(f"\nNEXT STEPS:")
    for step in report['next_steps']:
        print(f"  {step}")