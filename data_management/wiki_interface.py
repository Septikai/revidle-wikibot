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
        If no exact matches are found (ignoring case) then it will also search sections
        of the pages it initially found for more specific results.

        :param text: the page to search for.
        :param limit: the number of results to return.
        :returns: a list of search results."""
        results = self.wiki.search(text, results=limit)
        if text in results:
            return results
        section_results = [result for result in results if text.lower() in result.lower()]
        for result in results:
            section_results.extend(self.section_search(self.to_page(result), text))
            if len(section_results) >= limit:
                for result in section_results:
                    print("------------------")
                    print(result)
                    print("\n\n")
                    print(self.to_page(result.split("#")[0]).section(result.split("#")[1]))
                break
        return section_results[:limit]

    def page_search(self, text: str) -> MediaWikiPage:
        """Searches for a page to return.

        Will return the first result as a page.

        :param text: the page to search for.
        :returns: the page requested."""
        return self.to_page(self.search(text, 1)[0])

    def section_search(self, page: MediaWikiPage, text: str) -> List[str]:
        """Searches a page for a specific section.

        :param page: the page to search.
        :param text: the section to search for on the page.
        :returns: a list of result strings in the format `Page#Section`."""
        return [f"{page.title}#{section}" for section in page.sections if text.lower() in section.lower()]

    def advanced_search(self, text: str, limit=5) -> List[SearchResult]:
        """Searches for text with snippets of pages where the text is found

        :param text: the page to search for.
        :param limit: the number of results to fetch.
        :returns: a list of SearchResult objects."""
        return self.wiki.advanced_search(text, results=limit, srprop=["snippet"])
