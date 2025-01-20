from flask import Flask, render_template, request, jsonify, redirect, session
from requests import get, post
import requests
import os
import base64
import json
import random
import urllib.parse
from datetime import datetime, timedelta
from dotenv import load_dotenv

# import logging
# logging.basicConfig(level=logging.DEBUG)

# flask app initialization
app = Flask(__name__)

# environment variables
load_dotenv()
client_id = os.getenv("CLIENT_ID")  # client_id for spotify api
client_secret = os.getenv("CLIENT_SECRET")  # client_secret for spotify api
app.secret_key = os.getenv("SECRET_KEY")    # secret key for flask app
redirect_uri = "http://127.0.0.1:5000/callback" # redirect uri 
auth_url = "https://accounts.spotify.com/authorize"
api_base_url = "https://api.spotify.com/v1/"
token_url = "https://accounts.spotify.com/api/token"

app.config["SESSION_COOKIE_SECURE"] = False  # SWITCH TO TRUE IF IN PRODUCTION WITH HTTPS
app.config["SESSION_COOKIE_HTTPONLY"] = True    
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"   # controls whether session cookie should be sent to cross site requests

# get spotify API token
def get_token():
    auth_string = f"{client_id}:{client_secret}"
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")

    headers = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}

    # make the API request
    result = post(token_url, headers=headers, data=data)

    # API responses for debugging
    print(f"Spotify API Response Status Code: {result.status_code}")
    print(f"Spotify API Response Content: {result.content}")

    # handle errors gracefully
    if result.status_code != 200:
        raise ValueError("Failed to retrieve access token from Spotify API.")

    # parse and return the access token
    token = json.loads(result.content).get("access_token")
    if not token:
        raise KeyError("No access_token found in Spotify API response.")
    return token

# construct authorization header
def get_auth_header(token):
    return {"Authorization": f"Bearer {token}"}

# login to user spotify account
@app.route("/login")
def login():

    print("Redirecting to Spotify login...")
    print("Session contents:", session)  # Debugging session

    scope = "playlist-modify-private"
    params = {
        "client_id": client_id,
        "response_type": 'code',
        "scope": scope,
        "redirect_uri": redirect_uri,
        "show_dialog": True
    }
    authorization_url = f"{auth_url}?{urllib.parse.urlencode(params)}"
    print(f"Redirecting to Spotify login URL: {authorization_url}")  # Debugging log
    return redirect(authorization_url)

