from flask import Flask, render_template, request
import requests
import logging
import math

app = Flask(__name__)

API_KEY = 'ENTER YOUR GOOGLE API KEY'
PLACES_API_URL = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
DETAILS_API_URL = 'https://maps.googleapis.com/maps/api/place/details/json'
GEOCODE_API_URL = 'https://maps.googleapis.com/maps/api/geocode/json'
DISTANCE_MATRIX_API_URL = 'https://maps.googleapis.com/maps/api/distancematrix/json'

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def geocode_address(address):
    """Convert address to latitude and longitude."""
    params = {
        'address': address,
        'key': API_KEY
    }
    logging.debug(f"Geocoding request parameters: {params}")
    response = requests.get(GEOCODE_API_URL, params=params)
    logging.debug(f"Geocoding API response status code: {response.status_code}")
    logging.debug(f"Geocoding API response: {response.text}")
    
    results = response.json().get('results', [])
    if results:
        location = results[0]['geometry']['location']
        return location['lat'], location['lng']
    return None, None

def get_nearby_restaurants(lat, lng, radius=1000, type='restaurant'):
    """Fetch nearby restaurants."""
    params = {
        'location': f"{lat},{lng}",
        'radius': radius,
        'type': type,
        'key': API_KEY
    }
    logging.debug(f"Nearby restaurants request parameters: {params}")
    response = requests.get(PLACES_API_URL, params=params)
    logging.debug(f"Nearby restaurants API response status code: {response.status_code}")
    logging.debug(f"Nearby restaurants API response: {response.text}")
    
    results = response.json().get('results', [])
    return results

def get_place_details(place_id):
    """Fetch detailed information about a place."""
    params = {
        'place_id': place_id,
        'key': API_KEY
    }
    logging.debug(f"Place details request parameters: {params}")
    response = requests.get(DETAILS_API_URL, params=params)
    logging.debug(f"Place details API response status code: {response.status_code}")
    logging.debug(f"Place details API response: {response.text}")
    
    details = response.json().get('result', {})
    reservation_link = details.get('website')
    
    # Get price level and convert to range
    price_level = details.get('price_level', None)
    details['price_range'] = get_price_range(price_level)
    
    return details, reservation_link

def get_price_range(price_level):
    """Map price level to approximate price range."""
    price_ranges = {
        0: "$0",
        1: "$10-$20",
        2: "$21-$40",
        3: "$41-$60",
        4: "$61+"
    }
    return price_ranges.get(price_level, "N/A")

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate the distance between two lat/lon coordinates in miles."""
    # Using Haversine formula to calculate distance
    R = 3958.8  # Radius of Earth in miles
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_travel_times(orig_lat, orig_lng, dest_lat, dest_lng):
    """Get travel times by walking, driving, and public transit using Google Distance Matrix API."""
    params = {
        'origins': f"{orig_lat},{orig_lng}",
        'destinations': f"{dest_lat},{dest_lng}",
        'mode': 'driving',  # Default mode for driving
        'key': API_KEY
    }
    response_driving = requests.get(DISTANCE_MATRIX_API_URL, params=params)
    
    params['mode'] = 'walking'
    response_walking = requests.get(DISTANCE_MATRIX_API_URL, params=params)
    
    params['mode'] = 'transit'
    response_transit = requests.get(DISTANCE_MATRIX_API_URL, params=params)
    
    results_driving = response_driving.json()
    results_walking = response_walking.json()
    results_transit = response_transit.json()
    
    times = {
        'driving': results_driving['rows'][0]['elements'][0]['duration']['text'],
        'walking': results_walking['rows'][0]['elements'][0]['duration']['text'],
        'transit': results_transit['rows'][0]['elements'][0]['duration']['text']
    }
    
    return times

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        address = request.form['address']
        lat, lng = geocode_address(address)
        if lat and lng:
            restaurants = get_nearby_restaurants(lat, lng)
            top_restaurants = restaurants[:3]  # Get top 3 restaurants
            restaurant_details = []
            for restaurant in top_restaurants:
                place_id = restaurant.get('place_id')
                details, reservation_link = get_place_details(place_id)
                details['distance'] = calculate_distance(lat, lng, restaurant['geometry']['location']['lat'], restaurant['geometry']['location']['lng'])
                details['travel_times'] = get_travel_times(lat, lng, restaurant['geometry']['location']['lat'], restaurant['geometry']['location']['lng'])
                details['reservation_link'] = reservation_link
                restaurant_details.append(details)
            return render_template('results.html', restaurants=restaurant_details, API_KEY=API_KEY)
        else:
            return render_template('index.html', error="Unable to geocode address. Please check the address and try again.")
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)
