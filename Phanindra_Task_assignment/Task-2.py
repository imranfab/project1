import pandas as pd
from huggingface_hub import HfApi
import requests
import json
import os
import time
from bs4 import BeautifulSoup
import re

def fetch_models_from_api(limit=100, filter_task=None):
    """
    Fetch models from Hugging Face Hub using the official API.
    
    Parameters:
    - limit: Maximum number of models to fetch
    - filter_task: Specific NLP task to filter models (e.g., "text-classification")
    
    Returns:
    - List of model dictionaries
    """
    print(f"Fetching up to {limit} models from Hugging Face Hub...")
    
    # Initialize the Hugging Face API client
    api = HfApi()
    
    # Fetch models from the Hub
    models = api.list_models(
        filter=filter_task,
        limit=limit,
        sort="downloads",
        direction=-1  # Sort in descending order by downloads
    )
    
    # Process the models data
    all_models = []
    for model in models:
        model_data = {
            "id": model.id,
            "model_name": model.modelId,
            "author": model.author,
            "downloads": model.downloads,
            "likes": model.likes,
            "tags": model.tags,
            "pipeline_tag": model.pipeline_tag,
            "last_modified": str(model.lastModified) if model.lastModified else None,
            "model_link": f"https://huggingface.co/{model.id}",
            "description": None,  # Will be populated later
        }
        all_models.append(model_data)
    
    return all_models

def fetch_model_descriptions(models, max_models=100):
    """
    Fetch descriptions for each model using multiple methods:
    1. Try to fetch from API
    2. Scrape the model page with various selectors
    
    Parameters:
    - models: List of model dictionaries
    - max_models: Maximum number of models to fetch descriptions for
    
    Returns:
    - Updated list of model dictionaries with descriptions
    """
    print(f"Fetching descriptions for up to {max_models} models...")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    processed_models = []
    for i, model in enumerate(models[:max_models]):
        try:
            
            # Method 1: Try to fetch card data from API
            card_url = f"https://huggingface.co/api/models/{model['id']}"
            try:
                card_response = requests.get(card_url, headers=headers)
                if card_response.status_code == 200:
                    card_data = card_response.json()
                    model['cardData'] = card_data
                    
                    # Extract description from card data
                    if 'cardData' in card_data and card_data['cardData'] and 'description' in card_data['cardData']:
                        model['description'] = card_data['cardData']['description']
                    elif 'description' in card_data:
                        model['description'] = card_data['description']
            except Exception as card_error:
                print(f"Error fetching card data for {model['id']}: {str(card_error)}")
            
            # If we still don't have a description, try scraping the page
            if not model['description']:
                # Method 2: Scrape the model page
                page_response = requests.get(model['model_link'], headers=headers)
                if page_response.status_code == 200:
                    soup = BeautifulSoup(page_response.text, 'html.parser')
                    
                    # Try multiple selectors to find the description
                    description = None
                    
                    # Try to find README content
                    readme_section = soup.find('div', {'id': 'repo-content-pjax-container'})
                    if readme_section:
                        paragraphs = readme_section.find_all('p')
                        if paragraphs:
                            description = paragraphs[0].get_text(strip=True)
                    
                    # Try to find article content
                    if not description:
                        article = soup.find('article')
                        if article:
                            paragraphs = article.find_all('p')
                            if paragraphs:
                                description = paragraphs[0].get_text(strip=True)
                    
                    # Try to find any div with markdown content
                    if not description:
                        markdown_divs = soup.find_all('div', class_=lambda c: c and ('markdown' in c or 'prose' in c))
                        for div in markdown_divs:
                            paragraphs = div.find_all('p')
                            if paragraphs:
                                description = paragraphs[0].get_text(strip=True)
                                break
                                
                    # Final attempt: check meta description
                    if not description:
                        meta_desc = soup.find('meta', {'name': 'description'})
                        if meta_desc and 'content' in meta_desc.attrs:
                            description = meta_desc['content']
                    
                    if description:
                        # Clean up the description
                        description = re.sub(r'\s+', ' ', description).strip()
                        model['description'] = description
            
            processed_models.append(model)
            
            # Add a delay to be respectful to the server
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing model {model['id']}: {str(e)}")
            # Still add the model even if there was an error
            processed_models.append(model)
    
    return processed_models

def filter_nlp_models(models):
    """Filter models to include only NLP-related ones."""
    nlp_tags = [
        "text-classification", "text-generation", "summarization", 
        "translation", "question-answering", "text2text-generation",
        "fill-mask", "sentence-similarity", "token-classification",
        "zero-shot-classification", "text-to-speech", "feature-extraction",
        "conversational", "transformers", "gpt", "bert", "llm", "natural-language-processing"
    ]
    
    filtered_models = []
    for model in models:
        # Check if any tag is NLP-related
        if any(tag.lower() in nlp_tags or any(nlp_tag in tag.lower() for nlp_tag in nlp_tags) 
               for tag in model["tags"] if isinstance(tag, str)):
            filtered_models.append(model)
        # Also check pipeline_tag
        elif model["pipeline_tag"] and any(nlp_tag in model["pipeline_tag"].lower() for nlp_tag in nlp_tags):
            filtered_models.append(model)
    
    return filtered_models

def save_data(data, format="json"):
    """Save the extracted data in the specified format."""
    if not data:
        print("No data to save.")
        return
    
    # Create a directory for the output if it doesn't exist
    if not os.path.exists("output"):
        os.makedirs("output")
    
    # Clean up the data before saving
    data_to_save = []
    for item in data:
        # Create a copy to avoid modifying the original
        clean_item = item.copy()
        # Remove cardData to avoid saving huge amounts of data
        if 'cardData' in clean_item:
            del clean_item['cardData']
        data_to_save.append(clean_item)
    
    if format.lower() == "json":
        with open("output/huggingface_nlp_models.json", "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        print("Data saved to output/huggingface_nlp_models.json")
        
    elif format.lower() == "csv":
        # Convert the list of dictionaries to a DataFrame
        df = pd.DataFrame(data_to_save)
        # Convert lists to strings for CSV format
        for col in df.columns:
            if df[col].apply(lambda x: isinstance(x, list)).any():
                df[col] = df[col].apply(lambda x: ', '.join(x) if isinstance(x, list) else x)
        
        df.to_csv("output/huggingface_nlp_models.csv", index=False, encoding="utf-8")
        print("Data saved to output/huggingface_nlp_models.csv")
    
    else:
        print(f"Unsupported format: {format}")

def main():
    """Main function to fetch and process models."""
    # Fetch models from the API
    all_models = fetch_models_from_api(limit=500)  # Get 500 models
    print(f"Fetched {len(all_models)} models from the Hugging Face Hub.")
    
    # Filter for NLP-related models
    nlp_models = filter_nlp_models(all_models)
    print(f"Found {len(nlp_models)} NLP-related models.")
    
    # Fetch descriptions for a subset of models (to be mindful of rate limits)
    nlp_models_with_descriptions = fetch_model_descriptions(nlp_models, max_models=100)
    print(f"Added descriptions to {len(nlp_models_with_descriptions)} models.")
    
    # Save the data
    save_data(nlp_models_with_descriptions, format="json")
    save_data(nlp_models_with_descriptions, format="csv")
    
    print("Process completed successfully.")

if __name__ == "__main__":
    main()