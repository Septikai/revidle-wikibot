from mediawiki import MediaWiki
from mediawiki.utilities import memoize
from typing import List, Optional
from pydantic import BaseModel, field_validator
import re
import html

class SearchResult(BaseModel):
    ns: int
    title: str
    pageid: int
    size: Optional[int] = None
    wordcount: Optional[int] = None
    snippet: Optional[str] = None
    sectionsnippet: Optional[str] = None
    timestamp: Optional[str] = None #NOTE: Should be parsed into datetime object if there's a use case that requires timestamp

    @field_validator("snippet", mode="before")
    def clean_snippet(cls, v):
        if v is None:
            return v
        # Replace <span class="searchmatch">...</span> with **...**
        v = re.sub(r'<span class="searchmatch">(.*?)</span>', r'**\1**', v)
        v = html.unescape(v)
        return v
    
    @field_validator("sectionsnippet", mode="before")
    def clean_section_snippet(cls, v):
        if v is None:
            return v
        # Replace <span class="searchmatch">...</span> with **...**
        v = re.sub(r'<span class="searchmatch">(.*?)</span>', r'**\1**', v)
        v = html.unescape(v)
        return v


class PatchedMediaWiki(MediaWiki):
    @memoize
    def advanced_search(
        self, query: str, srprop: Optional[List[str]] = None, srnamespace: Optional[List[int]] = None, limit: Optional[int] = None
    ) -> List[SearchResult]:
        """Search text in pages with srprop and srnamespace

        Args:
            query (str): Page title
            limit (Optional[int]): Number of pages to return, set to None means no limit and will attempt to fetch 500
            srprop (Optional[List[str]]): List of srprop included in the response
            srnamespace(Optional[List[int]]): List of namespace ids used for searching, passing None searches all namespaces
        Returns:
            list of SearchResult instances
            class SearchResult(BaseModel):
                ns: int
                title: str
                pageid: int
                size: Optional[int] = None
                wordcount: Optional[int] = None
                snippet: Optional[str] = None
                sectionsnippet: Optional[str] = None
                timestamp: Optional[str] = None        
        """

        self._check_query(query, "Query must be specified")

        max_pull = 500

        search_params = {
            "list": "search",
            "srnamespace": "|".join(map(str, srnamespace)) if srnamespace else "*",
            "srprop": "|".join(srprop) if srprop else "",
            "srlimit": min(limit, max_pull) if limit is not None else max_pull,
            "srsearch": query,
            "sroffset": 0,  # this is what will be used to pull more than the max
        }
    
        raw_results = self.wiki_request(search_params)

        self._check_error_response(raw_results, query)

        search_results = [SearchResult.model_validate(d) for d in raw_results["query"]["search"]]

        return search_results
