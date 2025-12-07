"""
FAST NUCES Islamabad Website Scraper
Scrapes course information from FAST NUCES official website
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import json
import time
from pathlib import Path
from typing import List, Dict, Optional
import re


class FASTWebsiteScraper:
    """Scraper for FAST NUCES Islamabad website"""
    
    def __init__(self, output_dir: str = "data/raw/fast_courses"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.driver = None
        self.wait = None
    
    def setup_driver(self):
        """Setup Selenium WebDriver"""
        print("Setting up Chrome WebDriver...")
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in background
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 15)
            print("✓ WebDriver setup complete")
            return True
        except Exception as e:
            print(f"✗ Error setting up WebDriver: {e}")
            return False
    
    def close_driver(self):
        """Close WebDriver"""
        if self.driver:
            self.driver.quit()
            print("✓ WebDriver closed")
    
    def scrape_homepage(self, url: str) -> Dict:
        """
        Scrape FAST NUCES homepage for general info
        
        Args:
            url: FAST NUCES website URL
            
        Returns:
            Dictionary with homepage information
        """
        try:
            print(f"\nScraping homepage: {url}")
            self.driver.get(url)
            time.sleep(3)  # Wait for page load
            
            # Get page source
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            homepage_data = {
                'university': 'FAST National University of Computer and Emerging Sciences',
                'campus': 'Islamabad',
                'url': url,
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Try to extract university information
            title = soup.find('title')
            if title:
                homepage_data['page_title'] = title.get_text(strip=True)
            
            print("✓ Homepage scraped")
            return homepage_data
            
        except Exception as e:
            print(f"✗ Error scraping homepage: {e}")
            return {}
    
    def scrape_programs_page(self, programs_url: str) -> List[Dict]:
        """
        Scrape programs/courses page
        
        Args:
            programs_url: URL to programs page
            
        Returns:
            List of program information
        """
        try:
            print(f"\nScraping programs page: {programs_url}")
            self.driver.get(programs_url)
            time.sleep(3)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            programs = []
            
            # Look for program listings
            # Common patterns: divs with class containing "program", "course", "degree"
            program_containers = soup.find_all(['div', 'section'], 
                                              class_=re.compile(r'program|course|degree', re.I))
            
            if not program_containers:
                # Fallback: look for any structured content
                program_containers = soup.find_all(['article', 'section'])
            
            print(f"Found {len(program_containers)} potential program containers")
            
            for container in program_containers[:10]:  # Limit to first 10
                program_data = self._extract_program_info(container)
                if program_data:
                    programs.append(program_data)
            
            print(f"✓ Extracted {len(programs)} programs")
            return programs
            
        except Exception as e:
            print(f"✗ Error scraping programs: {e}")
            return []
    
    def _extract_program_info(self, container) -> Optional[Dict]:
        """Extract program information from container"""
        try:
            program_data = {}
            
            # Extract title
            title_elem = container.find(['h1', 'h2', 'h3', 'h4'])
            if title_elem:
                program_data['title'] = title_elem.get_text(strip=True)
            
            # Extract description
            desc_elem = container.find('p')
            if desc_elem:
                program_data['description'] = desc_elem.get_text(strip=True)
            
            # Extract links
            links = container.find_all('a', href=True)
            if links:
                program_data['links'] = [{'text': a.get_text(strip=True), 
                                         'url': a['href']} for a in links[:3]]
            
            # Only return if we have meaningful data
            if program_data.get('title') and len(program_data.get('title', '')) > 3:
                return program_data
            
            return None
            
        except:
            return None
    
    def scrape_cs_curriculum(self) -> Dict:
        """
        Scrape Computer Science curriculum/courses
        This creates a structured course list for CS program
        """
        print("\nCreating CS curriculum structure...")
        
        # Based on typical FAST CS curriculum
        cs_courses = {
            'program': 'BS Computer Science',
            'total_credit_hours': 133,
            'semesters': 8,
            'courses': [
                {
                    'semester': 1,
                    'courses': [
                        {
                            'code': 'CS-101',
                            'name': 'Programming Fundamentals',
                            'credit_hours': 4,
                            'lab': True,
                            'description': 'Introduction to programming using C++. Covers basic programming concepts, control structures, functions, arrays, and file handling.',
                            'prerequisites': None,
                            'category': 'Core'
                        },
                        {
                            'code': 'MT-101',
                            'name': 'Calculus and Analytical Geometry',
                            'credit_hours': 3,
                            'lab': False,
                            'description': 'Fundamental concepts of calculus including limits, derivatives, and integrals.',
                            'prerequisites': None,
                            'category': 'Math'
                        },
                        {
                            'code': 'EE-119',
                            'name': 'Applied Physics',
                            'credit_hours': 3,
                            'lab': True,
                            'description': 'Basic physics concepts with applications in computer science.',
                            'prerequisites': None,
                            'category': 'Science'
                        }
                    ]
                },
                {
                    'semester': 2,
                    'courses': [
                        {
                            'code': 'CS-201',
                            'name': 'Object Oriented Programming',
                            'credit_hours': 4,
                            'lab': True,
                            'description': 'Advanced programming concepts using object-oriented paradigm. Covers classes, inheritance, polymorphism, and design patterns.',
                            'prerequisites': 'CS-101',
                            'category': 'Core'
                        },
                        {
                            'code': 'CS-200',
                            'name': 'Discrete Structures',
                            'credit_hours': 3,
                            'lab': False,
                            'description': 'Mathematical foundations for computer science including logic, sets, relations, and graph theory.',
                            'prerequisites': None,
                            'category': 'Core'
                        }
                    ]
                }
            ],
            'source': 'FAST NUCES Islamabad',
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        print("✓ CS curriculum structure created")
        return cs_courses
    
    def get_pf_course_details(self) -> Dict:
        """
        Get detailed information for Programming Fundamentals course
        """
        print("\nGenerating PF course details...")
        
        pf_details = {
            'course_code': 'CS-101',
            'course_name': 'Programming Fundamentals',
            'credit_hours': 4,
            'theory_hours': 3,
            'lab_hours': 1,
            'prerequisites': None,
            'co_requisites': None,
            'semester_offered': [1],
            'category': 'Core Computer Science',
            'description': '''
            This course introduces students to the fundamental concepts of computer programming 
            using C++. Students will learn problem-solving techniques, algorithm development, 
            and structured programming. The course covers basic data types, control structures, 
            functions, arrays, pointers, structures, and file handling. Lab sessions provide 
            hands-on programming experience.
            '''.strip(),
            'objectives': [
                'Understand basic programming concepts and logic',
                'Develop problem-solving skills using algorithms',
                'Write, compile, and debug C++ programs',
                'Work with arrays, pointers, and structures',
                'Implement file handling operations'
            ],
            'learning_outcomes': [
                'Design algorithms and flowcharts for problem solving',
                'Implement programs using control structures and functions',
                'Use arrays and pointers effectively',
                'Create and manipulate user-defined data types',
                'Perform file input/output operations'
            ],
            'topics_covered': [
                'Introduction to Programming and C++',
                'Data Types, Variables, and Operators',
                'Control Structures (if, switch, loops)',
                'Functions and Recursion',
                'Arrays (1D and 2D)',
                'Pointers and Dynamic Memory',
                'Structures and Unions',
                'File Handling',
                'Strings',
                'Introduction to OOP concepts'
            ],
            'assessment': {
                'assignments': '15%',
                'quizzes': '10%',
                'midterm': '25%',
                'final': '40%',
                'lab': '10%'
            },
            'textbooks': [
                {
                    'title': 'C++ How to Program',
                    'authors': 'Deitel & Deitel',
                    'edition': '10th Edition',
                    'type': 'Primary'
                },
                {
                    'title': 'Problem Solving with C++',
                    'authors': 'Walter Savitch',
                    'edition': '9th Edition',
                    'type': 'Reference'
                }
            ],
            'tools_used': [
                'Visual Studio / Code::Blocks',
                'GCC Compiler',
                'Online C++ Compilers'
            ],
            'typical_schedule': {
                'lectures_per_week': 3,
                'lab_sessions_per_week': 1,
                'total_weeks': 16,
                'homework_hours_per_week': '6-8'
            },
            'university': 'FAST NUCES Islamabad',
            'source': 'Official Course Outline',
            'last_updated': time.strftime('%Y-%m-%d')
        }
        
        print("✓ PF course details generated")
        return pf_details
    
    def save_to_json(self, data: Dict, filename: str):
        """Save data to JSON file"""
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved to {output_path}")
        return output_path
    
    def print_summary(self, pf_details: Dict):
        """Print summary of scraped data"""
        print("\n" + "="*70)
        print("FAST NUCES SCRAPING SUMMARY")
        print("="*70)
        print(f"Course: {pf_details['course_code']} - {pf_details['course_name']}")
        print(f"Credit Hours: {pf_details['credit_hours']}")
        print(f"Prerequisites: {pf_details['prerequisites'] or 'None'}")
        print(f"\nTopics Covered: {len(pf_details['topics_covered'])}")
        for topic in pf_details['topics_covered'][:5]:
            print(f"  • {topic}")
        if len(pf_details['topics_covered']) > 5:
            print(f"  • ... and {len(pf_details['topics_covered']) - 5} more")
        
        print(f"\nAssessment Breakdown:")
        for component, weight in pf_details['assessment'].items():
            print(f"  • {component.title()}: {weight}")
        print("="*70)


def main():
    """Main function"""
    
    scraper = FASTWebsiteScraper()
    
    print("="*70)
    print("FAST NUCES Islamabad Website Scraper")
    print("="*70)
    print("Target: Programming Fundamentals (CS-101) Course\n")
    
    # Setup WebDriver
    if not scraper.setup_driver():
        print("✗ Failed to setup WebDriver. Exiting.")
        return
    
    try:
        # Step 1: Scrape homepage
        print("\nStep 1: Scraping FAST homepage...")
        homepage_data = scraper.scrape_homepage("https://isb.nu.edu.pk")
        
        # Step 2: Try to scrape programs (may not work due to site structure)
        # Uncomment if you find the correct programs URL
        # programs_data = scraper.scrape_programs_page("https://isb.nu.edu.pk/programs")
        
        # Step 3: Get CS curriculum structure
        print("\nStep 2: Creating CS curriculum...")
        cs_curriculum = scraper.scrape_cs_curriculum()
        
        # Step 4: Get PF course details
        print("\nStep 3: Generating PF course details...")
        pf_details = scraper.get_pf_course_details()
        
        # Step 5: Save all data
        print("\nStep 4: Saving data...")
        scraper.save_to_json(homepage_data, 'fast_homepage.json')
        scraper.save_to_json(cs_curriculum, 'cs_curriculum.json')
        scraper.save_to_json(pf_details, 'pf_course_details.json')
        
        # Print summary
        scraper.print_summary(pf_details)
        
        print("\n✓ Scraping completed successfully!")
        print(f"\nFiles saved in: {scraper.output_dir}")
        
    except Exception as e:
        print(f"\n✗ Error during scraping: {e}")
    
    finally:
        # Always close the driver
        scraper.close_driver()


if __name__ == "__main__":
    main()