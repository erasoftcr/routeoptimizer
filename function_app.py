import azure.functions as func
import logging
import googlemaps
import json

API_KEY = 'AIzaSyCmMAR_zQjkBg5u66GUnou9-AHH7iQvsjQ'  # Replace this with your actual Google Maps API key
gmaps = googlemaps.Client(key=API_KEY)

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

def calculate_route(origin_latlng, waypoints_latlng):
    route = gmaps.directions(
        origin=origin_latlng,
        destination=origin_latlng,
        waypoints=waypoints_latlng,
        mode="driving",
        optimize_waypoints=True
    )
    return route

def get_google_maps_url(origin_latlng, waypoints_latlng, route):
    waypoints_ordered = [waypoints_latlng[idx] for idx in route[0]['waypoint_order']]

    url = "https://www.google.com/maps/dir/"
    waypoints_ordered = [origin_latlng] + waypoints_ordered + [origin_latlng]
    url += "/".join([f"{loc[0]},{loc[1]}" for loc in waypoints_ordered])
    return url

def show_route(origin_name, waypoints_name, route, waypoint_duration):
    duration = 0
    distance = 0
    result = []

    for i, leg in enumerate(route[0]['legs']):
        start = origin_name if i == 0 else waypoints_name[route[0]['waypoint_order'][i - 1]]
        end = origin_name if i == len(waypoints_name) else waypoints_name[route[0]['waypoint_order'][i]]
        origin_lat = leg['start_location']['lat']
        origin_lng = leg['start_location']['lng']
        end_lat = leg['end_location']['lat']
        end_lng = leg['end_location']['lng']
        duration += leg['duration']['value'] + waypoint_duration
        distance += leg['distance']['value']

        result.append({
            "step": i+1,
            "start": start,
            "end": end,
            "distance": leg['distance']['text'],
            "duration": leg['duration']['text'],
            "waze_link": f"https://ul.waze.com/ul?ll={end_lat}%2C{end_lng}&navigate=yes",
            "google_directions_iframe": f"https://www.google.com/maps/embed/v1/directions?key={API_KEY}&origin={origin_lat},{origin_lng}&destination={end_lat},{end_lng}",
            "google_place_iframe": f"https://www.google.com/maps/embed/v1/place?key={API_KEY}&q={end_lat},{end_lng}&zoom=19&maptype=satellite"
        })

    total_distance_km = distance / 1000
    if duration < 3600:
        total_duration = f"{duration / 60:.2f} min"
    else:
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        total_duration = f"{hours} {'hour' if hours == 1 else 'hours'} {minutes} {'min' if minutes == 1 else 'mins'}"

    summary = {
        "total_distance_km": total_distance_km,
        "total_duration": total_duration
    }

    return {"steps": result, "summary": summary}

@app.route(route="calculate_route")
def calculate_route_function(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        # Parse the JSON body from the request
        req_body = req.get_json()
        
        # Extract origin and waypoints
        origin = req_body.get('origin')
        waypoints = req_body.get('waypoints')

        if not origin or not waypoints:
            raise ValueError("Missing origin or waypoints.")

        # Get origin name and lat/lng
        origin_latlng = origin.get('latlng')
        if not origin_latlng:
            raise ValueError("Missing origin latlng.")

        # Get lat/lng of waypoints
        waypoints_latlng = [wp.get('latlng') for wp in waypoints if wp.get('latlng')]

        if not waypoints_latlng:
            raise ValueError("Missing waypoints latlng.")

        # Calculate the route
        route = calculate_route(origin_latlng, waypoints_latlng)

        # Return the route as a JSON response
        return func.HttpResponse(
            json.dumps(route),
            mimetype="application/json",
            status_code=200
        )
    
    except ValueError as e:
        return func.HttpResponse(
            str(e),
            status_code=400
        )
    
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return func.HttpResponse(
            "An internal error occurred.",
            status_code=500
        )

@app.route(route="show_route")
def show_route_function(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        # Parse the JSON body from the request
        req_body = req.get_json()
        
        # Extract origin, waypoints and waypoint_duration
        origin = req_body.get('origin')
        waypoints = req_body.get('waypoints')
        route = req_body.get('route')
        waypoint_duration = req_body.get('waypoint_duration')

        if not origin or not waypoints:
            raise ValueError("Missing origin or waypoints.")

        # Get origin name and lat/lng
        origin_name = origin.get('name')
        if not origin_name:
            raise ValueError("Missing origin name.")
        
        origin_latlng = origin.get('latlng')
        if not origin_latlng:
            raise ValueError("Missing origin latlng.")

        # Get name and lat/lng of waypoints
        waypoints_name = [wp.get('name') for wp in waypoints if wp.get('name')]

        if not waypoints_name:
            raise ValueError("Missing waypoints name.")
        
        waypoints_latlng = [wp.get('latlng') for wp in waypoints if wp.get('latlng')]

        if not waypoints_latlng:
            raise ValueError("Missing waypoints latlng.")

        # Calculate the route
        google_maps_url = get_google_maps_url(origin_latlng, waypoints_latlng, route)
        route = show_route(origin_name, waypoints_name, route, waypoint_duration)
        route["summary"]["google_maps_url"] = google_maps_url

        # Return the route as a JSON response
        return func.HttpResponse(
            json.dumps(route),
            mimetype="application/json",
            status_code=200
        )
    
    except ValueError as e:
        return func.HttpResponse(
            str(e),
            status_code=400
        )
    
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return func.HttpResponse(
            "An internal error occurred.",
            status_code=500
        )
