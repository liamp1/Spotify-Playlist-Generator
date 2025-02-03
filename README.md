# Playlist Generator for Spotify

## About The Project

**Playlist Generator for Spotify** allows users to create and export custom playlists based on their favorite artists. Users can search for artists, generate a playlist with a mix of popular and lesser-known tracks, and preview the playlist before exporting it to their Spotify account.

### Key Features
- **Search for Artists**: Users can enter an artist’s name to generate a playlist.
- **Playlist Generation**: The app selects a mix of popular and random tracks from the searched artist.
- **Export to Spotify**: Users can export their generated playlist directly to their Spotify account.
- **User Authentication**: If not logged in, users are redirected to the Spotify login page before exporting.

### Built With
- [Flask](https://flask.palletsprojects.com/en/stable/)
- [Spotify API](https://developer.spotify.com/documentation/web-api)

---

## Getting Started

### Preface
This application is currently designed to run **locally** on your machine. You must run the server on your local environment and access it via `127.0.0.1:5000`. At this stage, the app is not publicly accessible online. However, future updates will include **Docker deployment**.

### Installation

Follow these steps to set up the application:

1. **Clone the Repository**
   ```sh
   git clone https://github.com/liamp1/Spotify-Playlist-Generator.git
   ```

2. **Run the Application**
   ```sh
   python main.py
   ```

---

## Usage

### 1. Accessing the Application
- Open the web application in your browser.
- You have the option to log in with Spotify or continue without logging in.

### 2. Searching for an Artist
- Type the name of an artist in the search bar.
- Press the **Add** button next to the artist you would like to select.
- The selected artists will appear in the **Selected Artists** window on the bottom right.

### 3. Generating a Playlist
- Press the **Generate Playlist** button in the **Selected Artists** window.
- A playlist of tracks based on the selected artists will appear.
- The playlist includes:
  - Track Name
  - Artist Name
  - Album Name
  - Album Cover

### 4. Exporting the Playlist to Spotify
#### If you are already logged into Spotify:
- Click the **Export Playlist** button.
- The playlist is instantly created in your Spotify account.
- A **notification popup** appears with a link to the exported playlist.

#### If you are not logged in:
- Clicking **Export Playlist** redirects you to Spotify’s login page.
- After logging in, the app exports the playlist to your Spotify account.
- A **popup notification** confirms the successful export with a direct link to the playlist.

### 5. Returning to the Search Page
- After exporting, you are redirected back to the **Search** page with your playlist still visible.
- You can:
  - Generate a new playlist by searching for another artist.
  - Export additional playlists.

