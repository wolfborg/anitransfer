# anitransfer
The goal of this script is to move your anime list from Anime Planet to AniList.

The complication with this is that Anime Planet gives you a JSON file while AniList lets you import from a MyAnimeList XML export file. Taking the information from the JSON and putting it into the same XML structure is easy enough, but the AniList import process is dependent on the MyAnimeList ID number. This means we need to find the anime on MyAnimeList and connect the ID with our data from Anime Planet to bring it all into AniList. To do this, this script uses the unofficial MyAnimeList API, Jikan to search for the ID.

The Jikan search function returns weird results at times though, especially if a show has multiple seasons, adaptations, or specials. That and Anime Planet tends to give us the English title whereas Jikan only seems to return the Japanese title (probably since MyAnimeList only gives access to that). With all this, I had to make it so that if the script can't immediately find the result it'll ask for your input to help determine which to pick.

IMPORTANT NOTE: If you make changes to this script DO NOT remove the Jikan request delay. If you make too many requests through Jikan too fast your IP will end up blocked from the API. According to their docs, you're required to have at least a 4 second delay between each request for bulk requesting like we're doing.