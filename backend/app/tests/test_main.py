def test_read_main(client):
    """Test the main endpoint returns the expected status code and response."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}
