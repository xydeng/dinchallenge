import time
import urllib2
import json
import re
import os
import numpy
import pandas as pd
#pd.set_option('display.mpl_style','default')  
import matplotlib.pyplot as plt
import statsmodels.api as sm

toQuery=u'chinese+restaurants'
CLIENT_ID = u'DRMPAVUGVDAIRP0NRQKABOGL0PZVS4EJF5P1KG2MO0ENH0TI'
CLIENT_SECRET = u'BPTJ1IU4SFK2FCYJGVWECHAMI1HIXB4PYX3QTHC4LPGE4INP'


def search(lat, lng, distance):
    """
    Searches the Foursquare API (Max Limit = 50)

    :param lat: Latitude of the request
    :param long: Longitude of the request
    :param distance: Distance to search (meters)
    :returns: List of retrieved venues
    """

    #url = 'https://api.foursquare.com/v2/venues/search?ll=%s,%s&intent=browse&radius=%s&limit=50&categoryId=%s&client_id=%s&client_secret=%s&v=%s' % (lat, lng, distance, CATEGORY_ID, CLIENT_ID, CLIENT_SECRET, time.strftime("%Y%m%d"))
    #url = 'https://api.foursquare.com/v2/venues/search?ll=%s,%s&radius=%s&limit=50&categoryId=%s&client_id=%s&client_secret=%s&v=%s' % (lat, lng, distance, CATEGORY_ID, CLIENT_ID, CLIENT_SECRET, time.strftime("%Y%m%d"))
    url = 'https://api.foursquare.com/v2/venues/search?ll=%s,%s&intent=browse&radius=%s&limit=50&query=%s&client_id=%s&client_secret=%s&v=%s' % (lat, lng, distance, toQuery, CLIENT_ID, CLIENT_SECRET, time.strftime("%Y%m%d"))
    venue_list = []

    data = make_request(url)
    venue_list=data['response']['venues']

    return venue_list

def searchnearby(Query=toQuery,nearby='Bergen'):
    """
    Searches the Foursquare API near a county
    :returns: List of retrieved venues
    """

    url = 'https://api.foursquare.com/v2/venues/search?near=%s&intent=browse&limit=40&query=%s&client_id=%s&client_secret=%s&v=%s' % (nearby, toQuery, CLIENT_ID, CLIENT_SECRET, time.strftime("%Y%m%d"))
    venue_list = []

    data = make_request(url)
    venue_list=data['response']['venues']
    #print venue_list
   
    df_v=pd.DataFrame.from_records(venue_list)
    if df_v.empty:
        return df_v
    #df=df_v[df_v[u'verified']]
    df=df_v
    #print df.columns
    df1=df[[u'name',u'referralId']].copy()
    #print type(df[u'location'].apply(lambda x: x[u'postalCode']))
    #df1.loc[:,u'zipcode']=df[u'location'].apply(lambda x: x[u'postalCode'])
    #df1.loc[:,u'city']=df[u'location'].apply(lambda x: x[u'city'])
    #print df
    #df1.loc[:,u'address']=df[u'location'].apply(lambda x: x[u'address'])
    #print df1
    return df1

def make_request(url):
    """
    Makes a new HTTP request to the given URL

    :param url: The URL to request
    :returns: JSON response
    """

    req = urllib2.Request(url)
    response = urllib2.urlopen(req)
    data = json.loads(response.read())
    response.close()

    return data


def getCensusdf(fname='asianbymcd.xls'):
    """ get chinese people population
    """
    census_tmp=pd.read_excel(fname,sheetname='2010',parse_cols='A,B,I,T',skiprows=3,header=0)[1:588]
    
    #print census_tmp
    # modify data and set county as a new column
    df_county=census_tmp[census_tmp['Area Name'].str.match(r'.*County')]
    df_twp=census_tmp[census_tmp['Area Name'].str.match(r'.* (?!County)')].copy()
    ## add a new column to df_twp with the corresponding county
    df_county.set_index('County',inplace=True)
    #print df_county.ix['34001']
    df_twp['County name']=df_twp['County'].apply(lambda x:df_county.ix[x,'Area Name'])
    df_twp['Chinese']=df_twp['(except Taiwanese)']+df_twp['Taiwanese']
    #print df_twp.sum()
    return df_twp

def getNresPerTwp(df_twp,saveto=None):
    """ get the Number of restaurants near each township
    In principle I need to get rid of duplicates. However due to the time limit I will simply take the nearby searched on as the value of the specific twp. This is crude estimate.
    """
    df=df_twp.copy()
    twp=df_twp['Area Name']
    nres=[]
    for itwp in twp:
        twpname=itwp
        if twpname.rsplit(' ',1)[1]!='township':
            twpname=twpname.rsplit(' ',1)[0]
        if twpname in ['Saddle Brook township','Maplewood township','Robbinsville township','Toms River township']:
            twpname=twpname.rsplit(' ',1)[0]            
        twpname=re.sub('\ ','+',twpname)+"+NJ"
        
        #print twpname
        venue_df=searchnearby(nearby=twpname)
        nres.append(len(venue_df.index))
    df['Nres']=pd.Series(nres,index=df.index)	
    if saveto is not None:
        df.to_csv(saveto)
    return df

