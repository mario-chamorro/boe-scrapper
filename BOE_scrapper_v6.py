# -*- coding: utf-8 -*-

import urllib 
from bs4 import BeautifulSoup 
import os 
import re 
import csv 
import pandas as pd 
import datetime 
import numpy as np 
import tweepy 
from credentials import *

source = "https://www.boe.es/boe/dias/"
downloadUrl = "https://www.boe.es"
files = []
meses = ("enero", "febrero", "marzo",
         "abril","mayo","junio",
         "julio","agosto", "septiembre",
         "octubre","noviembre","diciembre")


# Get a list of BOE PDF files on a given date
def get_PDF_list(date):
    files = []
    year = date[0:4]
    month = date[4:6]
    monthFixed = "{0:0=2d}".format(int(month)) # Convert to 01, 02, 03 format
    day = str(date[6:])
    dayFixed = day.zfill(2)
    url = source + year + "/" + monthFixed + "/" + dayFixed + "/index.php?t=c"
#     print(url)

    page = urllib.request.urlopen(url)
    soup = BeautifulSoup(page, "html5lib")
    # Look for all pdfs in page
    pdfs =  soup.findAll(attrs={"class":"puntoPDF"})
    for pdf in pdfs:
        file = pdf.find("a").text
        files.append(file)

    return files


# Returns a list of number of pages per BOE file (in boe files list) on a given date
def get_number_of_pages(date):
    files = get_PDF_list(date)
    pageNumberList = []

    for i in files:
        pageNumberString = re.search(" - .+ pág", i)
        if pageNumberString is None: # Needed in case element doesn´t show number of pages
            pageNumberList.append(np.NaN)
        else:
            pageNumberString = pageNumberString.group()
            pageNumber = re.search("\d+", pageNumberString).group()
            pageNumberList.append(int(pageNumber))
    return pageNumberList


# Daily function that gets the number of pages published in the desired "date"
def get_daily_pages(date):
    year = date[0:4]
    month = int(date[4:6])
    day = str(date[6:])

    pagesInDayDataFrame = pd.DataFrame(get_number_of_pages(date))
    pagesInDay = int(pagesInDayDataFrame.sum())

    message = ("Hoy, día " + str(day) + " de " + str(meses[month - 1]) +
          " de " + str(year) + ", se han publicado " +
          str(pagesInDay) + " páginas en el BOE")
    return message


# Daily function that gets the number of pages published in BOE in the current day
def get_today_pages():
    year = str(pd.Timestamp.today().year)
    month = str(pd.Timestamp.today().month).zfill(2)
    day = str(pd.Timestamp.today().day).zfill(2)
    # day = str(20)
    date = str(year + month + day)

    day_of_week = pd.Timestamp.today().dayofweek
    # day_of_week = 1

    if (day_of_week == 6):
        message = ("Hoy es domingo, el BOE descansa")
        return message
    elif (day_of_week != 6):
        pagesInDayDataFrame = pd.DataFrame(get_number_of_pages(date))
        pagesInDay = int(pagesInDayDataFrame.sum())
        message = ("Hoy, día " + day + " de " + str(meses[int(month) - 1]) + " de " + year + ", se han publicado " + str(pagesInDay) + " páginas en el BOE")
        return message


# Update yearly csv until the current day
def update_yearly_csv():
    files = []
    pageNumberList = []
    dates = []
    year = str(pd.Timestamp.today().year)

    # Read csv and get the range of dates to process
    csvfile = open("csv/" + year + ".csv", "r", encoding = "latin-1")
    row_count = (sum(1 for row in csvfile) - 1)
    csvfile.close()

    csvfile = open("csv/" + year + ".csv", "r", encoding = "latin-1")
    reader = csv.DictReader(csvfile)
    last_line = list(reader)[-1]

    startDate = pd.to_datetime(last_line["date"]) + datetime.timedelta(days=1)
    end_date = pd.Timestamp.today()
    daterange = pd.date_range(startDate, end_date)

    if (end_date.day - startDate.day) == -1:
        print("Everything is up to date. Nothing was processed.")
    else:
        # Loop through the days and get BOE files and number of pages
        for single_date in daterange:
            day = str(single_date.day).zfill(2)
            month = str(single_date.month).zfill(2)
            year = str(single_date.year)
            date = year + month + day

            try:
                files.extend(get_PDF_list(date))
                pageNumberList.extend(get_number_of_pages(date))
                numberOfFilesInDay = len(get_PDF_list(date))
                for i in range (0, numberOfFilesInDay):
                    dates.append(date)
            except:
                print("Error en el día " + date + " (!!!)")
                continue
            print("Procesado día " + date)

        # Create dataframe with all the data
        dataframe = pd.DataFrame()

        dataframe["date"] = dates
        dataframe["files"] = files
        dataframe["pages"] = pageNumberList
        dataframe.index = np.arange(row_count, row_count + len(files))


        # Append gathered data to the csv
        dataframe.to_csv("csv/" + str(year) + ".csv", mode="a", header=False)

        return dataframe


# Calculate the total pages published in BOE during the ongoing year
def get_yearly_pages():
    year = str(pd.Timestamp.today().year)
    dataframe = pd.read_csv("csv/" + year + ".csv", encoding='latin-1')
    total_pages = dataframe["pages"].sum()
    # total_pages = format(total_pages, "8d")
    total_pages = "{:,.0f}".format(total_pages)
    message = ("En lo que llevamos de año, se han publicado " + str(total_pages) + " paginas en el BOE")
    return message


# Access and authorize our Twitter credentials from credentials.py
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

tweet_today_pages = get_today_pages()
tweet_yearly_pages = get_yearly_pages()

def tweet_today():
    api.update_status(tweet_today_pages)

def tweet_yearly():
    api.update_status(tweet_yearly_pages)
