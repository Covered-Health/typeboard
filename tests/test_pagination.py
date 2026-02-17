from typeboard.pagination import Page


def test_page_total_pages():
    p = Page(items=[1, 2, 3], total=10, page=1, page_size=3)
    assert p.total_pages == 4


def test_page_has_next():
    p = Page(items=[1], total=10, page=1, page_size=5)
    assert p.has_next is True


def test_page_has_prev():
    p = Page(items=[1], total=10, page=2, page_size=5)
    assert p.has_prev is True


def test_page_no_prev_on_first():
    p = Page(items=[1], total=10, page=1, page_size=5)
    assert p.has_prev is False
