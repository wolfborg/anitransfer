# anitransfer
## usage
This requires [poetry][] on your machine for easier management of Python projects.

Install dependencies in a virtual environment. This is required only once.

```bash
poetry install
```

Run the conversion.
```bash
poetry run anitransfer.py path/to/your/file.json

# example
poetry run anitransfer.py ~/Downloads/export-anime-GhostLyrics.json
```

If you would like to see a full list of available options, run 
`poetry run anitransfer.py --help`.

[poetry]: https://python-poetry.org

## history
The goal of this script is to move your anime list from Anime Planet to AniList.

The complication with this is that Anime Planet gives you a JSON file while AniList lets you import from a MyAnimeList XML export file. Taking the information from the JSON and putting it into the same XML structure is easy enough, but the AniList import process is dependent on the MyAnimeList ID number. This means we need to find the anime on MyAnimeList and connect the ID with our data from Anime Planet to bring it all into AniList. To do this, this script uses the unofficial MyAnimeList API, Jikan to search for the ID.

The Jikan search function returns weird results at times though, especially if a show has multiple seasons, adaptations, or specials. That and Anime Planet tends to give us the English title whereas Jikan only seems to return the Japanese title (probably since MyAnimeList only gives access to that). With all this, I had to make it so that if the script can't immediately find the result it'll ask for your input to help determine which to pick.

IMPORTANT NOTE: If you make changes to this script DO NOT remove the Jikan request delay. If you make too many requests through Jikan too fast your IP will end up blocked from the API. According to their docs, you're required to have at least a 4 second delay between each request for bulk requesting like we're doing.

To make the process much faster despite the 4 second delay between Jikan search requests, I've added in a cached mapping of the Anime Planet titles to MyAnimeList IDs. If the Anime Planet title is found in the file, then we just grab the MAL ID from there instead of doing a Jikan request. This makes the process incredibly faster, and the more data we put through it and verify the faster it'll be. If you use this and want to send over your additional mappings or any fixes to this file, feel free to send them to be or make a pull request and I'll bring them in.

Right now, there's a number of certain show types this script has problems with. Many of these we can't do anything about because Anime Planet and MyAnimeList just store them too differently. For example, Anime Planet will list a show like "Digimon: Digital Monsters" as two seasons (with two listings) while MyAnimeList lists it as one show. This happens the other way around too, like with "Code Geass Gaiden: Boukoku no Akito" which is five OVAs that Anime Planet lists as one OVA collection but MAL lists seperately. Recap episodes tend to be missing as well. And also MyAnimeList likes to ignore titles it doesn't deem anime enough for them, like "Castlevania". AniList also doesn't list some of these shows either though, but Anime Planet does so watch for that during the confirmation process.

When you're done, a log file will be created in the logs folder listing all the shows it couldn't add to the XML file so you can deal with them manually on AniList after importing. When you do import, AniList will also list a few it has a problem importing as well that you can either manually fix or just don't exist there.
