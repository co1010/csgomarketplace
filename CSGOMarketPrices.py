from bs4 import BeautifulSoup
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime
from currency_converter import CurrencyConverter

# Dictionary containing references of currency symbols to acronyms
currency_ref = {'$': 'USD', '£': 'GBP', '€': 'EUR', '¥': 'JPY', 'P': 'PHP', '฿': 'THB', '₩': 'KRW', '₹': 'INR',
                'R$': 'BRL', 'S$': 'SGD', 'Mex$': 'MXN', 'CDN$': 'CAD', 'NZ$': 'NZD', 'HK$': 'HKD', 'pуб': 'RUB',
                'kr': 'SEK', 'Rp': 'IDR', 'RM': 'MYR', 'TL': 'TRY', 'R': 'ZAR'}

# Possible wears that a csgo item can have
wears = ['Battle-Scarred', 'Well-Worn', 'Field-Tested', 'Minimal%20Wear', 'Factory%20New']


def Initialize():
    # The file csgoskins is a csv listing every skin. Each line is a unique skin in format "gun, skin"
    cs_skins = open('csgoskins.csv', 'r')

    # The file line.txt stores what line the program is on, so I can stop it and start it back up where it left off.
    # If the file does not exist, it will create it.
    line_trackerW = open('line.txt', 'a+')

    try:
        line_trackerW.seek(0)
        starting_line = int(line_trackerW.readline().rstrip('\n'))
        if starting_line <= 0:
            starting_line = 1
    except ValueError:
        starting_line = 1

    # Skip to current line.
    line = cs_skins.readline().rstrip('\n')
    for n in range(1, starting_line):
        line = cs_skins.readline().rstrip('\n')

    linelist = line.split(',')
    item = '{} {}'.format(linelist[0].replace('%20', ' '), linelist[1].replace('%20', ' '))  # Normal item name
    print('Starting with the {} at {}'.format(item, datetime.now().time()))

    MainLoop(line, starting_line, cs_skins)


def MainLoop(line, starting_line, cs_skins):
    global wears

    while line:  # This main loop iterates through each cs:go skin

        linelist = line.split(',')
        item = '{} {}'.format(linelist[0].replace('%20', ' '), linelist[1].replace('%20', ' '))  # Normal item name

        # This loop iterates through each wear the skin has. Some skins don't have all wear values.
        for wear in wears:
            item_wear = wear.replace('%20', ' ')

            if IsInvalid(item, item_wear):
                continue

            soup = GetElements(linelist, item, wear, item_wear)
            if not soup:
                continue

            usd_item_price = GetPrice(soup)
            if not usd_item_price:
                continue

            highest_buyorder = GetBuyorder(soup)

            listing_volume = GetListingVolume(soup)

            buyorder_volume = GetBuyorderVolume(soup)

            # Item needs to be popular enough to easily sell. I set this number arbitrarily at 100 buyorders.
            # Item must also have at least a 20% difference between buyorder and price in order to make decent profit.
            if buyorder_volume > 100 and highest_buyorder < usd_item_price*.8:
                ratio = highest_buyorder/usd_item_price
                data = open('data.txt', 'a')
                data.write("{}, {}, ${}, ${}, {}, {}, {}\n".format(
                    item, item_wear, round(usd_item_price, 2), highest_buyorder,
                    round(ratio, 2), buyorder_volume, listing_volume))
                data.close()

        starting_line += 1
        line_trackerW = open('line.txt', 'w')
        line_trackerW.write(str(starting_line))
        line_trackerW.close()
        time.sleep(5)  # Wait to try to avoid "too many requests" error
        line = cs_skins.readline().rstrip('\n')


# Check if the item/wear combination is known to be invalid
def IsInvalid(item, item_wear):
    invalid_item_check = open('invalid.txt', 'r+')
    invalid_line = invalid_item_check.readline().rstrip('\n')
    while invalid_line:
        invalid_list = invalid_line.split(',')
        if item == invalid_list[0]:
            if item_wear == invalid_list[1]:
                return True
        invalid_line = invalid_item_check.readline().rstrip('\n')
    return False


