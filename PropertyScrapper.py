import numpy as np
import pandas as pd
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class PropertyScraper:

    def __init__(self):
        self.driver = None
        self.wait = None
        self.data = []

    # ---------- SETUP ----------
    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--disable-http2")
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--enable-features=NetworkServiceInProcess")
        chrome_options.add_argument("--disable-features=NetworkService")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        )

        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 10)

    def wait_for_page_to_load(self):
        try:
            self.wait.until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except:
            print("Page did not fully load")
        else:
            print(f"Loaded: {self.driver.title}")

    # ---------- NAVIGATION ----------
    def open_site(self):
        self.driver.get("https://www.99acres.com/")
        self.wait_for_page_to_load()

    def search_city(self, city="Chennai"):
        try:
            search_bar = self.wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="keyword2"]'))
            )
            search_bar.send_keys(city)
            time.sleep(2)

            valid_option = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="0"]'))
            )
            valid_option.click()
            time.sleep(2)

            search_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="searchform_search_btn"]'))
            )
            search_button.click()
            self.wait_for_page_to_load()

        except Exception as e:
            print("Search error:", e)

    # ---------- FILTERS ----------
    def apply_filters(self):
        try:
            self.wait.until(EC.element_to_be_clickable((By.ID, "bdf__lfBudMin"))).click()
            self.wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//*[@id='lf_budget_min_list']/li[3]")
                )
            ).click()

            self.wait.until(EC.element_to_be_clickable((By.ID, "bdf__lf_budMax"))).click()
            self.wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//*[@id='lf_budget_max_list']/li[@data-val='17']")
                )
            ).click()

            self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "label[for='verified_Y']"))
            ).click()

        except Exception as e:
            print("Filter error:", e)

    # ---------- SCRAPING ----------
    def extract_row(self, row):
        try:
            name = row.find_element(By.CLASS_NAME, "tupleNew__headingNrera").text
        except:
            name = np.nan

        try:
            location = row.find_element(By.CLASS_NAME, "tupleNew__propType").text
        except:
            location = np.nan

        try:
            price = row.find_element(By.CLASS_NAME, "tupleNew__priceValWrap").text
        except:
            price = np.nan

        try:
            elements = row.find_elements(By.CLASS_NAME, "tupleNew__area1Type")
            area, bhk = [ele.text for ele in elements]
        except:
            area, bhk = [np.nan, np.nan]

        return {
            "name": name,
            "location": location,
            "price": price,
            "area": area,
            "bhk": bhk
        }

    def scrape_pages(self):
        page_count = 0

        while True:
            page_count += 1
            print(f"Scraping page {page_count}")

            rows = self.driver.find_elements(By.CLASS_NAME, "tupleNew__TupleContent")

            for row in rows:
                self.data.append(self.extract_row(row))

            try:
                next_btn = self.driver.find_element(
                    By.XPATH, "//a[normalize-space()='Next Page >']"
                )
                next_btn.click()
                time.sleep(5)

            except:
                print("No more pages")
                break

    # ---------- CLEANING ----------
    def clean_data(self):
        df = pd.DataFrame(self.data)

        for col in ["name", "location", "price", "area", "bhk"]:
            if col not in df.columns:
                df[col] = np.nan

        df = (
            df.drop_duplicates()
            .apply(lambda col: col.str.strip().str.lower() if col.dtype == "object" else col)
            .assign(
                is_starred=lambda df_: df_["name"].str.contains("\n", na=False).astype(int),
                name=lambda df_: df_["name"].str.replace("\n[0-9.]+", "", regex=True).str.strip(),
                location=lambda df_: df_["location"].str.replace("chennai", "", regex=False).str.strip(),
                price=lambda df_: df_["price"].str.replace("₹", "", regex=False),
                area=lambda df_: df_["area"].str.replace("sqft", "", regex=False),
                bhk=lambda df_: df_["bhk"].str.replace("bhk", "", regex=False)
            )
            .reset_index(drop=True)
        )

        return df

    # ---------- SAVE ----------
    def save(self, df):
        df.to_excel("chennai-properties-99acres.xlsx", index=False)

    # ---------- RUN ----------
    def run(self):
        self.setup_driver()
        self.open_site()
        self.search_city()
        self.apply_filters()
        self.scrape_pages()

        self.driver.quit()

        df = self.clean_data()
        self.save(df)


# ---------- EXECUTE ----------
if __name__ == "__main__":
    scraper = PropertyScraper()
    scraper.run()