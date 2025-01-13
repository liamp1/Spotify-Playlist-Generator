from flask import Flask, render_template, request, jsonify
from requests import get, post
import os
import base64
import json
import random
from dotenv import load_dotenv

# flask app initialization
app = Flask(__name__)

# environment variables
load_dotenv()
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")

# get spotify API token
def get_token():
    auth_string = f"{client_id}:{client_secret}"
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    result = post(url, headers=headers, data=data)
    token = json.loads(result.content)["access_token"]
    return token

# construct authorization header
def get_auth_header(token):
    return {"Authorization": f"Bearer {token}"}

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

    return jsonify({"playlist": playlist})









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