def GetElements(linelist, item, wear, item_wear):
    item_url = linelist[0] + '%20%7C%20' + linelist[1] + '%20%28' + wear + '%29'
    main_url = 'https://steamcommunity.com/market/listings/730/'
    url = main_url + item_url
    driver = webdriver.Chrome()
    driver.get(url)

    # This try looks for the elements I need to get data from. I wait for them to load in before taking data
    # from the site.
    try:
        WebDriverWait(driver, 6).until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'table.market_commodity_orders_table')))
        WebDriverWait(driver, 6).until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, '#searchResultsRows span.market_listing_price.market_listing_price_with_fee')))
        WebDriverWait(driver, 6).until(EC.presence_of_element_located(
            (By.ID, 'searchResults_total')))
    except:
        res = driver.execute_script('return document.documentElement.outerHTML')
        soup = BeautifulSoup(res, 'lxml')
        # This if checks for a message that comes up when an item doesn't have the wear I checked for. I'm making a
        # file invalid.txt with a list of them so I can optimized my code later by automatically skipping over them.
        if not soup.find('div', {'class': 'market_listing_table_message'}) is None:
            driver.quit()
            invalid_item_wears = open('invalid.txt', 'a+')
            invalid_item_wears.write('{},{}\n'.format(item, item_wear))
            invalid_item_wears.close()
            return False
        # This if is true when there's no buy requests for a skin. The price is so low nobody wants to buy it.
        elif not soup.find('div', {'id': 'market_commodity_buyrequests'}) is None:
            driver.quit()
            return False
        # If it's not either of the above, then I got a too many requests error. I don't try to get around it with
        # an IP spoof, I just wait it out. I found 70 seconds to be the ideal number. I print a message so I know
        # when it happened. Normally happens every 4 minutes or so.
        else:
            print('Got "Too Many Requests" error at {} with {} {}'.format(datetime.now().time(), item, item_wear))
            time.sleep(70)
            driver.quit()
            return False

    res = driver.execute_script('return document.documentElement.outerHTML')
    soup = BeautifulSoup(res, 'lxml')
    driver.quit()

    return soup


def GetPrice(soup):
    global currency_ref

    # The following code finds the price, identifies its currency, and converts it into a float friendly number
    # which is passed to the currency converter to get the price in USD as a float.
    item_price = soup.find('span', {'class': 'market_listing_price market_listing_price_with_fee'})\
        .text.strip().replace(',', '.')
    item_price_pattern = re.compile(r'\d*\.?\d\d*\.?\d*\.?\d*')  # Pattern for the overall price
    item_price_periods = re.compile(r'\.\d\d\d')  # Pattern for finding if price is in thousands
    item_price_match = item_price_pattern.search(item_price)
    item_periods_match = item_price_periods.findall(item_price_match.group())
    friendly_price = item_price_match.group().replace('.', '', len(item_periods_match))  # Get rid of thousands comma

    item_currency_pattern = re.compile(r'[£€¥P฿₩₹]|[RS]\$|Mex\$|CDN\$|NZ\$|HK\$|^\$|pуб|kr|Rp|RM|TL|R')
    item_currency_match = item_currency_pattern.search(item_price)
    # When there's no match for the item currency(e.x, Ukraine hryvnia or Vietnam dong), return False.
    try:
        cur = CurrencyConverter()
        usd_item_price = cur.convert(float(friendly_price), currency_ref[item_currency_match.group()], 'USD')
    except:
        return False
    return usd_item_price


def GetBuyorder(soup):
    # Find the buyorder table and scrape the highest(first) value. This is always in USD thankfully.
    buyorder_table = soup.find('table', {'class': 'market_commodity_orders_table'}).text
    buyorder_pattern = re.compile(r'\d*,?\d*\.\d\d')
    buyorder_match = buyorder_pattern.search(buyorder_table)
    highest_buyorder = float(buyorder_match.group())
    return highest_buyorder


def GetListingVolume(soup):
    # Find the amount of listings of the item.
    listing_volume = int(soup.find('span', {'id': 'searchResults_total'}).text.replace(',', ''))
    return listing_volume


def GetBuyorderVolume(soup):
    # Find the amount of buyorders for the item. I'm using this as a measure of item popularity.
    buyorder_volume = int(soup.find('span', {'class': 'market_commodity_orders_header_promote'}).text.replace(',', ''))
    return buyorder_volume


if __name__ == "__main__":
    Initialize()
