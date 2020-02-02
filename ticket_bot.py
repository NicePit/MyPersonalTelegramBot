import time
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import ElementNotInteractableException
from collections import defaultdict
import pandas as pd
from tqdm import tqdm
import itertools
import os

# --------------------STATIC PARAMS----------------------------

year = 2020
months = range(1, 13)
origin_city = "Тель-Авив, Израиль,  TLV"
TOP_N_CHEAPEST_DESTINATIONS_PER_DAY = 3
STOP_CITIES = []
MAX_RETIRES = 5
CITIES = {'Rome': 'Рим, Италия,  ROM', 'Barcelona': 'Барселона, Испания, Эль-Прат BCN',
          'Lisbon': 'Лиссабон, Португалия, Лиссабон LIS'}
# --------------------------------------------------------------




class TicketFinder:

    def __init__(self):

        cap = DesiredCapabilities().FIREFOX
        cap["marionette"] = True
        GECKODRIVER_PATH = os.environ['GECKODRIVER_PATH']
        self.selenium_driver = webdriver.Firefox(capabilities=cap, executable_path=GECKODRIVER_PATH)
        self.url = 'https://aviasales.ru/calendar'
        self.selenium_driver.get(self.url)

        self.direct_tickets = None
        self.all_tickets = None

    def run(self, destination, min_days, max_days, target_month, departure_days):

        if destination:
            destination_city = CITIES[destination]
            path = f'tickets_to_{destination}_for_month_{target_month}.xlsx'
        else:
            destination_city = None
            path = f'tickets_to_everywhere_month_{target_month}.xlsx'

        writer = pd.ExcelWriter(path, engine='xlsxwriter')

        for i in range(0, 2):

            if i == 0:
                print('Scraping for direct flights')
                direct_only = True
            elif i == 1:
                print('Scraping for all flights')
                direct_only = False
            else:
                raise Exception('BOOM!')

            try:
                self.selenium_driver.find_element_by_css_selector('a.close-popup[data-args=calendar-tooltip]').click()
            except ElementNotInteractableException:
                pass

            self.selenium_driver.find_element_by_css_selector("#origin.in-text.tt-query").send_keys(origin_city)
            time.sleep(10)
            self.selenium_driver.find_element_by_css_selector(f"a[title='{origin_city}']").click()

            self.selenium_driver.execute_script(
                f"document.querySelector('.trip-duration-range > .min').value = {min_days}")
            self.selenium_driver.execute_script(
                f"document.querySelector('.trip-duration-range > .max').value = {max_days}")

            if destination_city:
                self.selenium_driver.find_element_by_css_selector("#destination.in-text.tt-query").send_keys(
                    destination_city)
                time.sleep(10)
                self.selenium_driver.find_element_by_css_selector(f"a[title='{destination_city}']").click()

            if len(departure_days) == 0:
                for month in months:
                    if month != target_month:
                        self.selenium_driver.execute_script(
                            f"document.querySelector('li[data-month=\"{month}\"] > label').setAttribute(\'class\',\'\')")
                    else:
                        self.selenium_driver.execute_script(
                            f"document.querySelector('li[data-month=\"{target_month}\"] > label').setAttribute(\'class\',\'checked\')")
            else:
                self.selenium_driver.find_element_by_id('ui-id-2').click()
                for dep_day in departure_days:
                    departure_days_to_select = list(
                        filter(lambda x: int(x.text) == dep_day, self.selenium_driver.find_elements_by_css_selector(
                            f"td[data-handler=selectDay][data-month='{target_month - 1}'][data-year='{year}'] > a.ui-state-default")))
                    for day in departure_days_to_select:
                        day.click()

            self.selenium_driver.find_element_by_css_selector('.c-label-button').click()

            rel_days = list()
            n = 0
            while n < MAX_RETIRES:
                n += 1
                rel_days = self.repeat_query(2 ** n, selector='.selectable.calendar-day')
                if len(rel_days) > 0:
                    break

            if len(rel_days) == 0:
                raise Exception('Something went wrong')

            tickets = defaultdict(list)
            direct_only_not_clicked = True
            currency_not_chosen = True

            for idx, rel_date in enumerate(rel_days):
                print(f"Scraping for date {idx + 1} out of {len(rel_days)}")
                rel_date.click()
                destinations = list()
                n = 1
                while n < MAX_RETIRES:
                    try:
                        time.sleep(2)
                        self.selenium_driver.find_element_by_css_selector('.link-but-small.default').click()
                        destinations = res = self.selenium_driver.find_elements_by_css_selector('.day-prices-route')
                        if len(destinations) > 0:
                            break
                    except:
                        time.sleep(2 ** n)
                        n += 1
                        continue

                self.selenium_driver.execute_script(
                    "document.querySelector('div.feedback-container').style.visibility='hidden'")

                if direct_only and direct_only_not_clicked:
                    time.sleep(5)
                    self.selenium_driver.find_element_by_css_selector('.checkbox-label.default .check').click()
                    direct_only_not_clicked = False

                if currency_not_chosen:
                    time.sleep(5)
                    currency_box = self.selenium_driver.find_element_by_css_selector('div[data-goal="currency"]')
                    currency_box.click()
                    usd_currency = currency_box.find_element_by_css_selector('li[data-value="USD"]')
                    usd_currency.click()
                    currency_not_chosen = False

                for idx2, destination in enumerate(tqdm(destinations[:TOP_N_CHEAPEST_DESTINATIONS_PER_DAY])):
                    try:
                        if idx2 != 0:
                            destination.click()
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
                        print("Weee")
                        continue

            df = pd.DataFrame(itertools.chain.from_iterable(list(tickets.values())))
            df['price'] = df['price'].apply(lambda x: x.replace(',', '').replace('$', ''))
            df['price'] = df['price'].apply(lambda x: int(x.strip()) if len(x.strip()) > 0 else 0)
            df = df.groupby('destination').apply(lambda x: x.sort_values(['price']).head(3))
            df['anomaly'] = df['price'] < (df['price'].mean() - df['price'].std())
            df = df.sort_values('price')

            if direct_only:
                df.to_excel(writer, sheet_name='direct_flights', index=False)
                self.direct_tickets = df
            else:
                df.to_excel(writer, sheet_name='all_flights', index=False)
                self.all_tickets = df
            self.selenium_driver.get(self.url)

        writer.save()
        writer.close()

    def repeat_query(self, time_to_sleep, selector):
        time.sleep(time_to_sleep)
        res = self.selenium_driver.find_elements_by_css_selector(selector)
        return res

    def close_driver(self):
        self.selenium_driver.close()

