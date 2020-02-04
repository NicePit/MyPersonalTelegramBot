import time

from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import ElementNotInteractableException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from collections import defaultdict
import pandas as pd
from tqdm import tqdm
import os

load_dotenv()

# --------------------STATIC PARAMS----------------------------

YEAR = 2020
MONTHS = range(1, 13)
ORIGIN_CITY = "Тель-Авив, Израиль,  TLV"
TOP_N_CHEAPEST_DESTINATIONS_PER_DAY = 2
STOP_CITIES = []
MAX_RETRIES = 10
SLEEP_TIME = 10

CITIES = {'Rome': 'Рим, Италия,  ROM',
          'Barcelona': 'Барселона, Испания, Эль-Прат BCN',
          'Lisbon': 'Лиссабон, Португалия, Лиссабон LIS'}

# --------------------------------------------------------------
GOOGLE_CHROME_BIN = os.environ.get('GOOGLE_CHROME_BIN')
CHROMEDRIVER_PATH = os.environ.get('CHROMEDRIVER_PATH')


class FareFinder:

    def __init__(self):

        print("Init of webdriver")

        chrome_options = ChromeOptions()
        chrome_options.binary_location = GOOGLE_CHROME_BIN
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-features=NetworkService")
        self.selenium_driver = webdriver.Chrome(chrome_options=chrome_options,
                                                executable_path=CHROMEDRIVER_PATH)

        self.url = 'https://aviasales.ru/calendar'

    def run(self, min_days, max_days, departure_months, departure_days=None, destination=None):

        print("Start scraping")
        kwargs = {"destination_city": destination, "min_days": min_days, "max_days": max_days,
                  "departure_months": departure_months, "departure_days": departure_days}

        print('SCRAPING DIRECT FLIGHTS')
        direct_tickets = self._search(direct=True, **kwargs)
        print('SCRAPING ALL FLIGHTS')
        all_tickets = self._search(direct=False, **kwargs)
        return direct_tickets, all_tickets

    def _search(self, direct=True, **kwargs):

        self.selenium_driver.get(self.url)
        self.selenium_driver.get(self.url)

        try:
            self.selenium_driver.find_element_by_css_selector('a.close-popup[data-args=calendar-tooltip]').click()
        except ElementNotInteractableException:
            pass

        self._set_kwargs(**kwargs)
        self.selenium_driver.execute_script(
            f"document.querySelector('.feedback-container').style.display=\'None\'")
        self.selenium_driver.find_element_by_css_selector('.c-label-button').click()
        time.sleep(SLEEP_TIME)

        self._set_currency()

        dates = self._find_dates()
        tickets_per_date = list()

        for idx, date in enumerate(dates):
            n = 1
            print("date", idx + 1)
            while n < MAX_RETRIES:
                try:
                    date.click()
                    cur_date_tickets = self._find_tickets_for_current_date(direct)
                    if len(cur_date_tickets) > 1:
                        tickets_per_date.append(cur_date_tickets)
                        break
                except Exception as e:
                    self.selenium_driver.execute_script("arguments[0].scrollIntoView();", date)
                    y_location = date.location['y']
                    self.selenium_driver.execute_script(f"window.scrollTo(0, {y_location - 100})")
                    print("Scrolling up a bit")
                    time.sleep(2 ** n)
                    n += 1
                    continue

        all_tickets = list()
        for date in tickets_per_date:
            for dest in date:
                for opt in dest:
                    all_tickets.append(opt)
        df = pd.DataFrame(all_tickets)
        df = self._postprocess_dataframe(df)
        return df

    def _set_currency(self):
        print("Setting currency")
        n = 1
        while n < MAX_RETRIES:
            try:
                currency_box = self.selenium_driver.find_element_by_css_selector('div[data-goal="currency"]')
                currency_box.click()
                time.sleep(2 ** n)
                usd_currency = currency_box.find_element_by_css_selector('li[data-value="USD"]')
                usd_currency.click()
                break
            except Exception as e:
                print("Currency settings:", e)
                n += 1
                continue

    def _set_kwargs(self, **kwargs):

        min_days = kwargs.get('min_days')
        max_days = kwargs.get('max_days')
        destination_city = kwargs.get('destination_city')
        departure_months = kwargs.get('departure_months')
        departure_days = kwargs.get('departure_days')

        if len(departure_months) > 1 and len(departure_days) > 1:
            raise RuntimeError("If departure days are specified, only one month can be chosen")

        self._set_origin()
        self._set_destination(destination_city)
        self._set_trip_duration(min_days=min_days, max_days=max_days)

        if departure_days:
            self._select_days(departure_month=departure_months[0], departure_days=departure_days)
        else:
            self._select_months(departure_months=departure_months)

    def _postprocess_dataframe(self, df: pd.DataFrame):
        df['price'] = df['price'].apply(lambda x: x.replace(',', '').replace('$', ''))
        df['price'] = df['price'].apply(lambda x: int(x.strip()) if len(x.strip()) > 0 else 0)
        df['destination'] = df['destination'].apply(lambda x: x.split(" - ")[1])
        df = df.groupby('destination').apply(lambda x: x.sort_values(['price']).head(3))
        df['anomaly'] = df['price'] < (df['price'].mean() - df['price'].std())
        df = df.sort_values('price')
        return df

    def _set_trip_duration(self, min_days, max_days):

        print("Setting duration")
        self.selenium_driver.execute_script(
            f"document.querySelector('.trip-duration-range > .min').value = {min_days}")
        self.selenium_driver.execute_script(
            f"document.querySelector('.trip-duration-range > .max').value = {max_days}")

    def _set_origin(self):
        print("Setting origin")
        tries = 1
        while tries < MAX_RETRIES:
            try:
                self.selenium_driver.find_element_by_css_selector("#origin").send_keys(ORIGIN_CITY)
                time.sleep(SLEEP_TIME * tries)
                self.selenium_driver.find_element_by_css_selector(f"a[title='{ORIGIN_CITY}']").click()
                break
            except Exception as e:
                print("Setting origin:", e)
                tries += 1

    def _set_destination(self, destination_city):
        print("Setting destination")
        if destination_city:
            tries = 1
            while tries < MAX_RETRIES:
                try:
                    self.selenium_driver.find_element_by_css_selector("#destination.in-text.tt-query").send_keys(
                        destination_city)
                    time.sleep(SLEEP_TIME * tries)
                    self.selenium_driver.find_element_by_css_selector(f"a[title='{destination_city}']").click()
                    break
                except Exception as e:
                    print("Setting destination:", e)
                    tries += 2

    def _select_days(self, departure_month, departure_days):
        self.selenium_driver.find_element_by_css_selector('a[data-goal=exact_date]').click()
        for dep_day in departure_days:
            departure_days_to_select = list(
                filter(lambda x: int(x.text) == dep_day, self.selenium_driver.find_elements_by_css_selector(
                    f"td[data-handler=selectDay][data-month='{departure_month - 1}']"
                    f"[data-year='{YEAR}'] > a.ui-state-default")))
            for day in departure_days_to_select:
                day.click()

    def _select_months(self, departure_months):
        for month in MONTHS:
            if month not in departure_months:
                self.selenium_driver.execute_script(
                    f"document.querySelector('li[data-month=\"{month}\"] > label').setAttribute(\'class\',\'\')")
        for dep_month in departure_months:
            self.selenium_driver.execute_script(
                f"document.querySelector('li[data-month=\"{dep_month}\"] > label')."
                f"setAttribute(\'class\',\'checked\')")

    def _find_dates(self):
        rel_days = list()
        n = 0
        while n < MAX_RETRIES:
            n += 1
            rel_days = self._repeat_query(2 ** n, selector='.selectable.calendar-day')
            if len(rel_days) > 0:
                break

        if len(rel_days) == 0:
            raise Exception('No tickets found')
        return rel_days

    def _find_tickets_for_current_date(self, direct: bool):
        destinations = list()
        n = 1
        while n < MAX_RETRIES:
            try:
                self.selenium_driver.find_element_by_css_selector('.link-but-small.default').click()
                destinations = self.selenium_driver.find_elements_by_css_selector('.day-prices-route')
                if len(destinations) > 0:
                    break
            except Exception as e:
                print("Tickets for current date:", e)
                time.sleep(2 ** n)
                n += 1
                continue

        self.selenium_driver.execute_script(
            "document.querySelector('div.feedback-container').style.visibility='hidden'")
        if direct:
            time.sleep(SLEEP_TIME)
            self.selenium_driver.find_element_by_css_selector('.checkbox-label.default .check').click()

        tickets = self._search_destinations(destinations)
        return tickets

    def _search_destinations(self, destinations):
        tickets = defaultdict(list)
        for idx2, destination in enumerate(tqdm(destinations[:TOP_N_CHEAPEST_DESTINATIONS_PER_DAY])):
            try:
                if idx2 != 0:
                    destination.click()
                    time.sleep(2)
                dest_name = ' - '.join(
                    [el.text for el in destination.find_elements_by_css_selector('.day-prices-header span')][
                    :-1])
                options = destination.find_elements_by_css_selector('.price-row')
                for option in options:
                    option_price = option.find_elements_by_css_selector('.price-td span')[0].text

                    option_freshness = option.find_element_by_class_name('freshnes-td').text
                    option_dates = option.find_element_by_css_selector('.date-td').text
                    option_link = option.find_element_by_class_name('controls-td a').get_attribute('href')
                    tickets[dest_name].append(
                        {'destination': dest_name, 'price': option_price, 'freshness': option_freshness,
                         'dates': option_dates, 'link': option_link})
            except Exception as e:
                print("Current day tickets destinations:", e)
        return list(tickets.values())

    def _repeat_query(self, time_to_sleep, selector):
        time.sleep(time_to_sleep)
        res = self.selenium_driver.find_elements_by_css_selector(selector)
        return res

    def close_driver(self):
        self.selenium_driver.close()


def search_tickets(min_days, max_days, departure_months, departure_days):
    print("New request for searching tickets, starting FareFinder job")
    finder = FareFinder()
    direct_tickets, all_tickets = finder.run(min_days=min_days, max_days=max_days,
                                             departure_months=departure_months, departure_days=departure_days)
    finder.close_driver()
    print("FareFinder job has been successfully completed")