def analysis(df):
    """ do some analysis and plot
    """

    ### Plot population versus Nres for every township
    #print df['Chinese'].tolist()
    # rename columns
    df1=df.rename(columns={'Chinese':'Chinese Population','Nres':'Num of Chinese Restaurants'})
    #df1.plot(x='Chinese Population',y='Num of Chinese Restaurants',kind='scatter')
    #plt.show()

    x=df1['Chinese Population'].values
    X=sm.add_constant(x)
    #X=x
    y=df1['Num of Chinese Restaurants'].values
    resfit=sm.OLS(y,X).fit()
    print "OLS model for the number of restaurants versus population in each Township (total %s)."%len(df1)
    print resfit.summary()

    if True:  #Plot
        fig, ax = plt.subplots(figsize=(8,6))
        ax.plot(x, y, 'o', label="data of all township")
        ax.plot(x, resfit.fittedvalues, 'r--.', label="OLS Fit")
        ax.set_xlabel("Population of Chinese")
        ax.set_ylabel("Num of Chinese Restaurants")        
        ax.legend(loc='best')
        plt.savefig("NumVerPopu_Twp.png")
        plt.show()


    ### Plot population versus Nres for every County
    df2=df1.groupby('County name',as_index=False).sum()#['Chinese Population','Num of Chinese Restaurants']
    x=df2['Chinese Population'].values
    X=sm.add_constant(x)
    #X=x
    y=df2['Num of Chinese Restaurants'].values
    resfit=sm.OLS(y,X).fit()
    print "OLS model for the number of restaurants versus population in each County (total %s)."%len(df2)
    print resfit.summary()
    if True:  #Plot
        fig, ax = plt.subplots(figsize=(14,5))
        ax.plot(x, y, 'ko', markersize=10,label="data of all County")
        ax.plot(x, resfit.fittedvalues, 'k-.',lw=3, label="OLS Fit")
        ax.set_xlabel("Population Of Chinese")
        ax.set_ylabel("Num of Chinese Restaurants")        
        ax.legend(loc='best')
        plt.savefig("NumVerPopu_County.png")
        plt.show()

    if True:  #Plot Residue
        fig, ax = plt.subplots(figsize=(14,6))
        #ax.plot(x, y, 'o', label="data of all County")
        xvalue=numpy.arange(len(df2.index))
        #print xvalue
        ax.bar(xvalue, resfit.resid,width=0.5, label="residue")
        xticklabels=df2['County name'].str.split().str[0]
        #ax.set_xticklabels(xticklabels,rotation=90)
        plt.xticks(xvalue,xticklabels,rotation=90)
        ax.set_ylabel("OLS Residue of Num of Chinese Restaurants")
        ax.set_xlim(0,len(df2.index))
        ax.legend(loc='best')
        plt.subplots_adjust(bottom=0.20)
        plt.savefig("Residue_NumVerPopu_County.png")
        plt.show()

    ### Plot population versus Nres for every County, with dummy variables.
    ### above analysis suggests that North Jersey has a large ratior of number of restaurants versus populatons. Let us check.
    #### I will put put geo category to denote if a County belongs to North Jersy (1), Central Jersy (2), South Jersey (3). Data from Wikipedia.
    #NorthJersey=['Bergen County','Essex County','Hudson County','Morris County','Passaic County','Sussex County','Union County','Warren County']
    #CentralJersey=['Middlesex County','Somerset County','Monmouth County','Mercer County','Hunterdon County','Ocean County']
    #SouthJersey=['Atlantic County','Burlington County','Camden County','Cape May County','Cumberland County','Gloucester County','Salem County']
    geocode={1:'North Jersey',2:'Central Jersey',3:'South Jersey'}
    geolist={'Bergen County':1,'Essex County':1,'Hudson County':1,'Morris County':1,'Passaic County':1,'Sussex County':1,'Union County':1,'Warren County':1,'Middlesex County':2,'Somerset County':2,'Monmouth County':2,'Mercer County':2,'Hunterdon County':2,'Ocean County':2,'Atlantic County':3,'Burlington County':3,'Camden County':3,'Cape May County':3,'Cumberland County':3,'Gloucester County':3,'Salem County':3}
    df3=df2.copy()
    df3['geocode']=df3['County name'].map(geolist)
    #print df3
    fig, ax = plt.subplots(figsize=(10,5))
    colors=['r','b','c']
    styles=['ro','b*','cd']
    for i in geocode:
        df4=df3[df3['geocode']==i]
        x=df4['Chinese Population'].values
        X=sm.add_constant(x)
        #X=x
        y=df4['Num of Chinese Restaurants'].values
        resfit=sm.OLS(y,X).fit()
        print "OLS model for the number of restaurants versus population in each County of %s."%geocode[i]
        print resfit.summary()
        ax.plot(x, y, '%s'%styles[i-1],markersize=10,label="data for %s"%geocode[i])
        ax.plot(x, resfit.fittedvalues, '%s-.'%colors[i-1], lw=3,label="OLS Fit for %s"%geocode[i])


                
    ax.set_xlabel("Population of Chinese")
    ax.set_ylabel("Num of Chinese Restaurants")        
    ax.legend(loc='best')
    plt.savefig("NumVerPopu_County_geo.png")
    plt.show()

    
if __name__=="__main__":
    #venue_list=search(40.940693, -74.124243,5000)
    #venue_list=searchnearby(County="Bergen+County+NJ")
    #venue_df=searchnearby(nearby="Washington+township+NJ")
    #venue_df=searchnearby(nearby="Saddle+Brook+NJ")
   
    dfname='nres_twp.csv'
    ### Prepare data, this is done only once if the data is absent
    if not (os.path.isfile(dfname) and os.path.getsize(dfname) > 0):
        # extract Census data from excel file
    	df_twp=getCensusdf(fname='asianbymcd.xls')
        # for every township, extract the number of restaurants with foursquare API
        # create a new df with this data and save to file
	df=getNresPerTwp(df_twp,saveto=dfname)
    else:
	df=pd.read_csv(dfname)

    ### analysis
    analysis(df)

    


	
