"""GitHub OAuth2 provider.

**Feature: code-review-refactoring, Task 5.8: Extract GitHub provider**
**Validates: Requirements 4.3**
"""

import httpx

from ..base import BaseOAuthProvider
from ..enums import OAuthProvider, PROVIDER_CONFIGS
from ..exceptions import OAuthUserInfoError
from ..models import OAuthConfig, OAuthUserInfo


class GitHubOAuthProvider(BaseOAuthProvider):
    """GitHub OAuth2 provider."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: tuple[str, ...] | None = None,
    ) -> None:
        """Initialize GitHub OAuth provider.

        Args:
            client_id: GitHub OAuth client ID.
            client_secret: GitHub OAuth client secret.
            redirect_uri: Callback URL.
            scopes: Permission scopes (defaults to user:email).
        """
        defaults = PROVIDER_CONFIGS[OAuthProvider.GITHUB]
        config = OAuthConfig(
            provider=OAuthProvider.GITHUB,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scopes=scopes or ("user:email",),
            authorize_url=defaults["authorize_url"],
            token_url=defaults["token_url"],
            userinfo_url=defaults["userinfo_url"],
        )
        super().__init__(config)

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get user info from GitHub.

        Args:
            access_token: GitHub access token.

        Returns:
            Normalized user information.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self._config.userinfo_url,
                    headers=headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                email = data.get("email")
                email_verified = False

                if not email:
                    email_response = await client.get(
                        "https://api.github.com/user/emails",
                        headers=headers,
                        timeout=30.0,
                    )
                    if email_response.status_code == 200:
                        emails = email_response.json()
                        for e in emails:
                            if e.get("primary"):
                                email = e.get("email")
                                email_verified = e.get("verified", False)
                                break

                name = data.get("name") or data.get("login")
                name_parts = (name or "").split(" ", 1)
                given_name = name_parts[0] if name_parts else None
                family_name = name_parts[1] if len(name_parts) > 1 else None

                return OAuthUserInfo(
                    provider=OAuthProvider.GITHUB,
                    provider_user_id=str(data.get("id", "")),
                    email=email,
                    email_verified=email_verified,
                    name=name,
                    given_name=given_name,
                    family_name=family_name,
                    picture=data.get("avatar_url"),
                    locale=None,
                    raw_data=data,
                )
            except httpx.HTTPStatusError as e:
                raise OAuthUserInfoError(
                    f"Failed to get GitHub user info: {e.response.text}"
                ) from e
            except httpx.RequestError as e:
                raise OAuthUserInfoError(f"GitHub user info request failed: {e}") from e
