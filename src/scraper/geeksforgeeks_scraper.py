"""
GeeksforGeeks C++ Content Scraper with Image Download
Scrapes C++ programming tutorials, images, and code examples from GeeksforGeeks
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse
import re
import hashlib
from PIL import Image
from io import BytesIO


class GeeksForGeeksScraper:
    """Scraper for GeeksforGeeks C++ content with image support"""
    
    def __init__(self, output_dir: str = "data/raw/course_content"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.images_dir = self.output_dir / "images"
        self.images_dir.mkdir(exist_ok=True)
        
        self.text_dir = self.output_dir / "text_files"
        self.text_dir.mkdir(exist_ok=True)
        
        self.base_url = "https://www.geeksforgeeks.org"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        self.downloaded_images = {}  # Track downloaded images
    
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
            
            # Find all article links
            content_area = soup.find('div', class_='content') or soup.find('article')
            
            if content_area:
                links = content_area.find_all('a', href=True)
                
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    if href and text and len(text) > 5:
                        full_url = urljoin(self.base_url, href)
                        
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
            return unique_topics[:30]
            
        except Exception as e:
            print(f"✗ Error fetching topic links: {e}")
            return []
    
    def download_image(self, img_url: str, article_id: str, img_index: int) -> Optional[Dict]:
        """
        Download and save an image
        
        Args:
            img_url: Image URL
            article_id: Unique article identifier
            img_index: Index of image in article
            
        Returns:
            Dictionary with image metadata
        """
        try:
            # Skip if already downloaded
            if img_url in self.downloaded_images:
                return self.downloaded_images[img_url]
            
            # Make absolute URL
            if not img_url.startswith('http'):
                img_url = urljoin(self.base_url, img_url)
            
            # Download image
            response = self.session.get(img_url, timeout=10)
            response.raise_for_status()
            
            # Verify it's an image
            try:
                img = Image.open(BytesIO(response.content))
                img.verify()
            except:
                return None
            
            # Create filename
            img_ext = Path(urlparse(img_url).path).suffix or '.png'
            if img_ext not in ['.jpg', '.jpeg', '.png', '.gif', '.svg']:
                img_ext = '.png'
            
            img_filename = f"{article_id}_img_{img_index:02d}{img_ext}"
            img_path = self.images_dir / img_filename
            
            # Save image
            with open(img_path, 'wb') as f:
                f.write(response.content)
            
            # Store metadata
            img_metadata = {
                'filename': img_filename,
                'path': str(img_path),
                'url': img_url,
                'size': len(response.content),
                'index': img_index
            }
            
            self.downloaded_images[img_url] = img_metadata
            return img_metadata
            
        except Exception as e:
            print(f"      ✗ Failed to download image: {e}")
            return None
    
    def extract_images_from_article(self, soup: BeautifulSoup, article_id: str) -> List[Dict]:
        """
        Extract and download all images from an article
        
        Args:
            soup: BeautifulSoup object
            article_id: Unique article identifier
            
        Returns:
            List of image metadata dictionaries
        """
        images_metadata = []
        
        # Find article content
        content_selectors = [
            'div.entry-content',
            'div.text',
            'article',
            'div.content',
            'div[itemprop="articleBody"]'
        ]
        
        content_div = None
        for selector in content_selectors:
            content_div = soup.select_one(selector)
            if content_div:
                break
        
        if not content_div:
            return images_metadata
        
        # Find all images
        images = content_div.find_all('img')
        
        print(f"      Found {len(images)} images")
        
        for i, img in enumerate(images, 1):
            img_url = img.get('src') or img.get('data-src')
            
            if img_url:
                # Get alt text for context
                alt_text = img.get('alt', '')
                
                # Download image
                img_metadata = self.download_image(img_url, article_id, i)
                
                if img_metadata:
                    img_metadata['alt_text'] = alt_text
                    img_metadata['context'] = self._get_image_context(img)
                    images_metadata.append(img_metadata)
                    print(f"        ✓ Downloaded: {img_metadata['filename']}")
        
        return images_metadata
    
    def _get_image_context(self, img_tag) -> str:
        """Get surrounding text context for an image"""
        context = ""
        
        # Get parent paragraph or div
        parent = img_tag.find_parent(['p', 'div', 'figure'])
        
        if parent:
            # Get text before and after image
            context = parent.get_text(strip=True)[:200]
        
        # Also check for caption
        caption = img_tag.find_next('figcaption')
        if caption:
            context += " | Caption: " + caption.get_text(strip=True)
        
        return context
    
    def scrape_article(self, url: str, title: str) -> Optional[Dict]:
        """
        Scrape a single article with text and images
        
        Args:
            url: Article URL
            title: Article title
            
        Returns:
            Dictionary with article content and images
        """
        try:
            print(f"  Scraping: {title[:50]}...")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Create unique article ID
            article_id = hashlib.md5(url.encode()).hexdigest()[:8]
            
            # Extract text content
            article_content = self._extract_content(soup)
            
            # Extract and download images
            print(f"      Extracting images...")
            images_metadata = self.extract_images_from_article(soup, article_id)
            
            # Extract code examples
            code_examples = self._extract_code_examples(soup)
            
            if article_content:
                return {
                    'article_id': article_id,
                    'title': title,
                    'url': url,
                    'content': article_content,
                    'content_length': len(article_content),
                    'images': images_metadata,
                    'images_count': len(images_metadata),
                    'code_examples': code_examples,
                    'code_examples_count': len(code_examples),
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
                
                if len(text) > 200:
                    content_text = text
                    break
        
        return content_text
    
    def _extract_code_examples(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract code examples from article"""
        code_examples = []
        
        # Find all code blocks
        code_blocks = soup.find_all(['pre', 'code'])
        
        for i, code_block in enumerate(code_blocks, 1):
            code_text = code_block.get_text(strip=True)
            
            # Only include substantial code (more than 2 lines)
            if len(code_text) > 50 and code_text.count('\n') > 1:
                code_examples.append({
                    'index': i,
                    'code': code_text,
                    'language': 'cpp'
                })
        
        return code_examples
    
    def scrape_multiple_articles(self, topics: List[Dict], limit: int = 20) -> List[Dict]:
        """
        Scrape multiple articles with images
        
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
        """Save each article as individual text file with image references"""
        
        for i, article in enumerate(articles, 1):
            safe_title = re.sub(r'[^\w\s-]', '', article['title'])[:50]
            safe_title = re.sub(r'[-\s]+', '_', safe_title)
            filename = f"{i:02d}_{safe_title}.txt"
            
            filepath = self.text_dir / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Title: {article['title']}\n")
                f.write(f"URL: {article['url']}\n")
                f.write(f"Source: {article['source']}\n")
                f.write(f"Course: {article['course']}\n")
                f.write(f"\n{'='*80}\n\n")
                
                # Write content
                f.write(article['content'])
                
                # Write image references
                if article['images']:
                    f.write(f"\n\n{'='*80}\n")
                    f.write(f"IMAGES ({len(article['images'])}):\n")
                    f.write(f"{'='*80}\n\n")
                    
                    for img in article['images']:
                        f.write(f"Image {img['index']}: {img['filename']}\n")
                        f.write(f"  Path: {img['path']}\n")
                        if img.get('alt_text'):
                            f.write(f"  Alt: {img['alt_text']}\n")
                        if img.get('context'):
                            f.write(f"  Context: {img['context'][:100]}...\n")
                        f.write("\n")
                
                # Write code examples
                if article['code_examples']:
                    f.write(f"\n{'='*80}\n")
                    f.write(f"CODE EXAMPLES ({len(article['code_examples'])}):\n")
                    f.write(f"{'='*80}\n\n")
                    
                    for code in article['code_examples']:
                        f.write(f"Example {code['index']}:\n")
                        f.write("```cpp\n")
                        f.write(code['code'])
                        f.write("\n```\n\n")
        
        print(f"✓ Saved {len(articles)} text files to {self.text_dir}")
    
    def print_summary(self, articles: List[Dict]):
        """Print summary of scraped content"""
        total_images = sum(a['images_count'] for a in articles)
        total_code = sum(a['code_examples_count'] for a in articles)
        
        print("\n" + "="*70)
        print("GEEKSFORGEEKS SCRAPING SUMMARY")
        print("="*70)
        print(f"Total articles scraped: {len(articles)}")
        print(f"Total content length: {sum(a['content_length'] for a in articles):,} characters")
        print(f"Total images downloaded: {total_images}")
        print(f"Total code examples: {total_code}")
        print(f"\nImages saved in: {self.images_dir}")
        print("\nArticles:")
        for i, article in enumerate(articles, 1):
            print(f"  {i}. {article['title'][:50]}")
            print(f"      Images: {article['images_count']}, Code: {article['code_examples_count']}")
        print("="*70)


def main():
    """Main function"""
    
    scraper = GeeksForGeeksScraper()
    
    cpp_url = "https://www.geeksforgeeks.org/cpp/c-plus-plus/"
    print("="*70)
    print("GeeksforGeeks C++ Content Scraper (with Images)")
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
    
    # Step 2: Scrape articles with images
    print(f"\nStep 2: Scraping articles with images (limit: 20)...")
    articles = scraper.scrape_multiple_articles(topics, limit=20)
    
    if articles:
        # Step 3: Save data
        print("\nStep 3: Saving data...")
        scraper.save_to_json(articles)
        scraper.save_as_text(articles)
        scraper.print_summary(articles)
        
        print("\n✓ Scraping completed successfully!")
        print(f"\nData saved in: {scraper.output_dir}")
    else:
        print("\n✗ No articles were successfully scraped")


if __name__ == "__main__":
    main()