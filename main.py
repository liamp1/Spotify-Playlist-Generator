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


# flask app initialization
app = Flask(__name__)

# environment variables
load_dotenv()
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
redirect_uri = "http://localhost:5000/callback"
auth_url = "https://accounts.spotify.com/authorize"
api_base_url = "https://api.spotify.com/v1/"
token_url = "https://accounts.spotify.com/api/token"

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
    result = post(token_url, headers=headers, data=data)
    token = json.loads(result.content)["access_token"]
    return token

# construct authorization header
def get_auth_header(token):
    return {"Authorization": f"Bearer {token}"}


@app.route("/login")
def login():
    scope = "playlist-modify-private"

    params = {
        "client_id": client_id,
        "repsonse_type": 'code',
        "scope": scope,
        "redirect_uri": redirect_uri,
        "show_dialog": True
    }

    authorization_url = f"{auth_url}?{urllib.parse.urlencode(params)}"

    return redirect(authorization_url)

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
            "client_secret": client_secret
        }

        reponse = requests.post(token_url, data=req_body)
        token_info = reponse.json()

        session["access_token"] = token_info["access_token"]
        session["refresh_token"] = token_info["refresh_token"]
        session["expires_at"] = datetime.now().timestamp() + token_info["expires_in"]

        return redirect("/export_playlist")





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
                    "popularity": track_details["popularity"]
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
        print(f"Artist {artist_id} has {len(artist_tracks)} tracks.")  # Debug log
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
        print(f"Selected {num_tracks} tracks from an artist. Remaining slots: {remaining_slots}")  # Debug log

    # fill remaining slots with random tracks from all artists (mixed)
    flat_tracks = [track for artist_tracks in all_tracks for track in artist_tracks]
    random.shuffle(flat_tracks)  # Shuffle tracks for a mixed selection
    remaining_tracks = [track for track in flat_tracks if track not in playlist]
    if remaining_slots > 0:
        playlist.extend(random.sample(remaining_tracks, min(remaining_slots, len(remaining_tracks))))
        print(f"Added {remaining_slots} remaining tracks from a mix of all artists.")  # Debug log

    # shuffle final playlist to mix tracks from all artists
    random.shuffle(playlist)

    # log popularity for debugging
    for track in playlist:
        print(f"Track: {track['name']} | Popularity: {track['popularity']}")  # Debug log

    # limit playlist to the maximum number of songs
    playlist = playlist[:max_songs]
    print(f"Final playlist has {len(playlist)} tracks.")  # Debug log

    final_playlist = jsonify({"playlist": playlist})
    return final_playlist

@app.route("/export_playlist")
def export_playlist():
    # Ensure the playlist exists in the session
    final_playlist = session.get('final_playlist')
    if not final_playlist:
        return jsonify({"error": "No playlist found in session"}), 400

    access_token = session.get('access_token')
    if not access_token:
        return redirect('/login')  # Redirect to login if access token is missing

    # Get the user profile
    headers = get_auth_header(access_token)
    user_profile_response = get(f"{api_base_url}me", headers=headers)

    if user_profile_response.status_code != 200:
        return jsonify({"error": "Failed to fetch user profile"}), 400

    user_profile = user_profile_response.json()
    user_id = user_profile.get('id')
    if not user_id:
        return jsonify({"error": "User ID not found"}), 400

    # Create a new playlist
    playlist_name = f"Generated Playlist {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    create_playlist_body = {
        "name": playlist_name,
        "description": "A playlist generated by the Flask app",
        "public": False
    }

    create_playlist_response = post(
        f"{api_base_url}users/{user_id}/playlists",
        headers=headers,
        json=create_playlist_body
    )

    if create_playlist_response.status_code != 201:
        return jsonify({"error": "Failed to create playlist"}), 400

    playlist = create_playlist_response.json()
    playlist_id = playlist.get('id')

    # Add tracks to the playlist
    track_uris = [track['uri'] for track in final_playlist]
    chunk_size = 100  # Spotify API allows adding up to 100 tracks at a time
    for i in range(0, len(track_uris), chunk_size):
        chunk = track_uris[i:i + chunk_size]
        add_tracks_response = post(
            f"{api_base_url}playlists/{playlist_id}/tracks",
            headers=headers,
            json={"uris": chunk}
        )
        if add_tracks_response.status_code != 201:
            return jsonify({"error": "Failed to add tracks to playlist"}), 400

    # Respond with success and playlist link
    return jsonify({
        "message": "Playlist created successfully!",
        "playlist_url": playlist.get('external_urls', {}).get('spotify', '#')
    })

    




# Home route
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        query = request.form.get("content", "")
        if not query:
            return render_template("index.html", error="Please enter a search term.")

        token = get_token()
        results = search_spotify(token, query)

        # Extract artist information
        artists = [
            {
                "name": artist["name"],
                "id": artist["id"],
                "image": artist["images"][0]["url"] if artist["images"] else "https://via.placeholder.com/100"
            }
            for artist in results.get("artists", {}).get("items", [])
        ]
        return render_template("index.html", artists=artists)
    return render_template("index.html")
if __name__ == "__main__":
    app.run(debug=True)