# callback to spotify after login
@app.route("/callback")
def callback():
    if "error" in request.args:
        return jsonify({"error": request.args["error"]})

    if "code" in request.args:
        req_body = {
            "code": request.args["code"],
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        response = requests.post(token_url, data=req_body)
        token_info = response.json()

        # Store token info in session
        session["access_token"] = token_info.get("access_token")
        session["refresh_token"] = token_info.get("refresh_token")
        session["expires_at"] = datetime.now().timestamp() + token_info.get("expires_in", 0)

        # Retrieve playlist from session
        playlist = session.get("playlist", [])
        session["playlist"] = playlist  # Re-store to ensure persistence

        # Redirect to the page specified before login
        redirect_url = session.pop("redirect_after_login", "/start")
        preserve_state = session.pop("preserve_state", False)

        if preserve_state:
            return redirect(redirect_url)

    return redirect("/start")



# search Spotify API
def search_spotify(token, query):
    url = "https://api.spotify.com/v1/search"
    headers = get_auth_header(token)
    params = {
        "q": query,
        "type": "artist",
        "limit": 5
    }
    response = get(url, headers=headers, params=params)
    return response.json()

# fetch top tracks for selected artists
def fetch_artist_tracks(token, artist_id):
    tracks = []
    headers = get_auth_header(token)

    # fetch artist's albums
    url = f"https://api.spotify.com/v1/artists/{artist_id}/albums"
    params = {"include_groups": "album,single,appears_on,compilation", "limit": 15}  # fetch up to 15 albums
    albums_response = get(url, headers=headers, params=params).json()   # request artist albums in json
    albums = albums_response.get("items", [])   # parse json

    # fetch tracks from each album
    for album in albums:
        album_id = album["id"]
        album_tracks_url = f"https://api.spotify.com/v1/albums/{album_id}/tracks"
        album_tracks_response = get(album_tracks_url, headers=headers).json()   # request tracks from album in json

        # fetch track information to find popularity
        for track in album_tracks_response.get("items", []):
            track_url = f"https://api.spotify.com/v1/tracks/{track['id']}"
            track_details = get(track_url, headers=headers).json()  # request track details in json

            # get details for each track that has a popularity > 30 and < 80
            # does not add the most popular tracks in playlist (> 80)
            if track_details.get("popularity", 0) > 30 & track_details.get("popularity", 0) < 80: 
                tracks.append({
                    "name": track_details["name"],
                    "artist": ", ".join([artist["name"] for artist in track_details["artists"]]),
                    "album": track_details["album"]["name"],
                    "image": track_details["album"]["images"][0]["url"] if track_details["album"]["images"] else None,
                    "popularity": track_details["popularity"],
                    "uri": track_details["uri"]
                })
    return tracks

# creates playlist based on artist chosen
@app.route("/create_playlist", methods=["POST"])
def create_playlist():
    artist_ids = request.json.get("artist_ids", [])
    if not artist_ids:
        return jsonify({"error": "No artists selected"}), 400

    token = get_token()
    all_tracks = []

    # fetch tracks for each artist
    for artist_id in artist_ids:
        artist_tracks = fetch_artist_tracks(token, artist_id)
        print(f"Artist {artist_id} has {len(artist_tracks)} tracks.")  # debug log
        all_tracks.append(artist_tracks)

    # target total number of songs, random number between 20 to 30
    max_songs = random.randint(20, 30)
    num_artists = len(artist_ids)
    songs_per_artist = max_songs // num_artists

    # collect tracks for the playlist
    playlist = []
    remaining_slots = max_songs

    # distribute tracks evenly among artists
    for artist_tracks in all_tracks:
        if remaining_slots <= 0:
            break
        num_tracks = min(songs_per_artist, len(artist_tracks))
        playlist.extend(random.sample(artist_tracks, num_tracks))
        remaining_slots -= num_tracks
        print(f"Selected {num_tracks} tracks from an artist. Remaining slots: {remaining_slots}")  # debug log

    # fill remaining slots with random tracks from all artists (mixed)
    flat_tracks = [track for artist_tracks in all_tracks for track in artist_tracks]
    random.shuffle(flat_tracks)  # shuffle tracks for a mixed selection
    remaining_tracks = [track for track in flat_tracks if track not in playlist]
    if remaining_slots > 0:
        playlist.extend(random.sample(remaining_tracks, min(remaining_slots, len(remaining_tracks))))
        print(f"Added {remaining_slots} remaining tracks from a mix of all artists.")  # debug log

    # shuffle final playlist to mix tracks from all artists
    random.shuffle(playlist)

    # log popularity for debugging
    for track in playlist:
        print(f"Track: {track['name']} | Popularity: {track['popularity']}")  # debug log

    # limit playlist to the maximum number of songs
    playlist = playlist[:max_songs]
    print(f"Final playlist has {len(playlist)} tracks.")  # debug log
    print(f"Session data at /create_playlist: {session}")   # debug log

    session["playlist"] = playlist  # store playlist in current session
    session.modified = True # save the session data back to client
    print(f"Playlist stored in session: {session.get('playlist')}") # debug log
    return jsonify({"playlist": playlist})

# exports the playlist generated to user spotify account
@app.route("/export_playlist")
def export_playlist():
    
    playlist = session.get("playlist") 

    if not playlist:
        print("No playlist in session.")  # Debug log
        return jsonify({"error": "No playlist available to export"}), 400

    # check if user is logged in
    access_token = session.get("access_token")
    if not access_token:
        # Save the redirect path and redirect to login
        session["redirect_after_login"] = "/start"
        session["preserved_state"] = True
        session.modified = True  # Ensure session changes are saved
        # print(f"Redirecting to login. Playlist in session: {playlist}")
        return jsonify({"error": "Please log in to export the playlist."}), 401

    # check if playlist has already been exported
    if "exported_playlist_id" in session:
        playlist_id = session["exported_playlist_id"]
        playlist_url = f"https://open.spotify.com/playlist/{playlist_id}"
        return jsonify({"playlist_url": playlist_url}), 200


    # if user is logged in, proceed to export playlist
    headers = get_auth_header(access_token)
    user_profile_response = get(f"{api_base_url}me", headers=headers)   # grabs user profile
    if user_profile_response.status_code != 200:
        return jsonify({"error": "Failed to fetch user profile"}), 400

    user_profile = user_profile_response.json()
    user_id = user_profile.get("id")    # get user id
    if not user_id:
        return jsonify({"error": "User ID not found"}), 400

    # create spotify playlist
    create_playlist_body = {
        "name": f"Generated Playlist {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "description": "A playlist generated by \"Playlist Generator for Spotify\"",
        "public": False
    }
    create_playlist_response = post(
        f"{api_base_url}users/{user_id}/playlists",
        headers=headers,
        json=create_playlist_body
    )
    if create_playlist_response.status_code != 201:
        return jsonify({"error": "Failed to create playlist"}), 400

    created_playlist = create_playlist_response.json()
    playlist_id = created_playlist.get("id")    # grab id of playlist
    playlist_url = created_playlist.get("external_urls", {}).get("spotify", "#")

    # store the playlist ID in sesssion to prevent duplicates
    session["exported_playlist_id"] = playlist_id

    # insert all track uris to spotify playlist
    track_uris = [track.get("uri") for track in playlist if track.get("uri")]
    if not track_uris:
        return jsonify({"error": "No valid track URIs found in the playlist"}), 400

    chunk_size = 100    # spotify api allows a max of 100 tracks to be added to a playlist in a single request
    # goes from 0 to how many tracks the playlist has, ensuring each iteration processes up to 100 tracks at a time
    for i in range(0, len(track_uris), chunk_size):
        chunk = track_uris[i:i + chunk_size]    # extracts a slice of track_uris containing at most 100 uris
        # request to spotify API
        add_tracks_response = post(
            f"{api_base_url}playlists/{playlist_id}/tracks",
            headers=headers,
            json={"uris": chunk}
        )
        if add_tracks_response.status_code != 201:
            return jsonify({"error": "Failed to add tracks to playlist"}), 400
        
    # # clear playlist after successful export
    # session.pop("playlist", None)

    # return jsonify({
    #     "message": "Playlist exported successfully!",
    #     # "playlist_url": created_playlist.get("external_urls", {}).get("spotify", "#")
    # })

    return jsonify({"playlist_url": playlist_url}), 200

# home route
@app.route("/start", methods=["GET", "POST"])
def index():
    playlist = session.get("playlist", [])  # Retrieve the playlist from the session
    success = request.args.get("success", default=None)
    playlist_url = request.args.get("playlist_url", default=None)
    artists = session.get("artists", [])

    if request.method == "POST":
        query = request.form.get("content", "") # get user search input
        if not query:
            return render_template("index.html", error="Please enter a search term.", playlist=playlist, artists=artists, success=success, playlist_url=playlist_url)

        token = get_token()
        results = search_spotify(token, query)

        # extract artist information
        artists = [
            {
                "name": artist["name"],
                "id": artist["id"],
                "image": artist["images"][0]["url"] if artist["images"] else "https://via.placeholder.com/100"
            }
            for artist in results.get("artists", {}).get("items", [])
        ]
        session["artists"] = artists    # store search results in session
        return render_template("index.html", artists=artists, playlist=playlist, success=success, playlist_url=playlist_url)
    return render_template("index.html", playlist=playlist, success=success, playlist_url=playlist_url)

# landing page
@app.route("/")
def home():
    session.pop("playlist", None)  # remove playlist from session
    return render_template("home.html")
if __name__ == "__main__":
    app.run(debug=True)