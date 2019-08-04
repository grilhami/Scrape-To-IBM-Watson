import json
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import requests

from bs4 import BeautifulSoup
from matplotlib.lines import Line2D
from ibm_watson import DiscoveryV1
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from tqdm import tqdm
from urllib.request import urlopen, Request
from urllib.parse import urlparse

class DiscoveryUtil(object):
    def __init__(self, api_key, url, driver_path, scrape="all"):
        
        self.api_key = api_key
        self.url = url
        
        self.driver_path = driver_path
        
        self.driver = webdriver.Chrome(executable_path=self.driver_path)
        
        self.discovery = DiscoveryV1(version="2018-12-03",
                                     iam_apikey=self.api_key,
                                     url=self.url
                                    )
        