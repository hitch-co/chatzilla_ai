import requests
import numpy as np
from bs4 import BeautifulSoup

from classes.ConsoleColoursClass import bcolors, printc

class ArticleGenerator:
    def __init__(self, rss_link="http://rss.cnn.com/rss/cnn_showbiz.rss"):
        self.rss_link = rss_link
        self.articles = []
        self.article_details = []

    def fetch_articles(self):
        response = requests.get(self.rss_link)
        if response.status_code != 200:
            print("Failed to fetch the RSS feed.")
            return []
        
        soup = BeautifulSoup(response.content, 'xml')
        self.articles = []
        
        for item in soup.find_all('item'):
            article_dict = {
                'title': item.title.string if item.title else "N/A",
                'link': item.link.string if item.link else "N/A",
                'pub_date': item.pubDate.string if item.pubDate else "N/A",
                'description': item.description.string if item.description else "N/A"
            }
            self.articles.append(article_dict)
        printc(f"Successfully fetched: {len(self.articles)} article titles and links", bcolors.FAIL)
        # print(self.articles[:1])
        
        return self.articles


    def fetch_content(self):
        if not self.articles:
            print("Missing URL or article data.")
            return []
        
        for article in self.articles:
            this_article = {}
            full_url = article['link']
            response = requests.get(full_url)
            
            if response.status_code != 200:
                printc(f"Failed to fetch the article at {full_url}.", bcolors.FAIL)
                continue

            soup = BeautifulSoup(response.content, 'html.parser')
            content_html_soup = soup.find('div', {'class': 'article__content'})
            
            if content_html_soup:
                content_text = content_html_soup.get_text()
            else: 
                printc(f"Successfully fetched article at {full_url} but Article contains no content", bcolors.FAIL)
                continue

            this_article['content'] = self.clean_html_text(content_text)
            self.article_details.append(this_article)
            if not self.article_details:
                printc("ERROR: Article details list is empty!", bcolors.FAIL)
        return self.article_details


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

        # Make sure it ends with the last complete sentence.
        sentence_match = re.findall(r'[^.!?]*[.!?]', text)
        if sentence_match:
            text = ''.join(sentence_match)
        elif text and text[-1] not in ".!?":
            text = text + '.'

        return text

    # def fetch_articles_content(self):
    #     self.fetch_articles()
    #     self.fetch_content()

    # def fetch_random_article2(self, trunc_characters_at=1000):
    #     printc('Preview of article_details:', bcolors.FAIL)
    #     print(f"len(article_details):{len(self.article_details)}")
        
    #     #Print statement to view partial articles in console
    #     #for article in self.article_details[:10]:
    #     #    temp_article = {key: (value[:trunc_characters_at] if key == 'content' else value) for key, value in article.items()}
    #     #    printc(f'\nArticle content (truncated):',bcolors.OKBLUE)
    #     #    print(temp_article)
        
    #     random_article_dictionary = np.random.choice(self.article_details)
    #     random_article_dictionary['content'] = random_article_dictionary['content'][:trunc_characters_at]
        
    #     printc(f"\nrandom_article_dictionary 'content' (type: {type(random_article_dictionary)})':",bcolors.FAIL)
    #     print(random_article_dictionary['content'])
        
    #     return random_article_dictionary       

    def fetch_random_article(self, trunc_characters_at=1000):
        self.fetch_articles()
        self.fetch_content()
        
        printc('Preview of article_details:', bcolors.FAIL)
        print(f"len(article_details):{len(self.article_details)}")
        
        #Print statement to view partial articles in console
        #for article in self.article_details[:10]:
        #    temp_article = {key: (value[:trunc_characters_at] if key == 'content' else value) for key, value in article.items()}
        #    printc(f'\nArticle content (truncated):',bcolors.OKBLUE)
        #    print(temp_article)
        
        random_article_dictionary = np.random.choice(self.article_details)
        random_article_dictionary['content'] = random_article_dictionary['content'][:trunc_characters_at]
        
        printc(f"\nrandom_article_dictionary 'content' (type: {type(random_article_dictionary)})':",bcolors.FAIL)
        print(random_article_dictionary['content'])
        
        return random_article_dictionary

def main(rss_link=None):
    article_generator = ArticleGenerator(rss_link=rss_link)
    random_article_dictionary = article_generator.fetch_random_article(trunc_characters_at=500)
    print(random_article_dictionary['content'])

if __name__ == "__main__":
    main(rss_link="http://rss.cnn.com/rss/cnn_showbiz.rss")


# article_generator = ArticleGenerator(rss_link="http://rss.cnn.com/rss/cnn_showbiz.rss")

# articles = article_generator.fetch_articles()
# article_content = article_generator.fetch_content()

