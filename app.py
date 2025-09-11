import streamlit as st
import requests
from bs4 import BeautifulSoup
import time

st.set_page_config(page_title="NSE Option Chain Scraper", layout="wide")
st.title("📄 NSE Option Chain HTML Scraper (Basic)")

def scrape_option_chain_html(symbol="NIFTY"):
    url = f"https://www.nseindia.com/option-chain?symbol={symbol}"
    headers = {
        "User -Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com"
    }
    session = requests.Session()
    try:
        # First request to get cookies
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        time.sleep(1)  # polite delay
        response = session.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        return response.text
    except Exception as e:
        st.error(f"Failed to fetch NSE option chain page: {e}")
        return None

symbol = st.sidebar.selectbox("Select Symbol", ["NIFTY", "BANKNIFTY"])
if st.sidebar.button("Fetch Option Chain HTML"):
    html = scrape_option_chain_html(symbol)
    if html:
        st.success(f"Fetched NSE option chain page HTML for {symbol} (length: {len(html)} characters)")
        # Show page title as a simple check
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string if soup.title else "No title found"
        st.write(f"Page Title: {title}")

        # Example: Show first 1000 characters of HTML
        st.code(html[:1000], language="html")

        # TODO: You can add parsing logic here to extract data from HTML if possible
    else:
        st.error("Failed to fetch or parse NSE option chain page.")
