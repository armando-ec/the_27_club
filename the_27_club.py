# Load packages
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import regex
import geopandas as gpd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import matplotlib.pyplot as plt

# Scrape data using BeautifulSoup
result = requests.get('https://en.wikipedia.org/wiki/27_Club')
soup = BeautifulSoup(result.text, 'html')
table = soup.find('table', {'class': 'wikitable'})
header_row = table.find('tr')
header_birthplace = soup.new_tag('th')
header_birthplace.string = 'Birthplace'
header_row.append(header_birthplace)
headers = [header.text.strip() for header in table.find_all('th')]

rows = []
for row in table.find_all('tr')[1:]:
    cells = row.find_all('td')
    link = cells[0].find('a')
    if link:
        article_title = link['href']
        url = f'https://en.wikipedia.org{article_title}'

        response = requests.get(url, headers={'User-Agent': 'MyWikipediaApp/1.0 (contact: )'}) # Add your email in contact
        
        if response.status_code == 200:
            article_soup = BeautifulSoup(response.content, 'html.parser')
            infobox = article_soup.find('table', {'class': re.compile(r"infobox.*")})

            if infobox:
                birthplace_variable = infobox.find('th', string=re.compile(r'^(Born|Place of birth)$'))
                birthplace_text = birthplace_variable.find_next('td').get_text(strip=True) if birthplace_variable else 'No birthplace field'
                birthplace = regex.split(r'(?r)\d\d\d\d', birthplace_text)[0]
                birthplace = birthplace.replace('[1]', '')
            else:
                birthplace = 'No infobox'
        else:
            birthplace = 'Bad response'
    else:
        birthplace = 'No link'
    
    new_cell = soup.new_tag('td')
    new_cell.string = birthplace
    cells.append(new_cell)

    row_data = [cell.text.strip() for cell in cells]
    rows.append(row_data)

# Add the data into a dataframe
df = pd.DataFrame(rows, columns=headers)

# Check the data for missing birthplaces
no_birthplace_df = df.loc[df['Birthplace'].isin(['No birthplace field', 'No infobox', 'Bad response', 'No link']), 'Name']
no_birthplace_df

# Add the missing birthplaces into a list
missing_birthplace_list = [
    'Como, Mississippi, U.S.',
    'Butte, Montana, U.S.',
    'Buffalo, New York, U.S.',
    'Kansas City, Missouri, U.S.',
    'Phoenix, Arizona, U.S.',
    'London, England',
    'Sofia, Bulgaria',
    'New York, New York, U.S.',
    'Philadelphia, Pennsylvania, U.S.',
    'Duisburg, Germany',
    'Saint Louis Park, Minnesota, U.S.',
    'Geelong, Australia',
    'Houston, Texas, U.S.',
    'Leeds, England',
    'Vienna, Austria',
    'Warrington, England',
    'West Palm Beach, Florida, U.S.',
    'Woodland Hills, California, U.S.',
    'Moscow, Russia',
    'Gyeonggi-do, South Korea',
    'Saint Petersburg, Russia',
    'Mexico City, Mexico'
]

# Match the rows with no birthplace to the correct birthplace
name_birthplace_dict = dict(zip(no_birthplace_df, missing_birthplace_list))

# Add the missing birthplace to the dataframe
df.loc[df['Name'].isin(no_birthplace_df), 'Birthplace'] = df.loc[df['Name'].isin(no_birthplace_df), 'Name'].map(name_birthplace_dict)

# Create new columns to add the Location, Latitude and Longitude to every row
geolocator = Nominatim(user_agent='city_locator')
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

df['Location'] = df['Birthplace'].apply(geocode)
df['Latitude'] = df['Location'].apply(lambda loc: loc.latitude if loc else None)
df['Longitude'] = df['Location'].apply(lambda loc: loc.longitude if loc else None)

# Check the data for rows missing location
no_geocode = df[df['Location'].isna()][['Name', 'Birthplace']]
no_geocode

# Add the correct birthplace names into a list
corrected_birthplace_list = [
    'São Paulo, Brazil',
    'Mecca, Saudi Arabia',
    'Šilutė, Lithuania',
    'Cherepovets, Russia',
    'Ho Chi Minh City, Vietnam',
    'Prague, Czech Republic',
    'Srbac, Bosnia and Herzegovina',
    'Saint Petersburg, Russia',
    'Petropavl, Kazakhstan'
]

# Match the rows with location to the correct location
corrected_birthplace_dict = dict(zip(no_geocode['Name'], corrected_birthplace_list))

# Add the correct birthplac names into the dataframe of rows with no location
no_geocode['Corrected Birthplace'] = no_geocode['Name'].map(corrected_birthplace_dict)

# Add location to the missing rows and add it to the main dataframe
no_geocode['Corrected Location'] = no_geocode['Corrected Birthplace'].apply(geocode)
corrected_location_dict = dict(zip(no_geocode['Name'], no_geocode['Corrected Location']))
df.loc[df['Location'].isna(), 'Location'] = df.loc[df['Location'].isna(), 'Name'].map(corrected_location_dict)

# Add the missing latitude and longitude
mask = df['Latitude'].isna() & df['Location'].notna()

df.loc[mask, 'Latitude'] = df.loc[mask, 'Location'].apply(lambda loc: loc.latitude)
df.loc[mask, 'Longitude'] = df.loc[mask, 'Location'].apply(lambda loc: loc.longitude)

# Check if any rows are missing longitude or latitude
df.loc[df['Longitude'].isna()]
df.loc[df['Latitude'].isna()]

# Create map
world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
world = world[world['name'] != 'Antarctica']

fig, ax = plt.subplots(figsize=(12, 8))
world.plot(ax=ax, color='lightgrey', edgecolor='black', linewidth=0.2)

ax.scatter(df['Longitude'], df['Latitude'], color='#CE4257', s=10)
ax.axis('off')

plt.subplots_adjust(left=0, right=1, top=0.95, bottom=0.05)

plt.title('The 27 Club')
plt.savefig('27_club_map.png', bbox_inches='tight', pad_inches=0, dpi=700)
plt.show()