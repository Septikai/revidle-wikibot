from typing import List

import mediawiki
from mediawiki import MediaWikiPage
from helpers.wiki_lib_patch import PatchedMediaWiki, SearchResult


class WikiInterface:
    def __init__(self, user_agent):
        self.wiki = PatchedMediaWiki(url="https://revolutionidle.wiki.gg/api.php", user_agent=user_agent)

    def to_page(self, page_id) -> MediaWikiPage:
        """Convert a page ID to a MediaWikiPage.

        :param page_id: the ID of the page to return.
        :returns: the page requested."""
        return self.wiki.page(page_id, auto_suggest=False)

    def search(self, text: str, limit=10) -> List[str]:
        """Search the wiki pages.

        Will return the search results, not pages.
        If no exact matches are found (ignoring case) then it will also search sections
        of the pages it initially found for more specific results.

        :param text: the page to search for.
        :param limit: the number of results to return.
        :returns: a list of search results."""
        results = self.wiki.search(text[:300], results=limit)
        if text in results:
            return results
        section_results = [result for result in results if text.lower() in result.lower()]
        for result in results:
            section_results.extend(self.section_search(self.to_page(result), text))
            if len(section_results) >= limit:
                break
        return section_results[:limit]

    def page_search(self, text: str, exact: bool = False) -> MediaWikiPage:
        """Searches for a page to return.

        Will return the first result as a page.

        :param text: the page to search for.
        :param exact: when enabled, will only search for an exact match and not search for pages with related content.
        :returns: the page requested."""
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

    def section_search(self, page: MediaWikiPage, text: str) -> List[str]:
        """Searches a page for a specific section.

        :param page: the page to search.
        :param text: the section to search for on the page.
        :returns: a list of result strings in the format `Page#Section`."""
        # TODO: find a better way to detect a page with no sections
        try:
            return [f"{page.title}#{section.replace(' ', '_')}" for section in page.sections if text.lower() in section.lower()]
        except IndexError:
            return []

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
        return self.wiki.advanced_search(query=text[:300], limit=limit, srprop=["snippet","sectionsnippet"])

