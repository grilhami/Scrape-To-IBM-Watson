import json
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
import re
import requests

from bs4 import BeautifulSoup
from ibm_watson import DiscoveryV1
from googletrans import Translator
from matplotlib.lines import Line2D
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from tqdm import tqdm
from urllib.request import urlopen, Request
from urllib.parse import urlparse

class DiscoveryUtil(object):
    def __init__(self, api_key, url, collection_name, reset_collection=True): 

        # TODO: Includese scraper capability
        self.api_key = api_key
        self.url = url
        self.collection_name = collection_name
        
        self.discovery = DiscoveryV1(version="2018-12-03",
                                     iam_apikey=self.api_key,
                                     url=self.url
                                    )

        # TODO: Need to add function to handle
        # modifying configuration to include
        # keyword extraction
        self.translator = Translator()
    
        self.environment_id, self.config_id, self.collection_id = self._get_ids()
        
        if reset_collection is True:
            self.collection_id = self._reset_collection()
        
        
    def _reset_collection(self):
        # Delete collection
        delete_collection = self.discovery.delete_collection(self.environment_id, 
                                                             self.collection_id).get_result()
        print(json.dumps(delete_collection, indent=2))

        # Make a new collection
        new_collection = self.discovery.create_collection(environment_id=self.environment_id, 
                                                 configuration_id=self.config_id, 
                                                 name=self.collection_name, 
                                                 description="", 
                                                 language="en").get_result()
        print(json.dumps(new_collection, indent=2))

        new_collection_id = new_collection['collection_id']
        return new_collection_id
        
    def _get_ids(self):

        if self.collection_name == "Today and Yesterday":
            pass
        elif self.collection_name == "Last 6 Months":
            pass
        else:
            raise ValueError("Collection name unkown in this environment.")

        environments = self.discovery.list_environments().get_result()
        #print(json.dumps(environments, indent=2))
        environment_id = environments['environments'][1]['environment_id']
        print("Environment ID: {}".format(environment_id), end="\n\n")

        # Get config ID
        configs = self.discovery.list_configurations(environment_id).get_result()
        #print(json.dumps(configs, indent=2))
        config_id = [x['configuration_id'] for x in configs['configurations'] if self.collection_name in x['name']][0]
        print("Configurations ID: {}".format(config_id), end="\n\n")

        # Get collection current id 
        collections = self.discovery.list_collections(environment_id).get_result()
        #print(json.dumps(collections, indent=2))
        collection_id = [x['collection_id'] for x in collections['collections'] if self.collection_name in x['name']][0]
        print("Collection ID: {}".format(collection_id), end="\n\n")

        return environment_id, config_id, collection_id
        
    def _url_name_extension(self, url):
        file_name = os.path.basename(url)
        if file_name == "":
            file_name = urlparse(url).path
            file_name = file_name.replace("/", "-")
        file_name = file_name.replace("?", "-").replace("=", "-")
        return file_name

    def _open_file(self, content, write_file=False, name_extension=""):
        """
        Function to open or write files.
        """

        if write_file is False:
            try:
                fileinfo =  open((content), "rb")
            except:
                fileinfo =  open(os.path.join(os.getcwd(), content), "rb")

            return fileinfo
        else:
            filename = "temp_url_files/temporary_file_{}.html".format(name_extension)
            with open(filename, "w") as f:
                f.write(content)
        return filename
        
    def _get_webpage_data(self, url, no_p=False, main_tag=None, attribute_dict={}):
        """
        Function to clean web content.
        """

        MAX_RETRIES = 20
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}

        session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=MAX_RETRIES)
        session.mount('https://', adapter)
        session.mount('http://', adapter)

        r = session.get(url, headers=headers)

        soup = BeautifulSoup(r.content)

        all_p_data = [p.text for p in soup.find_all("p")]
        
        # Handle text that is not contain within a
        # an html tag <p>
        if no_p is True:
            if main_tag is None and bool(attribute_dict) is False:
                raise ValueError("when no_p is true, then main tag and attribute dict must not be empty")
            
            assert isinstance(main_tag, str), f"main tag must be str, not {type(main_tag)}"
            assert isinstance(attribute_dict, dict), f"main tag must be dict, not {type(attribute_dict)}"
            assert bool(attribute_dict) == True, "attribute dict must not be empty"
            
            text = soup.find("div", {"class": "itp_bodycontent detail_text"})
            final_text = text.text
            return final_text

        try:
            title = soup.find("h1").text
        except:
            title = soup.find("h1")

        try: 
            final_text = " ".join([title] + all_p_data)
        except:
            final_text = " ".join(all_p_data)
        return final_text
    
    def _normalize_string(self, s):
        s = re.sub(r"([.!?])", r" \1", s)
        s = re.sub(r"[^a-zA-Z.!?]+", r" ", s)
        s = s.lower()
        return s

    def send_news_discovery(self, url_list):

        # TODO: Add support for using a file path

        print("Generating web data...")
        all_content_list = list(map(self._get_webpage_data, tqdm(url_list)))
        
        for content_idx in range(len(all_content_list)):
            if len(all_content_list[content_idx].split()) >= 150:
                print("This link has MORE thatn 150 tokens")
                print(url_list[content_idx], end="\n\n")

            else:
                print("This link has LESS thatn 150 tokens")
                print(url_list[content_idx], end="\n\n")
            
        content_list = [content for content in all_content_list if len(content.split()) > 150]
        indeces = [all_content_list.index(content) for content in content_list]


        print("Translating contents...")
        content_translated = []

        for content in tqdm(content_list):
            try:
                text = self.translator.translate(content, src="id", dest="en").text
                content_translated.append(text)
            except:
                continue
                
        print("Normalizing Text...")
        content_translated = list(map(self._normalize_string, tqdm(content_translated)))

        print("Generating file names...")
        content_names = list(map(self._url_name_extension, tqdm(url_list)))
        content_names = [content_names[i] for i in indeces]

        print("Sending to Watson Discovery...")
        for content_i in tqdm(range(len(content_translated))):
            print(content_translated[content_i])
            try:
                get_path = self._open_file(content_translated[content_i], write_file=True, name_extension=content_names[content_i])

                content_file = self._open_file(get_path)

                # Send the data to the service
                add_doc = self.discovery.add_document(self.environment_id, 
                                                 self.collection_id, 
                                                 file=content_file).get_result()
                print(json.dumps(add_doc, indent=2), end="\n\n")
            except Exception as e:
                error = {'error': str(e)}
                print(json.dumps(error), end="\n\n")
                continue
        return content_names, url_list
    
    def get_result(self, urls, query):

        # TODO: Get url and file name based on result.
        content_names, url_list = self.send_news_discovery(urls)
        
        query_collections = self.discovery.query(self.environment_id, 
                                        self.collection_id, 
                                        query=query).get_result()
        return query_collections
    def query(self, query):
        query_result = self.discovery.query(self.environment_id, 
                                        self.collection_id, 
                                        query=query).get_result()
        return query_result
   
