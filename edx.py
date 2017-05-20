import csv
import time
import json
import toolz
import pickle
import requests
import numpy as np
import matplotlib.pyplot as plt
from flask import Flask, render_template, url_for, request

app = Flask(__name__)

infos = list()
base_url = 'https://api.edx.org'
access_token_url = '/oauth2/v1/access_token'
get_catalogs_list_url = '/catalog/v1/catalogs/'
get_catalog_info_url = '/catalog/v1/catalogs/' # +id

# The number of trying request if it faces to API limitation
TRY_NUMBERS = 2

client_id = '###'
client_secret = '###'


"""
This class is for analytics of data
"""
class Analytics:
    def __init__(self):
        self.category_info = dict()

analytics = Analytics()


"""
This is a class for Course type which contains following information
"""
class Course:
    def __init__(self):
        self.category = None
        self.description = None
        self.title = None
        self.institute = None
        self.instructor = None
        self.price = None
        self.site = None
        self.credit = None
        self.id = None


"""
This function is for converting unicode text to json format

Parameter
----------
text: input unicode text

Return
----------
input text in json format
"""
def unicode_to_json(text):
    unicode_text = unicode(text)
    data = json.loads(unicode_text)
    return data


"""
This function is for converting input to ascii string

Parameter
----------
text: input text

Return
----------
input text in ascii format
"""
def to_string_ascii(text):
    return unicode(text).replace("\r", " ").replace("\n", " ").replace("\t", '').replace("\"", "")

"""
This function is for extracting considerable fields of API's response

Parameter
----------
catalog_info_data: The information for each catalog which is the response of API

"""
def extract_info(catalog_info_data):
    global infos
    global analytics
    
    if len(catalog_info_data['results']) > 0: 
        for course in catalog_info_data['results']:
            course_info = Course()
            if len(course['subjects']) > 0:
                course_info.category = to_string_ascii(course['subjects'][0]['name'])
            course_info.description = to_string_ascii(course['short_description'])
            course_info.title = to_string_ascii(course['title'])
            if len(course['owners']) > 0:
                course_info.institute = to_string_ascii(course['owners'][0]['name'])
                course_info.site = str(course['owners'][0]['marketing_url'])
            if len(course['course_runs']) > 0:
                instructors = ""
                for instructor in course['course_runs'][0]['instructors']:
                    instructors = instructors + ", " + to_string_ascii(instructor)
                course_info.instructor = instructors
                course_info.price = str(course['course_runs'][0]['seats'][len(course['course_runs'][0]['seats'])-1]['price']) \
                                    + " " + str(course['course_runs'][0]['seats'][len(course['course_runs'][0]['seats'])-1]['currency'])
                course_info.credit = str(course['course_runs'][0]['seats'][len(course['course_runs'][0]['seats'])-1]['credit_hours'])
            course_info.id = str(course['key'])
            
            infos.append(course_info)


"""
This router is for showing information over a html file
"""
@app.route('/')
def home():
    global infos
    return render_template('layout.html', info=infos)


"""
This function is for generating access token

Return
----------
access_token
"""
def get_access_token():
    access_token_request_body = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'token_type': 'jwt'
    }
    
    url = base_url+access_token_url
    access_token_info = requests.post(url=url, data=access_token_request_body)
    access_token_info = access_token_info.text
    
    # convert to unicode
    access_token_data = unicode_to_json(access_token_info)
    return str(access_token_data['access_token'])

"""
This function is for getting all of the catalogs, but for now there is just one

Return
----------
list of catalogs with corresponding data
"""
def catalogs_list(access_token):
    try_request = TRY_NUMBERS
    get_catalogs_header = {
            'Authorization': 'JWT ' + access_token
    }
    
    while try_request > 0:
        catalogs_list = requests.get(base_url+get_catalogs_list_url, headers=get_catalogs_header)
        if catalogs_list.status_code == 429: # reaching the limitation
            waiting_time = [int(s) for s in catalogs_list.text.split() if s.isdigit()]
            waiting_time = int(waiting_time[0])
            print 'sleep for', waiting_time, 'seconds'
            try_request -= 1
            time.sleep(waiting_time + 20)
        else:
            try_request = 0
            
    catalogs_list_data = unicode_to_json(catalogs_list.text)
    return catalogs_list_data

