from bs4 import BeautifulSoup
import requests
import pandas as pd
import time
import numpy as np 
from datetime import datetime
import csv

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import sqlite3

# email details 
EMAIL_SENDER = ""
EMAIL_PASSWORD = ""
EMAIL_RECEIVER = ""  

# sqlite database 
DB_PATH = "flipkart/flipkart_data.db"
TABLE_NAME = "products"

headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

def clean_price(price):
    if not price:
        return None
    cleaned = price.replace("Â", "").replace("â‚¹", "").replace("₹", "").strip()
    return ''.join(filter(str.isdigit, cleaned)) 

def scrape_details(url):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        product_soup = BeautifulSoup(response.text, "html.parser")

        try:
            title = product_soup.find('span', class_="VU-ZEz").text.strip()
        except:
            title = None

        try:
            current_price = product_soup.find('div', class_="Nx9bqj CxhGGd").text.strip()
        except:
            current_price = None

        try:
            original_price = product_soup.find('div', class_="yRaY8j A6+E6v").text.strip()
        except:
            original_price = None

        try:
            ratings = product_soup.find('div', class_="XQDdHH").text.strip()
        except:
            ratings = None

        try:
            reviews_number = product_soup.find('span', attrs={"class" : "Wphh3N"}).text.split("&")[1]
        except:
            reviews_number = None

        return {
            "Title": title,
            "Current Price": clean_price(current_price) if current_price else None,
            "Original Price": clean_price(original_price) if original_price else None,
            "Ratings": ratings,
            "Number of Reviews": clean_price(reviews_number) if reviews_number else None,
            "Product URL": url
        }

    except Exception as e:
        print(f"Failed to scrape {url}: {e}")
        return None
 
