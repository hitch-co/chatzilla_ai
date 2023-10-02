from modules import openai_gpt_chatcompletion
from classes.ArticleGeneratorClass import ArticleGenerator
import os
from modules import load_env, load_yaml

def get_random_rss_article_summary_prompt(newsarticle_rss_feed = 'http://rss.cnn.com/rss/cnn_showbiz.rss',
                                          summary_prompt = 'none',
                                          OPENAI_API_KEY = None):
    
    #Grab a random article                
    article_generator = ArticleGenerator(rss_link=newsarticle_rss_feed)
    random_article_dictionary = article_generator.fetch_random_article(trunc_characters_at=500)
    rss_article_content = random_article_dictionary['content']

    #replace ouat_news_article_summary_prompt placeholder params
    params = {"rss_article_content":rss_article_content}
    random_article_content_prompt = summary_prompt.format(**params)

    #Final prompt dict submitted to GPT
    gpt_prompt_dict = [{'role': 'system', 'content': random_article_content_prompt}]

    print("gpt_prompt_dict")
    print(gpt_prompt_dict)
    random_article_content_prompt_summary = openai_gpt_chatcompletion(gpt_prompt_dict, OPENAI_API_KEY=OPENAI_API_KEY)
    
    return random_article_content_prompt_summary

if __name__ == '__main__':
    yaml_data = load_yaml(yaml_dirname='config')
    load_env(env_dirname='config')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

    #test1 -- get_random_rss_article_summary_prompt
    summary_prompt = yaml_data['ouat_news_article_summary_prompt']
    response = get_random_rss_article_summary_prompt(newsarticle_rss_feed='http://rss.cnn.com/rss/cnn_showbiz.rss',
                                                    summary_prompt=summary_prompt,
                                                    OPENAI_API_KEY=OPENAI_API_KEY)
    print(response)