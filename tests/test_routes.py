def test_home_page(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"<!DOCTYPE html" in response.data or b"<html" in response.data


def test_about_page(client):
    response = client.get("/about")

    assert response.status_code == 200
    assert b"<!DOCTYPE html" in response.data or b"<html" in response.data


def test_contact_page(client):
    response = client.get("/contact")

    assert response.status_code == 200
    assert b"<!DOCTYPE html" in response.data or b"<html" in response.data