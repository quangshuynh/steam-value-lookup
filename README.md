# Steam Value Lookup

Steam Value Lookup is a small Flask web app that looks up a Steam user's library and estimates its current total store value. Enter a numeric SteamID or a Steam vanity name to view the user's profile, owned games, playtime statistics, and per-game prices.

## Features

- Accepts a 17-digit SteamID or a Steam vanity name.
- Loads the user's public Steam profile and owned games.
- Fetches current US store prices from Steam's Store API.
- Calculates total games, total playtime, average playtime, and estimated library value.
- Sorts games by playtime by default, with client-side sorting controls for playtime and name.
- Links profiles, game thumbnails, and games back to Steam.
- Creates a local SQLite database through Flask-SQLAlchemy.

## How It Works

1. The app resolves a vanity name to a SteamID when necessary.
2. Steam's Web API returns the user's profile and owned games.
3. Store prices are requested concurrently for the returned app IDs.
4. Flask renders the results page with calculated library statistics.

Price data is an estimate based on the current US store price. Free, unavailable, delisted, and price-hidden games are reported as `$0.00`.

## Requirements

- Python 3.10 or newer
- A Steam Web API key
- A Steam profile with game details visible to the API

## Setup

From the project root:

```bash
python -m venv .venv
```

Activate the virtual environment:

**Windows PowerShell**

```powershell
.venv\Scripts\Activate.ps1
```

**Windows Command Prompt**

```bat
.venv\Scripts\activate
```

Install the dependencies:

```bash
pip install Flask Flask-SQLAlchemy python-dotenv requests
```

Create a `.env` file in the project root:

```env
STEAM_API_KEY=your_steam_web_api_key
DATABASE_URL=sqlite:///steam_value_lookup.db
```

`DATABASE_URL` is optional. If omitted, the app uses SQLite. Do not commit `.env` or expose your Steam API key.

## Run Locally

The Flask application imports modules from `backend`, so start it from that directory:

```bash
cd backend
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in a browser.

The development server runs with Flask debug mode enabled by `app.py`. For production, use a WSGI server and disable debug mode.

## Project Structure

```text
.
├── backend/
│   ├── app.py              # Flask routes and lookup workflow
│   ├── config.py           # Environment-based configuration
│   ├── database.py         # SQLAlchemy setup and table initialization
│   ├── models.py           # User, game, and inventory models
│   ├── steam_api.py        # Steam API and store-price helpers
│   ├── static/             # CSS and browser-side sorting logic
│   └── templates/          # Search and results pages
├── instance/
│   └── steam_value_lookup.db
└── steam_value_lookup.sql  # Reference SQL schema
```

## Routes

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/` | Displays the SteamID search form |
| `POST` | `/lookup` | Fetches and displays a user's library and estimated values |

## Privacy and API Notes

- Steam profile and game details must be publicly available for the lookup to return useful data.
- Steam API and Store API responses may be rate-limited or temporarily unavailable.
- The app requests prices in US dollars (`cc=us`).
- The current lookup flow does not persist fetched users or games to the database; the models and schema are available for future persistence work.
- Steam owns the Steam trademarks and related content. This project is an independent tool and is not affiliated with Valve.

## Future Improvements

- Add a `requirements.txt` or `pyproject.toml` for reproducible installs.
- Cache price lookups and add API request timeouts/retry handling for all endpoints.
- Persist lookup results using the existing SQLAlchemy models.
- Add currency selection and clearer handling for private profiles.
- Add automated tests for API failures, empty libraries, vanity-name resolution, and price parsing.

## License

No license has been specified for this project yet.