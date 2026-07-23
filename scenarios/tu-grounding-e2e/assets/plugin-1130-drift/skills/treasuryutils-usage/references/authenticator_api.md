# Authenticator API Reference (generated)

- treasuryutils_version: `1.8.0`
- generated_at_utc: `2026-07-10T16:08:46.035900+00:00`
- install_extras: `treasuryutils (core)`

## `treasuryutils.authenticator`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `auth_status` | function | `(*, settings_obj: 'TreasuryBaseSettings \| None', source_auth_refs: 'Mapping[str, Sequence[str]] \| None') -> 'AuthStatusReport'` | Build a structured doctor report for the authentication configuration. |
| `AuthenticationError` | class | `(what: 'str', *, why: 'str \| None', fix: 'str \| None', where: 'str \| None', code: 'str') -> 'None'` | Raised when credential acquisition or token refresh fails. |
| `AuthProfile` | callable | `(*args, **kwargs)` | Runtime representation of an annotated type. |
| `BaseAuthenticator` | class | `()` | Abstract base for all authentication providers. |
| `BaseAuthenticator.get_token` | function | `() -> 'str'` | Acquire and return a valid access token. |
| `BearerAuthProfile` | class | `(*, aliases: list[str], allow_interactive: bool, type: Literal['bearer'], token: pydantic.types.SecretStr, scheme: str, expires_at: datetime.datetime \| None, expiry_buffer_seconds: typing.Annotated[int, Ge(ge=0)]) -> None` | Static Bearer-token profile with optional expiry tracking. |
| `BearerTokenAuthenticator` | class | `(token: 'str \| SecretStr', *, scheme: 'str', expires_at: 'datetime.datetime \| None', refresh_callback: 'TokenRefreshCallback \| None', expiry_buffer_seconds: 'int', max_retries: 'int', retry_base_delay: 'float') -> 'None'` | Inject a static or auto-refreshing ``Authorization: Bearer`` header. |
| `BearerTokenAuthenticator.auth_flow` | function | `(request: 'httpx.Request') -> 'Generator[httpx.Request, httpx.Response, None]'` | Implement ``httpx.Auth`` by injecting the Authorization header. |
| `BearerTokenAuthenticator.get_token` | function | `() -> 'str'` | Return the current bearer token, refreshing first if expired. |
| `build_auth_registry` | function | `(*, settings_obj: 'TreasuryBaseSettings', overrides: 'Mapping[str, TokenProvider] \| None') -> 'Mapping[str, TokenProvider]'` | Build a registry mapping profile names and aliases to authenticators. |
| `ConfigurationError` | class | `(what: 'str', *, why: 'str \| None', fix: 'str \| None', where: 'str \| None', code: 'str') -> 'None'` | Raised when authentication configuration is invalid or incomplete. |
| `DatabricksAuthenticator` | class | `(*, host: 'str \| None', profile: 'str \| None', auth_type: 'str \| None', config_file: 'str \| None') -> 'None'` | Delegate authentication to the ``databricks-sdk`` unified credential chain. |
| `DatabricksAuthenticator.auth_flow` | function | `(request: 'httpx.Request') -> 'Generator[httpx.Request, httpx.Response, None]'` | Implement ``httpx.Auth`` by merging SDK-computed headers. |
| `DatabricksAuthenticator.get_token` | function | `() -> 'str'` | Extract the bearer token from the SDK-computed Authorization header. |
| `DatabricksAuthenticator.get_workspace_client` | function | `() -> 'WorkspaceClient'` | Return the cached :class:`~databricks.sdk.WorkspaceClient` instance. |
| `DatabricksAuthProfile` | class | `(*, aliases: list[str], allow_interactive: bool, type: Literal['databricks'], host: str \| None, profile: str \| None, auth_type: str \| None, config_file: str \| None) -> None` | Databricks unified authentication profile. |
| `get_authenticator` | function | `(profile: 'str \| None', *, settings_obj: 'TreasuryBaseSettings', overrides: 'Mapping[str, TokenProvider] \| None') -> 'TokenProvider'` | Resolve and return an authenticator instance. |
| `GoogleAuthenticator` | class | `(application_credentials: 'str \| None', scope: 'list[str] \| str \| None', *, allow_interactive: 'bool', max_retries: 'int', retry_base_delay: 'float') -> 'None'` | Resolve Google Cloud credentials and inject bearer tokens into requests. |
| `GoogleAuthenticator.auth_flow` | function | `(request: 'httpx.Request') -> 'Generator[httpx.Request, httpx.Response, None]'` | Implement ``httpx.Auth`` by injecting a Google bearer token. |
| `GoogleAuthenticator.get_credentials` | function | `() -> 'typing.Any'` | Return the underlying ``google.auth`` credentials (scopes + refresh preserved). |
| `GoogleAuthenticator.get_token` | function | `() -> 'str'` | Return a valid access token, refreshing the credential if needed. |
| `GoogleAuthProfile` | class | `(*, aliases: list[str], allow_interactive: bool, type: Literal['google'], scope: str \| list[str] \| None, application_credentials: pydantic.types.SecretStr \| None) -> None` | Google auth profile (JSON, file path, ADC, optional interactive). |
| `GoogleCredentialsProvider` | class | `(*args, **kwargs)` | Structural contract for the SDK-credentials auth modality. |
| `GoogleCredentialsProvider.get_credentials` | function | `() -> 'Credentials'` | Return a ``google.auth.credentials.Credentials`` for SDK-based access. |
| `MsalAuthenticator` | class | `(*, client_id: 'str', tenant_id: 'str \| None', client_secret: 'str \| None', user_email_hint: 'str \| None', scope: 'str', authority: 'str', enable_cache: 'bool', allow_interactive: 'bool', max_retries: 'int', retry_base_delay: 'float') -> 'None'` | Acquire Azure AD tokens via MSAL, auto-selecting the credential flow. |
| `MsalAuthenticator.auth_flow` | function | `(request: 'httpx.Request') -> 'Generator[httpx.Request, httpx.Response, None]'` | Implement ``httpx.Auth`` by injecting an Azure AD bearer token. |
| `MsalAuthenticator.get_token` | function | `() -> 'str'` | Acquire and return a valid Azure AD access token. |
| `MsalAuthProfile` | class | `(*, aliases: list[str], allow_interactive: bool, type: Literal['msal'], client_id: str, tenant_id: str \| None, client_secret: pydantic.types.SecretStr \| None, user_email_hint: str \| None, scope: str, authority: str, enable_cache: bool) -> None` | MSAL auth profile (service principal or user flow chosen by MSAL authenticator). |
| `render_auth_status` | function | `(report: 'AuthStatusReport') -> 'str'` | Render an :class:`AuthStatusReport` as human-readable text. |
| `resolve_authenticator` | function | `(registry: 'Mapping[str, TokenProvider]', profile: 'str', *, settings_obj: 'TreasuryBaseSettings') -> 'TokenProvider'` | Resolve *profile* from an already-built *registry*, normalizing the lookup key. |
| `scaffold_auth_profile` | function | `(*, profile_type: 'str', name: 'str', path: 'str \| Path \| None', overwrite: 'bool') -> 'str'` | Build a commented ``.env`` skeleton for one authentication profile. |
| `TokenProvider` | class | `(*args, **kwargs)` | Structural contract for objects that supply an access token. |
| `TokenProvider.get_token` | function | `() -> 'str'` | Acquire and return a valid access token. |
| `UnknownAuthProfileError` | class | `(message: 'str', *, code: 'str') -> 'None'` | Raised when a requested authentication profile name cannot be resolved. |
| `validate_auth` | function | `(*, profiles: 'list[str] \| None', connect: 'bool', token_probe: 'Callable[[str], str] \| None', settings_obj: 'TreasuryBaseSettings') -> 'list[AuthValidationResult]'` | Validate configured auth profiles, collecting per-profile results. |
| `WorkspaceClientProvider` | class | `(*args, **kwargs)` | Structural contract for the SDK-client auth modality. |
| `WorkspaceClientProvider.get_workspace_client` | function | `() -> 'WorkspaceClient'` | Return a ``databricks.sdk.WorkspaceClient`` for SDK-based access. |

