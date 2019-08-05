import functools
import json
import matplotlib.pyplot as plt
import numpy as np
import operator
import pandas as pd
import re
import tweepy
import seaborn as sns

from datetime import datetime
from ibm_watson import PersonalityInsightsV3
from pytube import YouTube


import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import tweepy
import re
import functools
import operator
import warnings

from ibm_watson import PersonalityInsightsV3
from pytube import YouTube
from datetime import datetime

class PersonalityInsightUtil(object):
    
    def __init__(self, 
                 api_key,
                 url, 
                 mode="twitter", 
                 translate=False, 
                 **kwargs):
        
        self._api_key_ = api_key
        self._url_ = url
        self.mode = mode
        self.translate = translate
        
        self.pi_service = PersonalityInsightsV3(url=self._url_, 
                                                iam_apikey=self._api_key_, 
                                                version="2017-10-13")
        if self.mode == "twitter":
            self.consumer_key = kwargs['consumer_key']
            self.consumer_secret = kwargs['consumer_secret']
            self.access_token = kwargs['access_token']
            self.access_token_secret = kwargs['access_token_secret']
            
            
            self.api = self._twttier_auth(self.consumer_key, 
                                 self.consumer_secret, 
                                 self.access_token, 
                                 self.access_token_secret)
        elif self.mode == "youtube":
            if kwargs:
                warnings.warn("Youtube mode does not need Twitter API Keys. For safety, please remove.")
        else:
            raise ValueError("Does not support platform.")
            
    def _twttier_auth(self,
                      consumer_key,
                      consumer_secret,
                      access_token, 
                      access_token_secret):
        """
            Helper function for tweepy auth.
        """
        auth_list = [
                consumer_key,
                consumer_secret,
                access_token,
                access_token_secret
            ]
        
        if "" in auth_list: raise ValueError("One or more of Twitter API keys are missing.")
            
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)

        api = tweepy.API(auth)
        return api

    def _retrieve_tweets(self,username, api):
        max_id = None
        statuses = []

        for x in range(0, 16):  # Pulls max number of tweets from an account
            if x == 0:
                statuses_portion = api.user_timeline(screen_name=username,
                                                             count=200,
                                                             include_rts=False)
                status_count = len(statuses_portion)
                # get id of last tweet and bump below for next tweet set
                max_id = statuses_portion[status_count - 1].id - 1
            else:
                statuses_portion = api.user_timeline(screen_name=username,
                                                             count=200,
                                                             max_id=max_id,
                                                             include_rts=False)
                status_count = len(statuses_portion)
                try:
                    # get id of last tweet and bump below for next tweet set
                    max_id = statuses_portion[status_count - 1].id - 1
                except Exception:
                    pass
            for status in statuses_portion:
                statuses.append(status)

            print ('Number of Tweets user have: %s' % str(len(statuses)))

            return statuses

    def _convert_status(self, status):
        """
            Function to help prepare tweet to be sent to watson api.
        """
        current_time = datetime.now()
        
        content = {
            'userid': str(status.user.id),
            'id': str(status.id),
            'sourceid': 'python-twitter',
            'contenttype': 'text/plain',
            'language': status.lang,
            'content': status.text,
            'created': round((status.created_at - current_time).total_seconds()),
            'reply': (status.in_reply_to_status_id is None),
            'forward': False
        }
        return content

    def get_personality(self, username_or_urls, pandas_df=False):
        
        if self.mode == "twitter":
            contents = self.twitter_scrape(username_or_urls)
        
        if self.mode == "youtube":
            contents = self.youtube_scraper(username_or_urls)
        
        contents = {'contentItems': contents}

        result = self.pi_service.profile(json.dumps(contents), 
                                 content_type="application/json", 
                                 accept="application/json").get_result()
        if pandas_df is True:
            result_df = self._generate_df(result, username_or_urls)
            return result_df
        else:
            return result

    def _show_plot(self, result):
        # TODO: Plot for children personalitites of the big 5    
        result_dict = {need['name']: need['percentile'] for need in result['personality']}
        
        df = pd.DataFrame.from_dict(result_dict, orient="index")
        
        df.reset_index(inplace=True)
        
        df.columns = ['name', 'percentile']

        # Plot the result
        plt.figure(figsize=(15,5))
        sns.barplot(y="name", x="percentile", data=df)
        plt.show()

    def _cleanhtml(self, raw_html):
        
        cleanr = re.compile('<.*?>')
        
        cleantext = re.sub(cleanr, '', raw_html)
        
        return cleantext

    def _clean_string(self, string_word):
        
        s = self._cleanhtml(string_word)
        
        s = re.sub("\n", "", s)
        
        s = re.sub("-->", "", s)
        
        s = re.sub('[^\w\s]','',s)
        
        s = re.sub("\d+", "", s)
        
        return s

    def _youtube_captions(self, url):

        source = YouTube(url)
        
        try:
            caption = source.captions.get_by_language_code("en")
        except:
            caption = source.captions.get_by_language_code("id")

        caption_to_str =(caption.generate_srt_captions())

        final_text = " ".join(self._clean_string(caption_to_str).split())

        return final_text

    def _get_results(self, result, mode='personality'):

        # Get personality output
        personality = result[mode]

        # Get names
        names =[personality[percent_idx]['name'] for percent_idx in range(len(personality))]

        # Get percentiles
        percentiles =[personality[percent_idx]['percentile'] for percent_idx in range(len(personality))]
        return names, percentiles

    def _big_five_children_results(self, result, flattened=True):

        # Initiate lists
        list_of_names = []
        list_of_percentiles = []

        personality = result['personality']

        for pers_idx in range(len(personality)):

            # Get personality type
            facet = personality[pers_idx]['children']

            # Get children personality name
            facet_names = [facet[facet_idx]['name'] for facet_idx in range(len(facet))]
            print(facet_names)

            # Get Get children personality percentile
            facet_percentiles = [facet[facet_idx]['percentile'] for facet_idx in range(len(facet))]
            print(facet_percentiles)

            # Append elements
            list_of_names.append(facet_names)
            list_of_percentiles.append(facet_percentiles)

        if flattened is True:

            # Flatten the list of lists
            list_of_names = functools.reduce(operator.iconcat, list_of_names, [])
            list_of_percentiles = functools.reduce(operator.iconcat, list_of_percentiles, [])

        return list_of_names, list_of_percentiles
    
    def _generate_df(self, result, username_or_url):
        #TODO: Need to make support for multiple urls

        # Get personality names and percentiles
        personality_names, personality_percentiles = self._get_results(result, mode='personality')
        values_names, values_percentiles = self._get_results(result, mode='values')
        needs_names, needs_percentiles = self._get_results(result, mode='needs')
        children_names, children_percentiles = self._big_five_children_results(result, flattened=True)


        # INITIATE DATAFRAM
        # If index == 0
        personality_df = pd.DataFrame(columns=["Source"] + personality_names)
        values_df = pd.DataFrame(columns=["Source"] + values_names)
        needs_df = pd.DataFrame(columns=["Source"] + needs_names)
        children_df = pd.DataFrame(columns=["Source"] + children_names)
            
        if "http" in username_or_url:
            source = username_or_url
        else:
            source = "https://twitter.com/"+username_or_url

        # Append data to dataframe
        personality_idx = values_df.index.max() + 1 if values_df.index.max() is not np.nan else 0
        personality_df.loc[personality_idx] = [source] + personality_percentiles

        values_idx = values_df.index.max() + 1 if values_df.index.max() is not np.nan else 0
        values_df.loc[values_idx] = [source] + values_percentiles

        needs_idx = needs_df.index.max() + 1 if needs_df.index.max() is not np.nan else 0
        needs_df.loc[needs_idx] = [source] + needs_percentiles

        children_idx = children_df.index.max() + 1 if children_df.index.max() is not np.nan else 0
        children_df.loc[children_idx] = [source] + children_percentiles
        
        result_df = pd.concat([personality_df, 
                               values_df.drop("Source", axis=1), 
                               needs_df.drop("Source", axis=1), 
                               children_df.drop("Source", axis=1)], axis=1, sort=False)
        return result_df
        
    
    def twitter_scrape(self,username):
        
        # TODO: Need to make support for mutiple accounts
        # or urls
        statuses = self._retrieve_tweets(username, self.api)
        
        contents = list(map(self._convert_status, statuses))
        
        return contents
    
    def youtube_scraper(self, url):
        
        # TODO: Decide if need support for a single string
        contents = list(map(self._youtube_captions, url))
        ready = [
            {"content": content, "contenttype": "text/plain"} for content in contents
        ]
                
        return ready
    