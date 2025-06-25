from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import pandas as pd

search_queries = ["Python Tutorial", "AI", "Agents"]
max_videos = 50

options = Options()
options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--log-level=3")

results = []

try:
    driver = webdriver.Chrome(options=options)

    for search_query in search_queries:
        url = f"https://www.youtube.com/results?search_query={search_query}"
        driver.get(url)
        time.sleep(3)

        while len(driver.find_elements("id", "video-title")) < max_videos:
            driver.execute_script("window.scrollTo(0, document.documentElement.scrollHeight);")
            time.sleep(2)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        video_blocks = soup.select("ytd-video-renderer")

        for block in video_blocks:
            a_tag = block.select_one('a#video-title')
            title = a_tag['title'] if a_tag else ''
            video_url = "https://www.youtube.com" + a_tag['href'] if a_tag else ''

            channel_tag = block.select_one('a.yt-simple-endpoint.style-scope.yt-formatted-string')
            channel_name = channel_tag.text.strip() if channel_tag else ''

            metadata_items = block.select('span.inline-metadata-item')
            views = metadata_items[0].text.strip() if len(metadata_items) > 0 else ''
            upload_date = metadata_items[1].text.strip() if len(metadata_items) > 1 else ''

            results.append({
                'Title': title,
                'Channel': channel_name,
                'Views': views,
                'Uploaded': upload_date,
                'URL': video_url
            })

finally:
    driver.quit()

df = pd.DataFrame(results)
df.to_csv("youtube/youtube_data.csv", index=False)
print(df.head())