## `treasuryutils.authenticator.base`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `BaseAuthenticator` | class | `()` | Abstract base for all authentication providers. |
| `BaseAuthenticator.get_token` | function | `() -> 'str'` | Acquire and return a valid access token. |

## `treasuryutils.authenticator.bearer_authenticator`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `BearerTokenAuthenticator` | class | `(token: 'str \| SecretStr', *, scheme: 'str', expires_at: 'datetime.datetime \| None', refresh_callback: 'TokenRefreshCallback \| None', expiry_buffer_seconds: 'int', max_retries: 'int', retry_base_delay: 'float') -> 'None'` | Inject a static or auto-refreshing ``Authorization: Bearer`` header. |
| `BearerTokenAuthenticator.auth_flow` | function | `(request: 'httpx.Request') -> 'Generator[httpx.Request, httpx.Response, None]'` | Implement ``httpx.Auth`` by injecting the Authorization header. |
| `BearerTokenAuthenticator.get_token` | function | `() -> 'str'` | Return the current bearer token, refreshing first if expired. |

## `treasuryutils.authenticator.databricks_authenticator`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `DatabricksAuthenticator` | class | `(*, host: 'str \| None', profile: 'str \| None', auth_type: 'str \| None', config_file: 'str \| None') -> 'None'` | Delegate authentication to the ``databricks-sdk`` unified credential chain. |
| `DatabricksAuthenticator.auth_flow` | function | `(request: 'httpx.Request') -> 'Generator[httpx.Request, httpx.Response, None]'` | Implement ``httpx.Auth`` by merging SDK-computed headers. |
| `DatabricksAuthenticator.get_token` | function | `() -> 'str'` | Extract the bearer token from the SDK-computed Authorization header. |
| `DatabricksAuthenticator.get_workspace_client` | function | `() -> 'WorkspaceClient'` | Return the cached :class:`~databricks.sdk.WorkspaceClient` instance. |

