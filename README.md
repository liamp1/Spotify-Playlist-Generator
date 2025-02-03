<!-- Improved compatibility of back to top link: See: https://github.com/othneildrew/Best-README-Template/pull/73 -->
<a name="readme-top"></a>
<!--
*** Thanks for checking out the Best-README-Template. If you have a suggestion
*** that would make this better, please fork the repo and create a pull request
*** or simply open an issue with the tag "enhancement".
*** Don't forget to give the project a star!
*** Thanks again! Now go create something AMAZING! :D
-->


<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="[https://github.com/liamp1/Spotify-Playlist-Generator]">
  </a>

  <h3 align="center">Playlist Generator for Spotify</h3>

  <p align="center">
    Generate your Spotify playlist based on your favorite artists.
    <br />
  </p>
</div>





<!-- ABOUT THE PROJECT -->
## About The Project

Playlist Generator for Spotify allows users to create and export custom playlists based on their favorite artists. Users can search for artists, generate a playlist with a mix of popular and lesser-known tracks, and preview the playlist before exporting it to their Spotify account.

Key Features:
<ul>
  <li>Search for Artists: Users can enter an artist’s name to generate a playlist</li>
  <li>Playlist Generation: The app selects a mix of popular and random tracks from the searched artist.</li>
  <li>Export to Spotify: Users can export their generated playlist directly to their Spotify account.</li>
  <li>User Authentication: If not logged in, users are redirected to the Spotify login page before exporting.</li>
</ul>





### Built With
<ul>
  <li><a href="https://flask.palletsprojects.com/en/stable/">Flask</a></li>
  <li><a href="https://developer.spotify.com/documentation/web-api">Spotify API</a></li>
</ul>





<!-- GETTING STARTED -->
## Getting Started

### Preface

This application is currently designed to run locally on your machine. You must run the server on your local environment and access it via 127.0.0.1:5000. At this stage, the app is not publicly accessible online. However, future updates will include Docker deployment.

### Installation

The guide to start up the app:

1. Clone the repository
   ```sh
   git clone https://github.com/liamp1/Spotify-Playlist-Generator.git
   ```
2. Run main.py
   ```sh
   python main.py
   ```



<!-- USAGE EXAMPLES -->
## Usage

1. Accessing the Application
<ul>
  <li>Open the web application in your browser.</li>
  <li>You have the option to log in with Spotify or continue without logging in.</li>
</ul>
2. Searching for an Artist
<ul>
  <li>Type the name of an artist in the search bar.</li>
  <li>Press the add button next to the artist you would like to select. The selected artists will appear in the "Selected Artists" window on the bottom right.</li>
</ul>
3. Generating Playlist
<ul>
  <li>Press the "Generate Playlist" button in the "Selected Artists" window.</li>
  <li>A playlist of tracks based on the selected artists will appear.</li>
  <li>The playlist includes
    <li>Track Name</li>
    <li>Artist Name</li>
    <li>Album Name</li>
    <li>Album Cover</li>
  </li>
</ul>
4. Exporting the Playlist to Spotify
<ul>
  <li>If you are already logged into Spotify:
    <li>Click the "Export Playlist" button.</li>
    <li>The playlist is instantly created in your Spotify account.</li>
    <li>A notification popup appears with a link to the exported playlist.</li>
  </li>
  <li>If you are not logged in:
    <li>Clicking "Export Playlist" redirects you to Spotify’s login page.</li>
    <li>The app exports the playlist to your Spotify account.</li>
    <li>A popup notification confirms the successful export with a direct link to the playlist.</li>
  </li>
</ul>
5. Returning to the Search Page
<ul>
  <li>After exporting, you are redirected back to the Search page with your playlist still visible.</li>
  <li>You can:
    <li>Generate a new playlist by searching for another artist.</li>
    <li>Export additional playlists.</li>
  </li>
</ul>