"""
This function is for extracting all of the usefull data from catalog list

Parameter
----------
catalogs_list_data: list of catalogs with their information
"""
def extract_all_info(catalogs_list_data, access_token):
    global infos
    page_counter = 1
    try_request = TRY_NUMBERS
    
    get_catalogs_header = {
            'Authorization': 'JWT ' + access_token
    }
    
    for result in catalogs_list_data['results']:
        catalog_id = int(result['id'])
        print 'number of all courses in catalog', catalog_id, 'is:', int(result['courses_count'])
        
        url = base_url+get_catalog_info_url+str(catalog_id)+'/courses/'
        
        while try_request > 0:                                       
            catalog_info = requests.get(url=url, headers=get_catalogs_header)
            if catalog_info.status_code == 429: # reaching the limitation
                waiting_time = [int(s) for s in catalog_info.text.split() if s.isdigit()]
                waiting_time = int(waiting_time[0])
                print 'sleep for', waiting_time, 'seconds'
                try_request -= 1
                time.sleep(waiting_time + 20)
            else:
                try_request = 0
        
        catalog_info_data = unicode_to_json(catalog_info.text)
        print 'number of active courses in catalog', catalog_id, 'is:', int(catalog_info_data['count'])
            
        # whenever there is a page iteration, get information for next pages
        while(catalog_info_data['next'] is not None):
            print 'on page:', page_counter
            page_counter += 1
            
            extract_info(catalog_info_data)
            next_url = str(catalog_info_data['next'])
            
            try_request = TRY_NUMBERS
            while try_request > 0:
                catalog_info = requests.get(url=next_url, headers=get_catalogs_header)
                if catalog_info.status_code == 429: # reaching the limitation
                    waiting_time = [int(s) for s in catalog_info.text.split() if s.isdigit()]
                    waiting_time = int(waiting_time[0])
                    print 'sleep for', waiting_time, 'seconds'
                    try_request -= 1
                    time.sleep(waiting_time + 20)
                else:
                    try_request = 0
            catalog_info_data = unicode_to_json(catalog_info.text)
        
        # get information of current page
        extract_info(catalog_info_data)
        print 'on page:', page_counter
       
    # storing data to pickle object for next uses
    print 'Storing data started...'
    pickle.dump(infos, open( "data.me", "wb" ))     
    print 'Storing data was successful'
    
"""
This function is for generating analytics (for now, number of courses in each category)
"""
def generate_analytics():
    global infos
    global analytics
    for info in infos:
        if info.category in analytics.category_info.keys():
            analytics.category_info[info.category] += 1
        else:
            analytics.category_info[info.category] = 1

"""
This function is for ploting analytics
"""
def draw_analytics():
    global analytics
    categories = tuple(x for x in analytics.category_info.keys())
    y_pos = np.arange(len(categories))
    numbers_per_cat = [x for x in analytics.category_info.values()]
    plt.bar(y_pos, numbers_per_cat, align='center', alpha=0.5)
    plt.xticks(y_pos, categories)
    locs, labels = plt.xticks()
    plt.setp(labels, rotation=90)
    plt.ylabel('Numbers')
    plt.title('Number of each category')
    plt.show()
    
    
"""
Write to csv file
"""
def write_to_csv():
    global infos
    with open('data.csv', 'wb') as f:
        writer = csv.writer(f)
        
        categories = list()
        descriptions = list()
        titles = list()
        institutes = list()
        instructors = list()
        prices = list()
        sites = list()
        credites = list()
        ids = list()
        
        for info in infos:
            categories.append(info.category)
            descriptions.append(info.description)
            titles.append(info.title)
            institutes.append(info.institute)
            instructors.append(info.instructor)
            prices.append(info.price)
            sites.append(info.site)
            credites.append(info.credit)
            ids.append(info.id)
            
        rows = zip(categories, descriptions, titles, institutes, instructors,
                   prices, sites, credites, ids)
        for row in rows:
            writer.writerow([unicode(s).encode("utf-8") for s in row])
            
    
def main():
    global infos
    global analytics
    access_token = get_access_token()
    
    # get catalogs list
    catalogs_list_data = catalogs_list(access_token)
        
    # extracting all data and storing on data.me file
#    extract_all_info(catalogs_list_data, access_token)
    
    # load the data from pickle file
    infos = pickle.load(open( "data.me", "rb" ))
    
    # This removes duplicates which have same category, description and title
    # API returns duplicates so by means of toolz we can remove them from our data
    infos = toolz.unique(infos, key=lambda x: (x.category, x.description, x.title))
    infos = list(infos)
    
    # generating analytics over the data
    generate_analytics()
    
    # drawing analytics
    draw_analytics()
    
    # write to csv
    write_to_csv()
    
    # running flask server to render html page with information on that      
    app.run()
    
if __name__ == "__main__":
    main()
    
    