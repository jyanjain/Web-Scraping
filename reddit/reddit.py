from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import pandas as pd

options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")

driver = webdriver.Chrome(options=options)

driver.get("https://www.reddit.com/r/Python/")


min_posts = 100
unique_post = set()
posts_data = []

while len(unique_post) < min_posts:
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(10)
    articles = driver.find_elements(By.TAG_NAME, "article")
    for article in articles:
        try:
            article.find_element(By.CLASS_NAME, "promoted-name-container")
            continue
        except:
            pass

        try:
            title_element = article.find_element(By.CSS_SELECTOR, 'a[id^="post-title-"]')
            title = title_element.text.strip()
            post_url = title_element.get_attribute("href")
 
            author_element = article.find_element(By.CSS_SELECTOR, 'span[slot="authorName"] a[href^="/user/"]')
            author = author_element.text.strip().split('/')[1]

            post_element = article.find_element(By.TAG_NAME, "shreddit-post")
            upvotes = post_element.get_attribute("score") or "0"
            comments = post_element.get_attribute("comment-count") or "0"


            time_element = article.find_element(By.TAG_NAME, "time")
            time_ = time_element.get_attribute("datetime").split('T')[0] + " - " + time_element.get_attribute("datetime").split('T')[1].split(".")[0]

            posts_data.append({
                "title": title,
                "author": author,
                "upvotes": upvotes,
                "comments": comments,
                "post_url": post_url,
                "post_time": time_
            })
            unique_post.add(post_url)
        
        except Exception as e:
            print(f"Error: {e}")
            continue

df = pd.DataFrame(posts_data)
df.to_csv("reddit_python_data.csv", index=False)

driver.quit()