## `treasuryutils.authenticator.errors`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `AuthenticationError` | class | `(what: 'str', *, why: 'str \| None', fix: 'str \| None', where: 'str \| None', code: 'str') -> 'None'` | Raised when credential acquisition or token refresh fails. |
| `ConfigurationError` | class | `(what: 'str', *, why: 'str \| None', fix: 'str \| None', where: 'str \| None', code: 'str') -> 'None'` | Raised when authentication configuration is invalid or incomplete. |

## `treasuryutils.authenticator.factory`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `build_auth_registry` | function | `(*, settings_obj: 'TreasuryBaseSettings', overrides: 'Mapping[str, TokenProvider] \| None') -> 'Mapping[str, TokenProvider]'` | Build a registry mapping profile names and aliases to authenticators. |
| `get_authenticator` | function | `(profile: 'str \| None', *, settings_obj: 'TreasuryBaseSettings', overrides: 'Mapping[str, TokenProvider] \| None') -> 'TokenProvider'` | Resolve and return an authenticator instance. |
| `UnknownAuthProfileError` | class | `(message: 'str', *, code: 'str') -> 'None'` | Raised when a requested authentication profile name cannot be resolved. |

## `treasuryutils.authenticator.google_authenticator`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `GoogleAuthenticator` | class | `(application_credentials: 'str \| None', scope: 'list[str] \| str \| None', *, allow_interactive: 'bool', max_retries: 'int', retry_base_delay: 'float') -> 'None'` | Resolve Google Cloud credentials and inject bearer tokens into requests. |
| `GoogleAuthenticator.auth_flow` | function | `(request: 'httpx.Request') -> 'Generator[httpx.Request, httpx.Response, None]'` | Implement ``httpx.Auth`` by injecting a Google bearer token. |
| `GoogleAuthenticator.get_credentials` | function | `() -> 'typing.Any'` | Return the underlying ``google.auth`` credentials (scopes + refresh preserved). |
| `GoogleAuthenticator.get_token` | function | `() -> 'str'` | Return a valid access token, refreshing the credential if needed. |

## `treasuryutils.authenticator.msal_authenticator`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `MsalAuthenticator` | class | `(*, client_id: 'str', tenant_id: 'str \| None', client_secret: 'str \| None', user_email_hint: 'str \| None', scope: 'str', authority: 'str', enable_cache: 'bool', allow_interactive: 'bool', max_retries: 'int', retry_base_delay: 'float') -> 'None'` | Acquire Azure AD tokens via MSAL, auto-selecting the credential flow. |
| `MsalAuthenticator.auth_flow` | function | `(request: 'httpx.Request') -> 'Generator[httpx.Request, httpx.Response, None]'` | Implement ``httpx.Auth`` by injecting an Azure AD bearer token. |
| `MsalAuthenticator.get_token` | function | `() -> 'str'` | Acquire and return a valid Azure AD access token. |

## `treasuryutils.authenticator.profiles`

| Symbol | Kind | Signature | Description |
| --- | --- | --- | --- |
| `AuthProfile` | callable | `(*args, **kwargs)` | Runtime representation of an annotated type. |
| `AuthProfileBase` | class | `(*, aliases: list[str], allow_interactive: bool) -> None` | Base schema for an authentication profile. |
| `BearerAuthProfile` | class | `(*, aliases: list[str], allow_interactive: bool, type: Literal['bearer'], token: pydantic.types.SecretStr, scheme: str, expires_at: datetime.datetime \| None, expiry_buffer_seconds: typing.Annotated[int, Ge(ge=0)]) -> None` | Static Bearer-token profile with optional expiry tracking. |
| `DatabricksAuthProfile` | class | `(*, aliases: list[str], allow_interactive: bool, type: Literal['databricks'], host: str \| None, profile: str \| None, auth_type: str \| None, config_file: str \| None) -> None` | Databricks unified authentication profile. |
| `GoogleAuthProfile` | class | `(*, aliases: list[str], allow_interactive: bool, type: Literal['google'], scope: str \| list[str] \| None, application_credentials: pydantic.types.SecretStr \| None) -> None` | Google auth profile (JSON, file path, ADC, optional interactive). |
| `MsalAuthProfile` | class | `(*, aliases: list[str], allow_interactive: bool, type: Literal['msal'], client_id: str, tenant_id: str \| None, client_secret: pydantic.types.SecretStr \| None, user_email_hint: str \| None, scope: str, authority: str, enable_cache: bool) -> None` | MSAL auth profile (service principal or user flow chosen by MSAL authenticator). |
