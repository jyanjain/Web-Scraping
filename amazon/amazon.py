from bs4 import BeautifulSoup
import requests
import pandas as pd
import numpy as np
from urllib.parse import urljoin

keyword = "Shirts"
pages = 2
urls = []

for i in range(1, pages+1):
    urls.append(f"https://www.amazon.in/s?k={keyword}&page={i}")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
}

data = {
        'Product Title' : [],
        "Price" : [],
        'Ratings' : [],
        "Number of Reviews" : [],
        'Prime Eligibility' : [],
        "Product URL" : [],
        "Sizes" : [],
    }

for url in urls:
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")

    product_urls = soup.find_all("a", attrs={'class': 'a-link-normal s-underline-text s-underline-link-text s-link-style'})

    links = []
    for link in product_urls: # gets all the link of products
        links.append(link.get("href"))

    for link in links: # iterate each link 
        product = urljoin("https://www.amazon.in", link)

        product_webpage = requests.get(product, headers=headers)

        product_soup = BeautifulSoup(product_webpage.content, "html.parser")

        try:
            title = product_soup.find("span", attrs={'id': 'productTitle'}).text.strip()
        except:
            print("Couldn't find title of the product")
            title = ""

        try:
            price = product_soup.find("span", attrs={'class': 'a-price-whole'}).text.strip()
        except:
            print("Couldn't find price of the product")
            price = ""

        try:
            ratings = product_soup.find("span", attrs={'class': 'a-icon-alt'}).text
        except:
            print("Couldn't find Rating of the product")
            ratings = ""

        try:
            reviews_number = product_soup.find("span", attrs={'id': 'acrCustomerReviewText'}).text.strip()
        except:
            print("Couldn't find Reviews Number of the product")
            reviews_number = ""

        try:
            size_list = [] # two ways are present for sizes 

            span_sizes = product_soup.find_all(
                "span",
                class_=lambda c: c and (
                    "swatch-title-text-display" in c and 
                    ("swatch-title-text" in c or "swatch-title-text-single-line" in c)
                )
            ) # if the sizes are present in blocks 
            
            for size in span_sizes:
                text = size.get_text(strip=True)
                if text and text.lower() != "select":
                    size_list.append(text)

            if not size_list:  # if the sizes are present in dropdown menu 
                select = product_soup.find("select", {"name": "dropdown_selected_size_name"})
                if select:
                    options = select.find_all("option")
                    for option in options:
                        text = option.get_text(strip=True)
                        if text.lower() != "select":
                            size_list.append(text)

        except Exception as e:
            print("Couldn't find sizes of the product:", str(e))
            size_list = []

        try:
            prime = product_soup.find("span", attrs={'id': 'dealBadgeSupportingText'}).text.strip()
            if prime=="With Prime":
                eligibilty = "Yes" 
        except:
            eligibilty = "No"

        data["Product Title"].append(title)
        data["Price"].append(price)
        data["Ratings"].append(ratings)
        data["Number of Reviews"].append(reviews_number)
        data["Prime Eligibility"].append(eligibilty)
        data["Product URL"].append(product)
        data["Sizes"].append(size_list)

    amazon_data = pd.DataFrame.from_dict(data)

    amazon_data["Product Title"] = amazon_data["Product Title"].replace("", np.nan)
    amazon_data = amazon_data.dropna(subset=['Product Title'])

    amazon_data.to_csv("amazon/amazon_data.csv", index=False, header=True)