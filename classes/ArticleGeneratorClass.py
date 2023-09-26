#USAGE EXAMPLE
# #Run the article through the summarizer()
# rss_link = "http://rss.cnn.com/rss/cnn_showbiz.rss"
# article_generator = ArticleGenerator(rss_link="http://rss.cnn.com/rss/cnn_showbiz.rss")

# random_article_dictionary = article_generator.fetch_random_article(trunc_characters_at=500)

# print(random_article_dictionary['content'])

import requests
import numpy as np
from bs4 import BeautifulSoup

class ArticleGenerator:
    def __init__(self, rss_link="http://rss.cnn.com/rss/cnn_showbiz.rss"):
        self.rss_link = rss_link
        self.articles = []

    def fetch_articles(self):
        self.rss_link
        import requests
        from bs4 import BeautifulSoup
        
        response = requests.get(self.rss_link)
        if response.status_code != 200:
            print("Failed to fetch the RSS feed.")
            return []
        
        soup = BeautifulSoup(response.content, 'xml')
        self.articles = []
        
        for item in soup.find_all('item'):
            article_dict = {}
            title = item.title.string if item.title else "N/A"
            link = item.link.string if item.link else "N/A"
            pub_date = item.pubDate.string if item.pubDate else "N/A"
            description = item.description.string if item.description else "N/A"
            
            article_dict["title"] = title
            article_dict["link"] = link
            article_dict["pub_date"] = pub_date
            article_dict["description"] = description        
            self.articles.append(article_dict)
            
        return self.articles



    def clean_html_text(self, text):
        import re

        # Remove HTML tags
        text = re.sub(r'<.*?>', ' ', text)
        
        # Replace common HTML character codes
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&lt;', '<', text)
        text = re.sub(r'&gt;', '>', text)
        text = re.sub(r'&quot;', '"', text)
        
        # Remove or replace special characters like '\t', '\r', '\xa0', etc.
        text = re.sub(r'[\t\r\xa0]', ' ', text)

        # Remove multiple spaces with a single space
        text = re.sub(r'\s+', ' ', text).strip()

        # Remove any leading or trailing spaces
        text = text.strip()

        # Remove multiple spaces but keep single '\n'
        text = re.sub(r'(?<!\n) +', ' ', text)
        text = re.sub(r' +(?!\n)', ' ', text)
        
        # Remove any leading or trailing spaces but keep leading or trailing newlines
        text = text.strip(' ')

        # Remove multiple spaces but keep single '\n'
        text = re.sub(r'(?<!\n) +', ' ', text)
        text = re.sub(r' +(?!\n)', ' ', text)

        # Remove any leading or trailing spaces but keep leading or trailing newlines
        text = text.strip(' ')

        return text



    def fetch_content(self):
        import requests
        from bs4 import BeautifulSoup

        # Check if both parameters are provided
        if not self.articles:
            print("Missing URL or article data.")
            return []
        
        # Initialize an empty list to hold the dictionaries with article details
        article_details = []
        
        # Loop through each dictionary in the list
        for article in self.articles:
            # Initialize a new dictionary to hold this article's details
            this_article = {}
            
            # The URL is already absolute in your data structure
            full_url = article['link']
            
            # Perform the GET request for each URL
            response = requests.get(full_url)
            if response.status_code != 200:
                print(f"Failed to fetch the article at {full_url}.")
                continue
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # The title is already in your data structure
            this_article['title'] = article['title']
            
            # Here, you'll need to inspect the CNN article's HTML to identify the correct tag and class
            # that holds the article text. In this example, I've used placeholders.
            content_html_text = soup.find('div', {'class': 'article__content'})

            content_text_clean = self.clean_html_text(content_html_text.get_text())

            if content_text_clean:
                this_article['content'] = content_text_clean
            else:
                this_article['content'] = "Could not retrieve content."
                
            this_article['url'] = full_url
            article_details.append(this_article)
        
        return article_details


    def fetch_random_article(self,
                             trunc_characters_at=100):
        #News stuff
        ##################################################################
        import numpy as np
        import time

        #get article details from some site
        article_title_and_links = self.fetch_articles()
        article_details = self.fetch_content()

        #select the article you wish you use
        random_article_dictionary = np.random.choice(article_details)
        random_article_dictionary['content'] = random_article_dictionary['content'][:trunc_characters_at]

        #Print details
        print(f"URL: {random_article_dictionary['url']}\nTitle: {random_article_dictionary['title']}\nchar_length: {len(random_article_dictionary['content'])}\n\n")

        return random_article_dictionary