def create_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        "Title" TEXT,
        "Current Price" TEXT,
        "Original Price" TEXT,
        "Old Price" TEXT,
        "Product URL" TEXT PRIMARY KEY,
        "Ratings" TEXT,
        "Number of Reviews" TEXT,
        "Last Seen" TEXT,
        "Price Dropped" TEXT
    )
    """)
    conn.commit()
    conn.close()



def initial_run():
    keyword = "laptop"
    base_url = f"https://www.flipkart.com/search?q={keyword}&otracker=search&otracker1=search&marketplace=FLIPKART&as-show=on&as=off"

    products_link = []
    page = 1

    while len(products_link) < 100:
        url = f"{base_url}&page={page}"

        response = requests.get(url, headers=headers)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.content, "html.parser")

        for link in soup.find_all("a", class_="CGtC98", href=True): # gets link of all the products 
                product_url = "https://www.flipkart.com" + link['href']
                products_link.append(product_url)

        page += 1
        print(len(products_link))



    #for csv ----------------
    products = []

    for product_link in products_link:
        data = scrape_details(product_link)
        if data:
            data["Old Price"] = data["Current Price"]
            data["Last Seen"] = datetime.today().strftime("%Y-%m-%d")
            data["Price Dropped?"] = "No"
            products.append(data)
        time.sleep(2)

    df = pd.DataFrame(products)
    df["Title"] = df["Title"].replace("", np.nan)
    df = df.dropna(subset=['Title'])
    df.to_csv("flipkart/flipkart_data.csv", index=False)



    #for sqlite ------------------
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    for link in products_link:
        data = scrape_details(link)
        if data:
            data["Old Price"] = data["Current Price"]
            data["Last Seen"] = datetime.today().strftime("%Y-%m-%d")
            data["Price Dropped"] = "No"

            placeholders = ', '.join(['?'] * len(data))
            columns = ', '.join([f'"{col}"' for col in data.keys()])  # Properly quote column names
            values = list(data.values())

            try:
                c.execute(f"INSERT OR IGNORE INTO {TABLE_NAME} ({columns}) VALUES ({placeholders})", values)
            except Exception as e:
                print(f"Insert failed: {e}")
        time.sleep(2)

    conn.commit()
    conn.close()


def update_prices():
    today = datetime.today().strftime("%Y-%m-%d")
    
    #for csv --------------------
    updated_data = []
    
    with open("flipkart/flipkart_data.csv", "r", encoding='utf-8') as file:
        reader = csv.DictReader(file)
        old_data = list(reader)

    for row in old_data:
        url = row["Product URL"]
        new_data = scrape_details(url)

        if new_data:
            try:
                old_price = int(''.join(filter(str.isdigit, row["Current Price"] or ""))) if row["Current Price"] else 0
            except:
                old_price = 0

            try:
                new_price = int(''.join(filter(str.isdigit, new_data["Current Price"] or ""))) if new_data["Current Price"] else old_price
            except:
                new_price = old_price

            percentage = ((old_price - new_price) / old_price) * 100 if old_price > 0 else 0
            price_dropped = "Yes" if percentage > 10 else "No"

            if price_dropped == "Yes":
                print(f"{new_data['Title']} ---- Price dropped by {percentage:.2f}%")
                send_email(new_data["Title"], old_price, new_price, url, percentage)

            updated_row = {
                "Title": new_data["Title"],
                "Current Price": new_data["Current Price"],
                "Original Price": new_data["Original Price"],
                "Old Price": row["Current Price"],
                "Product URL": url,
                "Ratings": new_data["Ratings"],
                "Number of Reviews": new_data["Number of Reviews"],
                "Last Seen": today,
                "Price Dropped?": price_dropped
            }
            updated_data.append(updated_row)
        else:
            row["Last Seen"] = today
            row["Price Dropped?"] = "No"
            updated_data.append(row)

    with open("flipkart/flipkart_data.csv", "w", newline='', encoding='utf-8') as file:
        fieldnames = ["Title", "Current Price", "Original Price", "Old Price", "Product URL", "Ratings", "Number of Reviews", "Last Seen", "Price Dropped?"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_data)



    #for sqlite ------------------
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(f"SELECT * FROM {TABLE_NAME}")
    rows = c.fetchall()
    columns = [desc[0] for desc in c.description]

    for row in rows:
        row_data = dict(zip(columns, row))
        url = row_data["Product URL"]
        old_price_str = row_data["Current Price"]
        data = scrape_details(url)

        if data:
            try:
                old_price = int(old_price_str or "0")
                new_price = int(data["Current Price"] or old_price)
            except:
                continue

            drop_percent = ((old_price - new_price) / old_price) * 100 if old_price > 0 else 0
            price_dropped = "Yes" if drop_percent > 10 else "No"

            if price_dropped == "Yes":
                print(f"{data['Title']} dropped by {drop_percent:.2f}%")
                send_email(data["Title"], old_price, new_price, url, drop_percent)

            update_values = (
                data["Current Price"],
                data["Original Price"],
                old_price_str,
                data["Ratings"],
                data["Number of Reviews"],
                datetime.today().strftime("%Y-%m-%d"),
                price_dropped,
                url
            )

            c.execute(f"""
                UPDATE {TABLE_NAME}
                SET
                    "Current Price" = ?,
                    "Original Price" = ?,
                    "Old Price" = ?,
                    "Ratings" = ?,
                    "Number of Reviews" = ?,
                    "Last Seen" = ?,
                    "Price Dropped" = ?
                WHERE "Product URL" = ?
            """, update_values)

    conn.commit()
    conn.close()

def send_email(product_title, old_price, new_price, url, drop_percent):
    subject = f"Price Drop: {product_title}"
    body = f"""
    The price for "{product_title}" dropped by {drop_percent:.2f}%.
    Old Price: ₹{old_price}
    New Price: ₹{new_price}
    Link: {url}

    Buy Now. Its a great deal.
    """

    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
            print(f"Email has been sent")
    except Exception as e:
        print(f"Email has not been sent")


create_table() #just need to run this once to create the table then comment it 

initial_run() #need to run this for getting the data initially 

update_prices() #for price tracking, need to re-run this for updates
