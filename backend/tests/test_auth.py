import httpx


def test_oauth_flow(client, canvas_oauth_config, mock_canvas_oauth_token_response):
    response = client.post("/auth/callback", params={"code": "valid_auth_code"})
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "mock_access_token"
