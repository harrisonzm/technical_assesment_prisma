from app.repositories.pagination import Page


def test_page_has_no_next_page_when_last_item_is_reached():
    page = Page(items=[1], total=3, offset=2, limit=2)

    assert page.has_next is False
