import requests
from bs4 import BeautifulSoup

def crawl_wikipedia():
    url = "https://en.wikipedia.org/wiki/Natural_language_processing"
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()
        return text[:1000]  # Return only first 1000 characters for preview
    except Exception as e:
        print(f"Error fetching Wikipedia data: {e}")
        return None

if __name__ == "__main__":
    data = crawl_wikipedia()
    if data:
        print("Extracted Wikipedia Data:", data)