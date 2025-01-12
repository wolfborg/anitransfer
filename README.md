# anitransfer
## Usage
This requires [poetry](https://python-poetry.org) on your machine for easier management of Python projects.

Install dependencies in a virtual environment. This is required only once.

```bash
poetry install
```

Run the conversion.
```bash
poetry run python anitransfer.py path/to/your/file.json
```

```bash
poetry run python anitransfer.py ~/Downloads/export-anime-GhostLyrics.json
```

When it's done running, a file called "convert.xml" will be in the folder. Use this to import your list.

If you would like to see a full list of available options, run `poetry run python anitransfer.py --help`.

## MAL API
In order to convert lists, you need to match Anime Planet titles to MyAnimeList IDs. This script has two APIs which can accomplish this. The original Jikan API this script relied on changed to v4 recently and right now its search queries are really bad. So for now it's recommended to use the MyAnimeList API instead with this script.

To use the MyAnimeList API, you must register for a client ID on the [MyAnimeList API panel](https://myanimelist.net/apiconfig). This will require a MyAnimeList account.

After you register an application there, the page will give you a client ID.

Create a .env file in the same folder as anitransfer.py with the following value:

```bash
MAL_CLIENT_ID=clientid
```
Replace `clientid` with your client ID. Do not let others see this ID.

After that, you'll be able to run the script with the new `--mal-api` option. Without this, it will default to using the Jikan API search.

```bash
poetry run python anitransfer.py --anime_list="path/to/your/file.json" --mal-api
```

Keep in mind the API currently does not have a publicly defined rate limit, but it's probably best to keep a delay on each request. The default API delay (for MAL and Jikan) is currently set to 1.5 seconds. This will only trigger a delay when an API request is actually done.

MAL API is far more effective than Jikan API search right now except for long titles. MAL API search "q" parameter for the query appears to have a character limit that isn't defined in their documentation. The limit appears to be 64 characters from some testing on my end. Any search done with a title longer than this limit will return a "bad request" message from the API. So I've added in checks for that to ignore those and keep the script going.

Might make it in the future so it tries to search with the first 64 characters. For now though those cases can be resolved by running the script with Jikan API after first processing the list through the MAL API. Or by manually searching for the MAL ID and then adding the cache mapping to the file yourself.

Additional related links:
https://myanimelist.net/forum/?topicid=1973141
https://myanimelist.net/forum/?topicid=1973077
https://myanimelist.net/apiconfig/references/api/v2

## Available Options
`--anime-list`: (path) Path to the Anime Planet JSON file for the script to process.

`--cache-only`: Runs process without looking up new matches, only cache mappings used.

`--mal-api`: Uses MAL API instead when doing search (MAL_CLIENT_ID  required in .env file).

`--search-queue`: Ignores all list processing, simply begins searches to clear the unmapped queue.

`--skip-confirm`: Skip any confirmation prompts that show up, still tries initial search for entries.

`--with-links`: Displays links to found MyAnimeList entries to help with manual confirmation.

`--with-info`: Displays entry info for found MyAnimeList entries to help with manual confirmation.

`--open-tabs`: Opens the Anime Planet and MyAnimeList search tabs in your browser during manual confirmation.

`--num-options`: (int) Determines the max number of options to display during options select.

`--limit`: (int) Limits the number of entries to process.

`--api-delay`: (int) Delay between API requests in seconds.

`--log-file`: (path) Write log of operations to this file.

`--cache-file`: (path) Cache file to use for already downloaded anime mappings.

`--bad-file`: (path) Cache file to use for incompatible anime mappings.

`--unmapped-file`: (path) Cache file to use for anime mappings that have not been reviewed yet.

Typically I run the script with `--cache-only` first to see if we already have every entry on the list. If there are still entries that weren't found, I then run it again with the `--mal-api --skip-confirm` flags enabled. This attempts automated matches based on a search APIs of the MAL database. MAL API is best search API to use for that but requires you to get credentials and add it to the .env file here. By default the search API used is Jikan because it doesn't require credentials, but it is still a third-party search API for MAL and isn't as effective.

If there are still entries that weren't found after that, then the remainder must be manually confirmed. Luckily, any entry that wasn't found by now has been added to the "anime_unmapped.csv" file so you don't have to reprocess your whole list. Simply use the `--search-queue` flag and it will present you with options to select for manual confirmation. It's recommended to use the `--mal-api` flag with this as well so the options are better. To make this process easier, I've added a `--with-info` flag that shows basic information like start year, episode counts and lengths, and studio of each MAL search result. Meanwhile, the `--open-tabs` flag will automatically open a browser tag for the current entry's Anime Planet page. Combine both `--with-info` and `--open-tabs` flags to compare the info on the Anime Planet page with the info displayed in the MAL selections to determine if there's a match. If you're unsure, you can use the `--with-links` flag to include links to the MAL entries to help you decide. Every confirmation is updated as you go, so if you have to end the process for now you can continue manually going through the queue later. In fact your anime list isn't even needed to go through the search queue, as that flag completely ignores lists and makes the sole purpose of the script to manually confirm matches.

Once the search queue is clear, make sure you process your list with the `--cache-only` flag to reprocess your list so that your converted file now includes the new entries you had manually confirmed. At that point, if it says there are no entries left to find, then you should be done. Make sure to review the log file for any issues that might have to be fixed after importing to AniList.

```bash
poetry run python anitransfer.py --anime-list="samples/export-anime-Wolfborg.json" --cache-only
poetry run python anitransfer.py --anime-list="samples/export-anime-Wolfborg.json" --mal-api --skip-confirm
poetry run python anitransfer.py --anime-list="samples/export-anime-Wolfborg.json" --mal-api --search-queue --with-info --with-links --open-tabs
poetry run python anitransfer.py --anime-list="samples/export-anime-Wolfborg.json" --cache-only
```

## Summary
The goal of this script is to move your anime list from Anime Planet to AniList, although it also works for MyAnimeList.

The complication with this is that Anime Planet gives you a JSON file while AniList lets you import from a MyAnimeList XML export file. The AniList import process is dependent on the MyAnimeList ID number. This means we need to find the anime on MyAnimeList and connect the ID with our data from Anime Planet to bring it all into AniList.

To get the MyAnimeList IDs, this script can use either the unofficial Jikan API (default) or the official MyAnimeList API. The MAL API is more effective, however it requires you to have a MAL account and register an application so they can give you a client ID.

Jikan API is currently really bad at handling a lot of titles with its search functionality. This is especially true if a show has multiple seasons, adaptations, or specials. So if possible it's highly recommended to use the MAL API.

If the script can't immediately a title match, it'll ask for your input to help determine which to pick. You can also manually enter a MAL ID during this process.

IMPORTANT NOTE: If you make changes to this script DO NOT remove the API request delay. If you make too many requests too fast your IP will likely end up blocked from the API. The defualt value should be safe.

To make this faster, I've added in a cached mapping of the Anime Planet titles to MyAnimeList IDs. If the Anime Planet title is found in the file, then we just grab the MAL ID from there instead of doing an API request. This makes the process incredibly faster, and the more data we put through it and verify the faster it'll be. If you use this and want to send over your additional mappings or any fixes to this file, feel free to send them to me or make a pull request and I'll bring them in.

Some shows cannot work during this process because an accurate mapping is not possible between the platforms. These are stored in a "bad cache" file that's only updated manually.

When the script is done, a log file will be created in the logs folder listing all the shows it couldn't add to the XML file so you can deal with them manually on AniList after importing. If you import to AniList, the site might also list a few titles it has a problem importing that you might have to manually fix or they just don't exist in the AniList database.

If you want me to process your list for you, reach out to me on [Twitter](https://twitter.com/Wolfborgg) or via email ([chaplin.derek@gmail.com](mailto:chaplin.derek@gmail.com)). And if you use the script, I would appreciate if you send me the cache file after so I can add the new mappings to the script.
