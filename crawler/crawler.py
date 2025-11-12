import json
from pathlib import Path
from typing import Dict, Set

import requests
from bs4 import BeautifulSoup
from rich import print as rprint

"""
This crawler is specifically adjusted to scrape the data from movie-locations.com.

What is important is the strucurte of the site.
It is hardcoded for now but we can extract it later on so it is more readable and easier to change but we probably won't care and need that.
Basically the site is divided by the first number/letter of the movie title.
It goes from 0-9 to Z.
Example: https://movie-locations.com/0/0-movies.php - This is the page for all movies starting with a number.
https://movie-locations.com/A/A-movies.php - This is the page for all movies starting with the letter A.
and it goes on like that until Z.

Then the movie pages are their own php pages with the movie title as the name in the category that they are in.
Example: Movie Tenet since it starts with T is in the T category so its page is:
https://movie-locations.com/movies/t/Tenet-film-locations.php
"""

# TODO: Could benefit from adding separate functions for different pages and better logging instead of just printing.


def crawlMovieLocationsCom(
    save_to_db: bool = False, output: str = "./data/movie_locations.json"
) -> bool:
    """Crawler for movie-locations.com.

    Args:
        save_to_db: If True, use a provided database connection to save results. For now we are doing it raw dog style with files.
        output: Path to a CSV file where results would be written. Default
            is ``movie_locations.csv``.

    Returns:
        True if the crawl completed successfully and the page parsed;
        False if the main page could not be fetched or parsed.
    """

    scrape_url_base: str = "https://movie-locations.com/"
    scrape_movies_url: str = "https://movie-locations.com/movies/"
    rprint(f"[blue]Initializing crawl for {scrape_url_base}[/blue]")

    rprint("[yellow]Loading seen URLs...[/yellow]")
    seen = load_seen_urls(output)
    rprint(f"[green]Loaded {len(seen)} seen URLs.[/green]")

    soup = BeautifulSoup(requests.get(scrape_url_base).text, "html.parser")

    content_container = soup.find("div", class_="content")
    if not content_container:
        rprint(f"[red]Failed to find content container in {scrape_url_base}[/red]")
        return False
    else:
        rprint(
            "[green]Fetched main page successfully. Commencing with the crawl...[/green]"
        )

    menu_container = content_container.find_all("p")[1]

    rprint(f"[blue]Menu container found: {menu_container is not None}[/blue]")

    category_links = [
        scrape_url_base + link.get("href") for link in menu_container.find_all("a")
    ]

    if category_links is None or len(category_links) == 0:
        rprint("[red]No category links found in menu container.[/red]")
        return False

    print(
        f"Found {len(category_links)} category links. Starting the crawl of each category..."
    )

    pages_crawled = []

    for category_link in category_links:
        # print(f"Crawing category page: {category_link}")
        category_name = category_link.split("/")[-1].split("-")[0]
        # print(category_name)

        category_soup = BeautifulSoup(requests.get(category_link).text, "html.parser")

        category_menu = category_soup.find("div", id="multicolumn3")

        for category_item in category_menu.find_all("p"):  # type: ignore
            if category_item.find("a"):
                movie_link = (
                    scrape_movies_url
                    + f"{category_name}/"
                    + category_item.find("a").get("href")  # type: ignore
                )

                # Skip if we've already seen this movie URL
                if movie_link in seen:
                    rprint(
                        f"[yellow]Already crawled: {movie_link} - skipping.[/yellow]"
                    )
                    continue

                rprint(f"[bold green]Movie link found: {movie_link}[/bold green]")
                rprint(
                    f"[bold green]Starting to crawl {movie_link} page...[/bold green]"
                )
                movie_soup = BeautifulSoup(requests.get(movie_link).text, "html.parser")

                movie_content = movie_soup.find("div", class_="content")
                if not movie_content:
                    rprint(f"[red]Failed to find movie content in {movie_link}[/red]")
                    continue

                page_object = {
                    "url": movie_link,
                    "title": "",
                    "text_content": "",
                }

                title_and_year_container = movie_content.find("h1")
                if not title_and_year_container:
                    rprint(
                        f"[red]Failed to find title and year container in {movie_link}[/red]"
                    )
                    continue

                # For now the title is both the title and the year together in "title | year" format
                title = title_and_year_container.get_text()
                # If we want to have the year we can extract it later
                # year = title_and_year_container.find("span").text
                page_object["title"] = title

                text_description = [p.get_text() for p in movie_content.find_all("p")]
                page_object["text_content"] = "\n".join(text_description)
                append_record(output, page_object)
                pages_crawled.append(page_object)
                rprint(f"[bold green]Crawled movie page: {title}[/bold green]")
            else:
                rprint("[red]No movie link sorry bud.[/red]")
                rprint(f"[red]No link movie title: {category_item.text}[/red]")
                rprint(
                    "[red]If we want to also have empty movie pages, we can change the code here[/red]"
                )

    return True


def load_seen_urls(output_path: str) -> Set[str]:
    """
    Load seen URLs from the existing output file to avoid re-crawling.
    Returns a set of URLs.
    Uses every line as a JSON object.
    """
    seen = set()
    p = Path(output_path)
    if not p.exists():
        return seen
    with p.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if "url" in obj:
                    seen.add(obj["url"])
            except json.JSONDecodeError:
                continue
    return seen


def append_record(output_path: str, record: Dict) -> None:
    """
    Append a single JSON object of the crawled page to the output file.
    Void function.
    """
    with open(output_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        fh.flush()


if __name__ == "__main__":
    crawlMovieLocationsCom()
