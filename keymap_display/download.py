import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By

def save_image(url):
    download_dir = os.environ.get('GITHUB_WORKSPACE', os.environ.get('HOME')+'/Downloads')
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing_for_trusted_sources_enabled": False,
        "safebrowsing.enabled": False
    })
    driver = webdriver.Chrome(options=options)

    driver.get(url)
    driver.find_elements(by=By.CLASS_NAME, value='btn-success')[2].click()
    driver.find_elements(by=By.CLASS_NAME, value='dropdown-menu')[5].find_elements(by=By.TAG_NAME, value='a')[1].click()

    download_wait(download_dir, 30)

def download_wait(directory, timeout, nfiles=None):
    seconds = 0
    dl_wait = True
    while dl_wait and seconds < timeout:
        time.sleep(1)
        dl_wait = False
        files = os.listdir(directory)
        if nfiles and len(files) != nfiles:
            dl_wait = True

        for fname in files:
            if fname.endswith('.crdownload'):
                dl_wait = True

        seconds += 1
    return seconds
