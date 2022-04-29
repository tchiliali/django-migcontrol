def until_next_outer(lst, h_tag):
    for element in lst:
        if element.name > h_tag:
            yield element
        else:
            return


def toc(lst):
    """
    Creates a TOC from a list of BeautifulSoup elements

    Called like this:

    toc(soup.find_all(["h1", "h2", "h3", "h4", "h5"]))
    """

    if not lst:
        return []

    item0 = lst[0]

    if len(lst) == 1:
        return [(item0, [])]

    children = toc(list(until_next_outer(lst[1:], item0.name)))
    siblings = [(item0.text, children)]
    start_offset = 1 + len(children)
    for cnt, item in enumerate(lst[start_offset:]):

        if item.name == item0.name:
            children_detect_offset = start_offset + cnt + 1
            children_list = list(
                until_next_outer(lst[children_detect_offset:], item.name)
            )
            siblings.append((item.text, toc(children_list)))

    return siblings
