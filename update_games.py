import os
from dotenv import load_dotenv
import requests
import json
from tqdm import tqdm

# Load environment variables from a .env file
load_dotenv()

# Replace with your Steam API key and Steam ID
STEAM_API_KEY = os.getenv('STEAM_API_KEY', '6D21DDC31824B11F6D274D96A0D41071')
STEAM_ID = os.getenv('STEAM_ID', '76561198030118131')

# App IDs to exclude (hidden/private games). Find IDs at store.steampowered.com/app/<ID>/
EXCLUDED_APP_IDS = {
    # e.g. 730,  # CS2
    899970, # NEKOPARA Extra
    333600, # NEKOPARA Vol. 1
    385800, # NEKOPARA Vol. 0
}

url = f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/?key={STEAM_API_KEY}&steamid={STEAM_ID}&include_appinfo=true&include_played_free_games=true"

response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    games = data.get('response', {}).get('games', [])
    games = [g for g in games if g['appid'] not in EXCLUDED_APP_IDS]
    if games:
        # Prepare the game data for JSON output
        game_list = []
        for game in tqdm(sorted(games, key=lambda x: x['playtime_forever'], reverse=True), desc="Fetching game details", unit="game"):
            appid = game['appid']
            name = game.get('name', 'Unknown Game')
            playtime = game['playtime_forever'] // 60  # Convert minutes to hours

            # Validate and provide a fallback for logo_url
            logo_url = game.get('img_logo_url')
            if logo_url:
                logo_url = f"https://media.steampowered.com/steamcommunity/public/images/apps/{appid}/{logo_url}.jpg"
            else:
                # Use icon_url as a fallback for logo_url
                icon_url = game.get('img_icon_url')
                if icon_url:
                    logo_url = f"https://media.steampowered.com/steamcommunity/public/images/apps/{appid}/{icon_url}.jpg"
                else:
                    logo_url = "https://via.placeholder.com/300x200?text=No+Image"  # Fallback placeholder image

            # Validate and provide a fallback for icon_url
            icon_url = game.get('img_icon_url')
            if icon_url:
                icon_url = f"https://media.steampowered.com/steamcommunity/public/images/apps/{appid}/{icon_url}.jpg"
            else:
                icon_url = "https://via.placeholder.com/64x64?text=No+Icon"  # Fallback placeholder icon

            store_url = f"https://store.steampowered.com/app/{appid}/"

            # Fetch additional details (e.g., genres, release date) from another API endpoint if available
            details_url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
            details_response = requests.get(details_url)

            # Ensure genres and release date are correctly fetched
            genres = []
            release_date = "Unknown"

            if details_response.status_code == 200:
                details_data = details_response.json()
                app_details = details_data.get(str(appid), {}).get('data', {})
                genres = [genre['description'] for genre in app_details.get('genres', [])]
                release_date = app_details.get('release_date', {}).get('date', 'Unknown')

            # Handle cases where genres or release date are missing
            genres = genres if genres else ["N/A"]
            release_date = release_date if release_date else "Unknown"

            # Fetch additional details (e.g., description, developers, publishers, etc.)
            description = "No description available"
            developers = []
            publishers = []
            platforms = []
            languages = "Unknown"
            metacritic_score = "N/A"
            # Remove fetching screenshots to save time
            screenshots = []

            if details_response.status_code == 200:
                details_data = details_response.json()
                app_details = details_data.get(str(appid), {}).get('data', {})

                # Extract additional details
                description = app_details.get('short_description', description)
                developers = app_details.get('developers', developers)
                publishers = app_details.get('publishers', publishers)
                platforms = [key for key, value in app_details.get('platforms', {}).items() if value]
                languages = app_details.get('supported_languages', languages).split(',')[0]  # Get the first language
                metacritic = app_details.get('metacritic', {})
                metacritic_score = metacritic.get('score', metacritic_score)

            # Fetch player achievements for the game
            achievements = []
            player_achievements_url = f"https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v1/?key={STEAM_API_KEY}&steamid={STEAM_ID}&appid={appid}"
            schema_achievements_url = f"https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/?key={STEAM_API_KEY}&appid={appid}"

            player_achievements_response = requests.get(player_achievements_url)
            schema_achievements_response = requests.get(schema_achievements_url)

            if player_achievements_response.status_code == 200 and schema_achievements_response.status_code == 200:
                player_achievements_data = player_achievements_response.json().get('playerstats', {}).get('achievements', [])
                schema_achievements_data = schema_achievements_response.json().get('game', {}).get('availableGameStats', {}).get('achievements', [])

                # Map schema achievements by their API name for easy lookup
                schema_achievements_map = {ach['name']: ach for ach in schema_achievements_data}

                # Filter and sort achievements by rarity (percentage of players who have it)
                for achievement in player_achievements_data:
                    if achievement.get('achieved') == 1:  # Only include unlocked achievements
                        schema_achievement = schema_achievements_map.get(achievement['apiname'], {})
                        achievements.append({
                            "name": schema_achievement.get('displayName', 'Unknown Achievement'),
                            "description": schema_achievement.get('description', 'No description available'),
                            "icon": schema_achievement.get('icon', ''),
                            "rarity": schema_achievement.get('percent', 100)  # Default to 100% if not available
                        })

                # Sort by rarity and take the top 5 rarest achievements
                achievements = sorted(achievements, key=lambda x: x['rarity'])[:5]

            # Add all details to the game list
            game_list.append({
                "name": name,
                "icon_url": icon_url,
                "logo_url": logo_url,
                "store_url": store_url,
                "playtime": playtime,
                "genres": genres,
                "release_date": release_date,
                "description": description,
                "developers": developers,
                "publishers": publishers,
                "platforms": platforms,
                "languages": languages,
                "metacritic_score": metacritic_score,
                "screenshots": screenshots,
                "achievements": achievements
            })

        # Write the game data to a JSON file
        with open('games.json', 'w', encoding='utf-8') as file:
            json.dump(game_list, file, indent=4)

        print("games.json has been created with detailed game information.")
    else:
        print("No games found or an error occurred.")
else:
    print(f"Error fetching Steam library: {response.status_code}")