"""Google OAuth2/OIDC provider.

**Feature: code-review-refactoring, Task 5.7: Extract Google provider**
**Validates: Requirements 4.2**
"""

import httpx

from ..base import BaseOAuthProvider
from ..enums import OAuthProvider, PROVIDER_CONFIGS
from ..exceptions import OAuthUserInfoError
from ..models import OAuthConfig, OAuthUserInfo


class GoogleOAuthProvider(BaseOAuthProvider):
    """Google OAuth2/OIDC provider."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: tuple[str, ...] | None = None,
    ) -> None:
        """Initialize Google OAuth provider.

        Args:
            client_id: Google OAuth client ID.
            client_secret: Google OAuth client secret.
            redirect_uri: Callback URL.
            scopes: Permission scopes (defaults to openid, email, profile).
        """
        defaults = PROVIDER_CONFIGS[OAuthProvider.GOOGLE]
        config = OAuthConfig(
            provider=OAuthProvider.GOOGLE,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scopes=scopes or ("openid", "email", "profile"),
            authorize_url=defaults["authorize_url"],
            token_url=defaults["token_url"],
            userinfo_url=defaults["userinfo_url"],
            jwks_url=defaults["jwks_url"],
        )
        super().__init__(config)

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """Get user info from Google.

        Args:
            access_token: Google access token.

        Returns:
            Normalized user information.
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self._config.userinfo_url,
                    headers=headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                return OAuthUserInfo(
                    provider=OAuthProvider.GOOGLE,
                    provider_user_id=data.get("sub", ""),
                    email=data.get("email"),
                    email_verified=data.get("email_verified", False),
                    name=data.get("name"),
                    given_name=data.get("given_name"),
                    family_name=data.get("family_name"),
                    picture=data.get("picture"),
                    locale=data.get("locale"),
                    raw_data=data,
                )
            except httpx.HTTPStatusError as e:
                raise OAuthUserInfoError(
                    f"Failed to get Google user info: {e.response.text}"
                ) from e
            except httpx.RequestError as e:
                raise OAuthUserInfoError(f"Google user info request failed: {e}") from e
