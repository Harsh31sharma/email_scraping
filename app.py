import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from bs4 import BeautifulSoup
import urllib.parse
import re
import time
import random

# --- Function to generate a dynamic Google Search URL ---
def generate_search_url(employment_type, business_type, city=None):
    query_parts = ['site:linkedin.com/in', '"gmail.com"']
    
    if employment_type:
        query_parts.append(f'"{employment_type}"')
    if business_type:
        query_parts.append(f'"{business_type}"')
    if city:
        query_parts.append(f'"{city}"')
        
    full_query = " ".join(query_parts)
    encoded_query = urllib.parse.quote_plus(full_query)
    
    return f"https://www.google.com/search?q={encoded_query}"

# --- Main Scraper Function (Cloud/Linux Optimized) ---
def run_scraper(url, max_pages, status_placeholder, log_placeholder):
    options = webdriver.ChromeOptions()
    
    # REQUIRED FOR STREAMLIT CLOUD (Linux without a monitor)
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # Stealth Settings
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
      "source": "Object.defineProperty(navigator, 'webdriver', { get: () => undefined })"
    })

    extracted_contacts = []
    seen_emails = set()
    email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')

    try:
        log_placeholder.info("Navigating to Google...")
        driver.get(url)
        
        for current_page in range(1, max_pages + 1):
            status_placeholder.write(f"**Scraping Page {current_page} of {max_pages}...**")
            log_placeholder.warning("Waiting for results to load...")
            
            try:
                WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.VwiC3b"))
                )
            except TimeoutException:
                log_placeholder.error("Timeout: Could not find search results. Google likely blocked the cloud server IP with a CAPTCHA.")
                break
                
            time.sleep(2) 

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            result_blocks = soup.find_all('div', class_=re.compile(r'\b(g|MjjYud)\b'))
            
            for block in result_blocks:
                name = "Name Not Found"
                h3_tag = block.find('h3')
                if h3_tag:
                    name = re.split(r'[-|·]', h3_tag.get_text(strip=True))[0].strip()
                
                snippet_div = block.find('div', class_='VwiC3b')
                if snippet_div:
                    emails_in_snippet = email_pattern.findall(snippet_div.get_text(strip=True))
                    for email in emails_in_snippet:
                        email = email.lower()
                        if email.endswith(".comat"): email = email.replace(".comat", ".com")
                        if email.endswith(".inand"): email = email.replace(".inand", ".in")
                        
                        if email not in seen_emails:
                            seen_emails.add(email)
                            extracted_contacts.append({'Name': name, 'Email': email})
            
            log_placeholder.success(f"Page {current_page} complete. Total unique contacts so far: {len(extracted_contacts)}")

            if current_page == max_pages:
                break

            try:
                next_button = driver.find_element(By.ID, "pnnext")
                driver.execute_script("arguments[0].scrollIntoView();", next_button)
                time.sleep(1)
                next_button.click()
                
                sleep_time = random.uniform(3.5, 6.5)
                log_placeholder.info(f"Sleeping for {sleep_time:.1f} seconds to mimic human behavior...")
                time.sleep(sleep_time)
                
            except NoSuchElementException:
                log_placeholder.info("No 'Next' button found. Reached the last page of results.")
                break

    except Exception as e:
        log_placeholder.error(f"An error occurred: {e}")

    finally:
        driver.quit()
        
    return extracted_contacts

# ==========================================
# STREAMLIT UI DESIGN
# ==========================================
st.set_page_config(page_title="LinkedIn Email Scraper", layout="wide")

st.title("🕵️‍♂️ LinkedIn Email Lead Scraper")
st.markdown("Extract names and emails from public Google Search results targeting LinkedIn profiles.")

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("Search Parameters")
    target_role = st.text_input("Target Role", value="Data Scientist")
    target_business = st.text_input("Business / Industry", value="Data Science")
    target_city = st.text_input("City (Optional)", value="Delhi NCR")
    
    st.divider()
    
    st.header("Scraper Settings")
    max_pages = st.slider("Max Pages to Scrape", min_value=1, max_value=20, value=3)
    
    start_button = st.button("🚀 Start Scraping", use_container_width=True)

# --- Main Content Area ---
if start_button:
    url = generate_search_url(target_role, target_business, target_city)
    st.write(f"**Generated Query URL:** [{url}]({url})")
    
    # Placeholders for dynamic UI updates
    status_text = st.empty()
    log_text = st.empty()
    
    with st.spinner("Initializing Chrome Engine on Cloud Server..."):
        # Run the scraper (no show_browser argument passed anymore)
        results = run_scraper(url, max_pages, status_text, log_text)
    
    status_text.success("Scraping Complete!")
    log_text.empty() # Clear the logs
    
    # Handle Results
    if results:
        df = pd.DataFrame(results)
        st.subheader(f"Extracted {len(df)} Contacts")
        
        # Display as interactive table
        st.dataframe(df, use_container_width=True)
        
        # CSV Download Button
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Results as CSV",
            data=csv,
            file_name=f"{target_role.replace(' ', '_')}_leads.csv",
            mime="text/csv",
        )
    else:
        st.warning("No emails were found. Google might have blocked the server request with a CAPTCHA, or there are no results for this query.")