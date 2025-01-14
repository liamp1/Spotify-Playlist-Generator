from flask import Flask, render_template, request, redirect, session, jsonify, url_for
from flask_session import Session
from requests import get, post
import os
import base64
import json
import random
from dotenv import load_dotenv
from urllib.parse import urlencode
import requests



# flask app initialization
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
print("SECRET_KEY from .env:", os.getenv("SECRET_KEY"))

# Configure Flask-Session
app.config['SESSION_TYPE'] = 'filesystem'  # Store sessions on the server
app.config['SESSION_PERMANENT'] = False    # Make sessions temporary
app.config['SESSION_FILE_DIR'] = './.flask_session/'  # Directory to store session files
app.config['SESSION_USE_SIGNER'] = True    # Sign session data for security
app.config['SESSION_KEY_PREFIX'] = 'spotify_'  # Prefix for session keys
Session(app)

# constants for OAuth configuration
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_URL = "https://api.spotify.com/v1"
REDIRECT_URI = "http://localhost:5000/callback"  # Update this to match your environment
SCOPE = "playlist-modify-public playlist-modify-private"

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

@app.route("/spotify-login")
def spotify_login():
    scope = "playlist-modify-public playlist-modify-private"
    auth_url = (
        f"{SPOTIFY_AUTH_URL}?response_type=code&client_id={client_id}"
        f"&scope={scope}&redirect_uri={REDIRECT_URI}"
    )
    print("Redirecting to Spotify login...")  # Debugging
    return redirect(auth_url)


@app.route("/callback")
def callback():
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "Authorization failed"}), 400

    # Exchange authorization code for tokens
    auth_response = requests.post(
        SPOTIFY_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
        }
    )

    auth_data = auth_response.json()
    session['access_token'] = auth_data.get('access_token')
    session['refresh_token'] = auth_data.get('refresh_token')
    session.modified = True  # Force session save
    print("Session data in callback:", dict(session))  # Debugging

    return redirect(url_for('export_playlist'))





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
                    "uri": track_details["uri"]  # Add the URI for each track
                })

    return tracks


@app.route("/create_playlist", methods=["POST"])
def create_playlist():
    artist_ids = request.json.get("artist_ids", [])
    if not artist_ids:
        return jsonify({"error": "No artists selected"}), 400

    token = get_token()
    all_tracks = []

    # Fetch tracks for each artist
    for artist_id in artist_ids:
        artist_tracks = fetch_artist_tracks(token, artist_id)
        all_tracks.append(artist_tracks)

    # Generate the playlist
    max_songs = random.randint(20, 30)
    playlist = []

    for artist_tracks in all_tracks:
        num_tracks = min(len(artist_tracks), max_songs // len(all_tracks))
        playlist.extend(random.sample(artist_tracks, num_tracks))

    session['final_playlist'] = playlist
    session.modified = True  # Force session save
    print("Storing playlist in session before Spotify login:", dict(session))  # Debugging

    return jsonify({"playlist": playlist})









@app.route('/export_playlist')
def export_playlist():
    print("Session data at export (before access):", dict(session))  # Debugging

    final_playlist = session.get('final_playlist', [])
    if not final_playlist:
        print("No playlist found in session")
        return jsonify({"error": "No playlist found in session"}), 400

    track_uris = [track.get('uri') for track in final_playlist if 'uri' in track]
    if not track_uris:
        print("No track URIs to add")
        return jsonify({"error": "No track URIs to add"}), 400

    access_token = session.get('access_token')
    if not access_token:
        print("No access token found, redirecting to Spotify login")
        return redirect(url_for('spotify_login'))

    headers = {"Authorization": f"Bearer {access_token}"}
    user_response = requests.get(f"{SPOTIFY_API_URL}/me", headers=headers).json()
    user_id = user_response.get('id')

    if not user_id:
        print("Failed to retrieve user ID")
        return jsonify({"error": "Failed to retrieve user information"}), 400

    playlist_name = "My Generated Playlist"
    create_playlist_response = requests.post(
        f"{SPOTIFY_API_URL}/users/{user_id}/playlists",
        headers=headers,
        json={"name": playlist_name, "description": "Generated playlist", "public": True}
    )

    playlist_data = create_playlist_response.json()
    playlist_id = playlist_data.get("id")

    if not playlist_id:
        print("Failed to create playlist on Spotify")
        return jsonify({"error": "Failed to create playlist"}), 400

    add_tracks_response = requests.post(
        f"{SPOTIFY_API_URL}/playlists/{playlist_id}/tracks",
        headers=headers,
        json={"uris": track_uris}
    )

    if add_tracks_response.status_code != 201:
        print("Failed to add tracks to the playlist")
        return jsonify({"error": "Failed to add tracks to the playlist"}), 400

    return jsonify({
        "success": True,
        "playlist_url": playlist_data["external_urls"]["spotify"]
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
