"""
GeeksforGeeks C++ Content Scraper
Scrapes C++ programming tutorials and notes from GeeksforGeeks
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin
import re


class GeeksForGeeksScraper:
    """Scraper for GeeksforGeeks C++ content"""
    
    def __init__(self, output_dir: str = "data/raw/course_content"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.base_url = "https://www.geeksforgeeks.org"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_topic_links(self, main_url: str) -> List[Dict]:
        """
        Extract all C++ topic links from the main page
        
        Args:
            main_url: Main C++ page URL
            
        Returns:
            List of dictionaries with topic info
        """
        try:
            print(f"Fetching main page: {main_url}")
            response = self.session.get(main_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            topics = []
            
            # Find all article links (GeeksforGeeks structure)
            # Look for links in the content area
            content_area = soup.find('div', class_='content') or soup.find('article')
            
            if content_area:
                links = content_area.find_all('a', href=True)
                
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # Filter relevant C++ topic links
                    if href and text and len(text) > 5:
                        # Make absolute URL
                        full_url = urljoin(self.base_url, href)
                        
                        # Only include geeksforgeeks.org links
                        if 'geeksforgeeks.org' in full_url:
                            topics.append({
                                'title': text,
                                'url': full_url,
                                'category': 'C++ Programming'
                            })
            
            # Remove duplicates
            seen_urls = set()
            unique_topics = []
            for topic in topics:
                if topic['url'] not in seen_urls:
                    seen_urls.add(topic['url'])
                    unique_topics.append(topic)
            
            print(f"✓ Found {len(unique_topics)} unique topic links")
            return unique_topics[:30]  # Limit to first 30 topics for now
            
        except Exception as e:
            print(f"✗ Error fetching topic links: {e}")
            return []
    
    def scrape_article(self, url: str, title: str) -> Optional[Dict]:
        """
        Scrape a single article/tutorial
        
        Args:
            url: Article URL
            title: Article title
            
        Returns:
            Dictionary with article content
        """
        try:
            print(f"  Scraping: {title[:50]}...")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract main content
            article_content = self._extract_content(soup)
            
            if article_content:
                return {
                    'title': title,
                    'url': url,
                    'content': article_content,
                    'content_length': len(article_content),
                    'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'source': 'GeeksforGeeks',
                    'course': 'Programming Fundamentals',
                    'language': 'C++'
                }
            
            return None
            
        except Exception as e:
            print(f"    ✗ Error scraping {title[:30]}: {e}")
            return None
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main article content from soup"""
        
        # Try different content selectors
        content_selectors = [
            'div.entry-content',
            'div.text',
            'article',
            'div.content',
            'div[itemprop="articleBody"]'
        ]
        
        content_text = ""
        
        for selector in content_selectors:
            content_div = soup.select_one(selector)
            if content_div:
                # Remove script and style elements
                for script in content_div(["script", "style", "nav", "footer"]):
                    script.decompose()
                
                # Get text
                text = content_div.get_text(separator='\n', strip=True)
                
                # Clean up multiple newlines
                text = re.sub(r'\n{3,}', '\n\n', text)
                
                if len(text) > 200:  # Only return if substantial content
                    content_text = text
                    break
        
        return content_text
    
    def scrape_multiple_articles(self, topics: List[Dict], limit: int = 20) -> List[Dict]:
        """
        Scrape multiple articles
        
        Args:
            topics: List of topic dictionaries
            limit: Maximum number of articles to scrape
            
        Returns:
            List of scraped articles
        """
        articles = []
        
        for i, topic in enumerate(topics[:limit], 1):
            print(f"\n[{i}/{min(limit, len(topics))}]")
            
            article_data = self.scrape_article(topic['url'], topic['title'])
            
            if article_data:
                articles.append(article_data)
            
            # Be polite - wait between requests
            time.sleep(2)
        
        return articles
    
    def save_to_json(self, articles: List[Dict], filename: str = "geeksforgeeks_cpp_content.json"):
        """Save articles to JSON"""
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Saved {len(articles)} articles to {output_path}")
        return output_path
    
    def save_as_text(self, articles: List[Dict]):
        """Save each article as individual text file"""
        text_dir = self.output_dir / "text_files"
        text_dir.mkdir(exist_ok=True)
        
        for i, article in enumerate(articles, 1):
            # Create safe filename
            safe_title = re.sub(r'[^\w\s-]', '', article['title'])[:50]
            safe_title = re.sub(r'[-\s]+', '_', safe_title)
            filename = f"{i:02d}_{safe_title}.txt"
            
            filepath = text_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Title: {article['title']}\n")
                f.write(f"URL: {article['url']}\n")
                f.write(f"Source: {article['source']}\n")
                f.write(f"Course: {article['course']}\n")
                f.write(f"\n{'='*80}\n\n")
                f.write(article['content'])
        
        print(f"✓ Saved {len(articles)} text files to {text_dir}")
    
    def print_summary(self, articles: List[Dict]):
        """Print summary of scraped content"""
        print("\n" + "="*70)
        print("GEEKSFORGEEKS SCRAPING SUMMARY")
        print("="*70)
        print(f"Total articles scraped: {len(articles)}")
        print(f"Total content length: {sum(a['content_length'] for a in articles):,} characters")
        print("\nArticles:")
        for i, article in enumerate(articles, 1):
            print(f"  {i}. {article['title'][:60]}")
        print("="*70)


def main():
    """Main function"""
    
    scraper = GeeksForGeeksScraper()
    
    # Main C++ page
    cpp_url = "https://www.geeksforgeeks.org/cpp/c-plus-plus/"
    
    print("="*70)
    print("GeeksforGeeks C++ Content Scraper")
    print("="*70)
    print(f"Target: {cpp_url}\n")
    
    # Step 1: Get topic links
    print("Step 1: Extracting topic links...")
    topics = scraper.get_topic_links(cpp_url)
    
    if not topics:
        print("✗ No topics found. Exiting.")
        return
    
    print(f"\nFound topics:")
    for i, topic in enumerate(topics[:10], 1):
        print(f"  {i}. {topic['title'][:60]}")
    if len(topics) > 10:
        print(f"  ... and {len(topics) - 10} more")
    
    # Step 2: Scrape articles
    print(f"\nStep 2: Scraping articles (limit: 20)...")
    articles = scraper.scrape_multiple_articles(topics, limit=20)
    
    if articles:
        # Step 3: Save data
        print("\nStep 3: Saving data...")
        scraper.save_to_json(articles)
        scraper.save_as_text(articles)
        scraper.print_summary(articles)
        
        print("\n✓ Scraping completed successfully!")
    else:
        print("\n✗ No articles were successfully scraped")


if __name__ == "__main__":
    main()