import functools
import json
import matplotlib.pyplot as plt
import operator
import pandas as pd
import re
import tweepy
import seaborn as sns

from datetime import datetime
from ibm_watson import PersonalityInsightsV3
from pytube import YouTube


class PersonalityInsightUtil(object):
    
    def __init__(self, 
                 api_key,
                 url, 
                 mode="twitter", 
                 translate=False, 
                 **kwargs):
        
        self._api_key_ = api_key
        self._url_ = url
        
        self.pi_service = PersonalityInsightsV3(url=self._url_, 
                                                iam_apikey=self._api_key_, 
                                                version="2017-10-13")
        if mode == "twitter":
            self.consumer_key = kwargs['consumer_key']
            self.consumer_secret = kwargs['consumer_secret']
            self.access_token = kwargs['access_token']
            self.access_token_secret = kwargs['access_token_secret']
            
            
            self.api = self._twttier_auth(self.consumer_key, 
                                 self.consumer_secret, 
                                 self.access_token, 
                                 self.access_token_secret)
        elif mode == "youtube":
            if kwargs:
                raise ValueError("Youtube mode does not need Twitter API Keys. For safety, please remove.")
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

    def _get_personality(self, statuses):
        
        content = {'contentItems': statuses}

        result = pi_service.profile(json.dumps(content), 
                                 content_type="application/json", 
                                 accept="application/json").get_result()
        return result

    def _show_plot(self, result):

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
    
    def twitter_scrape(self,username):
        
        statuses = self._retrieve_tweets(username, self.api)
        
        contents = list(map(self._convert_status, statuses))
        
        return contens
    
    def youtube_scraper(self, url):
        contents = list(map(self._youtube_captions, url))
        ready = [
            {"content": content, "contenttype": "text/plain"} for content in contents
        ]
                
        return ready
    