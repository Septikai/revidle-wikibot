from typing import List

from mediawiki import MediaWiki, MediaWikiPage


class WikiInterface:
    def __init__(self):
        self.wiki = MediaWiki(url="https://revolutionidle.wiki.gg/api.php")

    def to_page(self, page_id) -> MediaWikiPage:
        """Convert a page ID to a MediaWikiPage.

        :param page_id: the ID of the page to return.
        :returns: the page requested."""
        return self.wiki.page(page_id)

    def search(self, text: str, limit=10) -> List[str]:
        """Search the wiki pages.

        Will return the search results, not pages.

        :param text: the page to search for.
        :param limit: the number of results to return.
        :returns: a list of search results."""
        return self.wiki.search(text, results=limit)

    def page_search(self, text: str) -> MediaWikiPage:
        """Searches for a page to return.

        Will return the first result as a page.

        :param text: the page to search for.
        :returns: the page requested."""
        return self.to_page(self.search(text, 1))
