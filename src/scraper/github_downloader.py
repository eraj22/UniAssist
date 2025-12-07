"""
GitHub Past Papers Downloader
Downloads PF past papers from FAST NUCES GitHub repository
"""

import requests
import json
from pathlib import Path
from typing import List, Dict
import time
import re


class GitHubPastPapersDownloader:
    """Download past papers from GitHub repository"""
    
    def __init__(self, output_dir: str = "data/raw/past_papers"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_repo_contents(self, api_url: str) -> List[Dict]:
        """
        Get contents of a GitHub directory using API
        
        Args:
            api_url: GitHub API URL for the directory
            
        Returns:
            List of file information dictionaries
        """
        try:
            print(f"Fetching repository contents...")
            response = self.session.get(api_url, timeout=15)
            response.raise_for_status()
            
            contents = response.json()
            
            if isinstance(contents, list):
                print(f"✓ Found {len(contents)} items")
                return contents
            else:
                print("✗ Unexpected response format")
                return []
                
        except Exception as e:
            print(f"✗ Error fetching repo contents: {e}")
            return []
    
    def download_file(self, file_info: Dict) -> bool:
        """
        Download a single file from GitHub
        
        Args:
            file_info: Dictionary with file information from GitHub API
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_name = file_info['name']
            download_url = file_info['download_url']
            
            print(f"  Downloading: {file_name}")
            
            response = self.session.get(download_url, timeout=30)
            response.raise_for_status()
            
            # Save file
            output_path = self.output_dir / file_name
            
            # Handle binary files (PDFs, images)
            with open(output_path, 'wb') as f:
                f.write(response.content)
            
            print(f"    ✓ Saved to {output_path}")
            return True
            
        except Exception as e:
            print(f"    ✗ Error downloading {file_info.get('name', 'unknown')}: {e}")
            return False
    
    def download_all_papers(self, contents: List[Dict]) -> Dict:
        """
        Download all past paper files
        
        Args:
            contents: List of file information from GitHub
            
        Returns:
            Summary dictionary
        """
        stats = {
            'total': 0,
            'downloaded': 0,
            'failed': 0,
            'pdf_files': [],
            'other_files': []
        }
        
        for item in contents:
            if item['type'] == 'file':
                stats['total'] += 1
                
                # Check file extension
                file_name = item['name']
                file_ext = Path(file_name).suffix.lower()
                
                if file_ext in ['.pdf', '.docx', '.doc', '.txt', '.md']:
                    success = self.download_file(item)
                    
                    if success:
                        stats['downloaded'] += 1
                        if file_ext == '.pdf':
                            stats['pdf_files'].append(file_name)
                        else:
                            stats['other_files'].append(file_name)
                    else:
                        stats['failed'] += 1
                    
                    # Be polite - wait between downloads
                    time.sleep(1)
        
        return stats
    
    def create_metadata(self, stats: Dict):
        """Create metadata file for downloaded papers"""
        metadata = {
            'source': 'GitHub - FAST NUCES Islamabad Past Papers',
            'course': 'Programming Fundamentals (PF)',
            'semester': 'Semester 1',
            'download_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'statistics': {
                'total_files': stats['total'],
                'downloaded': stats['downloaded'],
                'failed': stats['failed']
            },
            'files': {
                'pdf_papers': stats['pdf_files'],
                'other_files': stats['other_files']
            }
        }
        
        metadata_path = self.output_dir / 'metadata.json'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Metadata saved to {metadata_path}")
    
    def print_summary(self, stats: Dict):
        """Print download summary"""
        print("\n" + "="*70)
        print("GITHUB DOWNLOAD SUMMARY")
        print("="*70)
        print(f"Total files found: {stats['total']}")
        print(f"Successfully downloaded: {stats['downloaded']}")
        print(f"Failed downloads: {stats['failed']}")
        print(f"\nPDF Papers: {len(stats['pdf_files'])}")
        for pdf in stats['pdf_files']:
            print(f"  • {pdf}")
        
        if stats['other_files']:
            print(f"\nOther Files: {len(stats['other_files'])}")
            for file in stats['other_files']:
                print(f"  • {file}")
        print("="*70)


def main():
    """Main function"""
    
    downloader = GitHubPastPapersDownloader()
    
    # GitHub API URL for the PF past papers directory
    # Convert: https://github.com/nuces-isb-past-papers/fsc-past-papers/tree/main/semester-1/PF
    # To API: https://api.github.com/repos/nuces-isb-past-papers/fsc-past-papers/contents/semester-1/PF
    
    github_api_url = "https://api.github.com/repos/nuces-isb-past-papers/fsc-past-papers/contents/semester-1/PF"
    
    print("="*70)
    print("GitHub Past Papers Downloader")
    print("="*70)
    print(f"Repository: FAST NUCES Islamabad")
    print(f"Course: Programming Fundamentals (PF)")
    print(f"Target: {github_api_url}\n")
    
    # Step 1: Get repository contents
    print("Step 1: Fetching repository contents...")
    contents = downloader.get_repo_contents(github_api_url)
    
    if not contents:
        print("\n✗ No files found or error occurred")
        return
    
    # Step 2: Download files
    print(f"\nStep 2: Downloading {len(contents)} files...")
    stats = downloader.download_all_papers(contents)
    
    # Step 3: Create metadata and summary
    if stats['downloaded'] > 0:
        print("\nStep 3: Creating metadata...")
        downloader.create_metadata(stats)
        downloader.print_summary(stats)
        print("\n✓ Download completed successfully!")
    else:
        print("\n✗ No files were successfully downloaded")


if __name__ == "__main__":
    main()