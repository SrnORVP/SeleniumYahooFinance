
from selenium.webdriver.common.by import By
import selenium.webdriver.remote.webelement
from selenium.common.exceptions import NoSuchElementException, InvalidArgumentException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from pprint import pprint as pp


# ------------------------------------------------------------------------------------------------------
# Util/ Logging

x = 0
def i():
    global x
    x = x + 1 if x else 1
    return x


def time_wait(times=1):
    global time_clock
    import time
    time.sleep(time_clock * times)


def elem_details(elem, blank_line=True):
    print(elem.id, '-', elem.tag_name, '-', elem.text)
    if blank_line:
        print()


def elems_details(elems, name=''):
    print(f'{len(elems)} ea. of "{name}"')
    for e in elems:
        elem_details(e, blank_line=False)
    print()


def find_windows_by_name(driver, name, verbose=True):
    if verbose:
        hwnds = get_hwnds_by_name(name)
        print('python hwnd')
        pp(hwnds)
        print()
        windows = driver.find_elements(AppiumBy.NAME, name)
        elems_details(windows, name)


def find_windows(driver, verbose=True):
    if verbose:
        windows = driver.find_elements(AppiumBy.CLASS_NAME, 'Window')
        elems_details(windows, 'window')
        windows = driver.find_elements(AppiumBy.XPATH, '//Window/Window')
        elems_details(windows, 'window/window')
        windows = driver.find_elements(AppiumBy.ACCESSIBILITY_ID, 'root')
        elems_details(windows, 'root')


def find_textbox(driver):
    lstID, lstText = get_elems_by_class(driver, 'TextBox')
    print([*zip(lstID, lstText)])

def find_botton_by_text(elem, text):
    elems = elem.find_elements(By.XPATH, '//Button')
    # elem.id, '-', elem.tag_name, '-', elem.text)
    # print([*zip(lstID, lstText)])