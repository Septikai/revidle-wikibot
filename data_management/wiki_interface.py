from typing import List

from mediawiki import MediaWikiPage
from helpers.wiki_lib_patch import PatchedMediaWiki, SearchResult

class WikiInterface:
    def __init__(self, user_agent):
        self.wiki = PatchedMediaWiki(url="https://revolutionidle.wiki.gg/api.php", user_agent=user_agent)

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
        return self.to_page(self.search(text, 1)[0])

    def advanced_search(self, text: str, limit=5) -> List[SearchResult]:
        """
        Searches for text with snippets of pages where the text is found 
        """
        return self.wiki.advanced_search(text, results=limit, srprop=["snippet"])