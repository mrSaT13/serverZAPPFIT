def make_strava_activity(
    activity_id: int = 1,
    name: str = "Morning Run",
    sport_type: str = "Run",
    distance: float = 10000.0,
    moving_time: int = 3600,
    total_elevation_gain: float = 50.0,
    start_date: str = "2024-01-15T08:00:00Z",
    timezone: str = "UTC",
    gear_id: str = "g12345",
):
    return {
        "id": activity_id,
        "name": name,
        "sport_type": sport_type,
        "distance": distance,
        "moving_time": moving_time,
        "total_elevation_gain": total_elevation_gain,
        "start_date": start_date,
        "start_date_local": start_date,
        "timezone": timezone,
        "gear_id": gear_id,
        "average_heartrate": 145.0,
        "max_heartrate": 175.0,
        "average_speed": 2.78,
        "max_speed": 5.0,
        "calories": 500.0,
        "description": "",
    }


def make_strava_gear(gear_id: str = "g12345", name: str = "Nike Pegasus", distance: float = 500000.0):
    return {
        "id": gear_id,
        "name": name,
        "distance": distance,
        "brand_name": "Nike",
        "model_name": "Pegasus",
        "primary": False,
    }


def make_strava_athlete(
    athlete_id: int = 12345,
    firstname: str = "Test",
    lastname: str = "User",
    measurement_preference: str = "meters",
):
    return {
        "id": athlete_id,
        "firstname": firstname,
        "lastname": lastname,
        "measurement_preference": measurement_preference,
    }
