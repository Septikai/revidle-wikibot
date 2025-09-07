from typing import List, Tuple, Optional

import mediawiki
from mediawiki import MediaWikiPage

from helpers.wiki_lib_patch import PatchedMediaWiki, SearchResult

# import logging
# logger = logging.getLogger(__name__)

class WikiInterface:
    def __init__(self, user_agent, max_query_len, wiki_base_url):
        self.max_query_len = max_query_len
        self.wiki = PatchedMediaWiki(url=f"{wiki_base_url}api.php", user_agent=user_agent)

    def to_page(self, page_id) -> MediaWikiPage:
        """Convert a page ID to a MediaWikiPage.

        :param page_id: the ID of the page to return.
        :returns: the page requested."""
        return self.wiki.page(page_id, auto_suggest=False)

    def search(self, text: str, limit=10) -> List[Tuple[str, Optional[str]]]:
        """Search the wiki pages.

        Will return the search results, not pages.
        If no exact matches are found (ignoring case) then it will also search sections
        of the pages it initially found for more specific results.

        :param text: the page to search for.
        :param limit: the number of results to return.
        :returns: a list of (title, section) tuples."""
        titles = self.wiki.search(text[:self.max_query_len], results=limit)
        
        results = [(title, None) for title in titles if text.lower() in title.lower()] 
        for title in titles:
            results.extend(self.section_search(self.to_page(title), text))
            if len(results) >= limit:
                break
        # logger.warning(results[:limit])
        return results[:limit]

    def section_search(self, page: MediaWikiPage, text: str) -> List[Tuple[str, str]]:
        """Searches a page for a specific section.

        :param page: the page to search.
        :param text: the section to search for on the page.
        :returns: a list of (title, section) tuples`."""
        # TODO: find a better way to detect a page with no sections
        try:
            return [(page.title, section) for section in page.sections if text.lower() in section.lower()]
        except IndexError:
            return []
    
    def page_search(self, text: str, exact: bool = False) -> MediaWikiPage:
        """Searches for a page to return.

        Will return the first result as a page.

        :param text: the page to search for.
        :param exact: when enabled, will only search for an exact match and not search for pages with related content.
        :returns: MediaWikiPage object of the page requested."""
        page = None
        try:
            page = self.to_page(text)
        except mediawiki.PageError:
            if exact:
                return page
            page = self.to_page(self.search(text)[0])
            page.summarize()
        finally:
            return page

    def page_or_section_search(self, text: str) -> str:
        """Searches for a page or section matching the provided text.

        :param text: the page or section to search for.
        :returns: a link to the requested page or section, or None if nothing is found."""
        page = self.page_search(text, exact=True)
        if page is not None:
            return page.url
        results = self.search(text, limit=5)
        if len(results) == 0:
            return None
        if "#" not in results[0]:
            return self.page_search(results[0]).url
        page = self.page_search(results[0][:results[0].index("#")])
        return page.url + results[0][results[0].index("#"):]

    def advanced_search(self, text: str, limit=None) -> List[SearchResult]:
        """Searches for text with snippets of pages where the text is found

        :param text: the page to search for.
        :param limit: the number of results to fetch.
        :returns: a list of SearchResult objects."""

        # Revo wiki Guide namespace ID = 3000
        return self.wiki.advanced_search(query=text[:self.max_query_len], limit=limit,
                                         srprop=["snippet","sectionsnippet"], srnamespace=[0, 3000])


