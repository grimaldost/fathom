---
name: auth-setup
description: >
  Use to set up treasuryutils authentication, configure an auth profile, or
  diagnose why a source needs credentials a consumer has not configured.
  Triggers for: "set up treasuryutils auth", "configure an auth profile",
  "AUTHENTICATOR__PROFILES", "AUTHENTICATOR__DEFAULT_PROFILE", "which
  auth_profile does this dataset need", "treasuryutils AuthenticationError /
  token refresh failed", "ConfigurationError auth", "UnknownAuthProfileError",
  "scaffold an auth profile / .env", "validate auth credentials", "msal /
  google / bearer / databricks profile", or "gcp-identity / msal-prod profile
  not configured". Drives the deterministic authenticator tooling (doctor /
  scaffold-profile / validate) and the profile primitives — it does not
  reimplement that logic, choose a modality, or read a secret value.
---

# Set Up Authentication Profiles

You are guiding a **treasuryutils consumer** — a human developer *or* an LLM
agent — through configuring authentication so the library can acquire and inject
credentials. treasuryutils resolves credentials from named **auth profiles**
(`AUTHENTICATOR__PROFILES__<name>__*`); a dataset's source declares which profile
it needs via `auth_profile`. A consumer hits an auth gap when a source references
a profile they have not configured (e.g. the bundled `gcp-identity` /
`msal-prod`), or when a configured profile is missing a secret.

Your job is to **orchestrate the deterministic auth tooling**, not to hand-author
`.env` files, choose the authentication modality, or supply secret values. Every
mechanical step delegates to a real function or CLI command. Reserve your own
reasoning for **modality choice, consent, and interaction** — the irreducible
judgment a deterministic tool cannot do.

> **Golden rule:** Never invent or echo a tenant ID, client ID, host, token, or
> any secret value. The tooling tells you the *shape* (which env-var names a
> profile needs, which are set); the user supplies the *values* out-of-band. If
> you cannot infer a value and the user has not given it, **ask** — do not guess,
> and never write or print a real secret.

---

## The deterministic core you drive

All of these are public API on `treasuryutils.authenticator` (Python) and are also
exposed as a CLI via `python -m treasuryutils.authenticator <command>` (or the
`treasuryutils-authenticator` console script). Prefer the CLI for an interactive
setup; reach for the Python API when you need the structured result objects.

| Step | Python API | CLI | What it does |
| --- | --- | --- | --- |
| Diagnose | `auth_status()` → `AuthStatusReport`; render with `render_auth_status(report)` | `doctor` | Reports the default profile and, per configured profile: type, whether required fields are present, the env-var **names** of its secret fields and which are set (a boolean — never the value). A malformed profile is reported, not raised. |
| Scaffold | `scaffold_auth_profile(*, profile_type, name, path=None, overwrite=False)` → `.env` text | `scaffold-profile --type T --name N [--path P] [--overwrite]` | Emits a commented `.env` skeleton of the `AUTHENTICATOR__PROFILES__<name>__<field>` names for the chosen profile type — required fields uncommented-with-placeholder, optional commented, secrets flagged. A no-op until the consumer fills in real values. |
| Validate | `validate_auth(*, profiles=None, connect=False)` → `list[AuthValidationResult]` | `validate [--profile N ...] [--connect]` | Static checks (the profile is configured and its required secrets are set); with `--connect`, also acquires a token **non-interactively** and classifies any failure by `error_kind` (`config` / `auth` / `unknown`). Exits non-zero on any failure. |

These are the **only** mechanisms you use to inspect, generate, and verify auth
profiles. Do not describe the profile schema from memory — let `doctor` and
`scaffold-profile` tell you the truth for the installed version.

> **Three doctors, three jobs.** `treasuryutils doctor` is a *general* library
> health check. `python -m treasuryutils.authenticator doctor` is the *auth*
> deterministic core this skill drives. And the **source → auth_profile** mapping
> (which datasets need which profile) is shown by `treasuryutils-datatools doctor`
> — the authenticator domain cannot read the catalog, so that mapping lives on the
> DataTools side.

---

## Credential tiers per modality

A profile *type* does not map to one credential — the interactive-capable
modalities (`google`, `msal`) resolve through an **ordered set of tiers** and
use the first that succeeds. This model is load-bearing for two later steps
(choosing a modality, and reading a `validate --connect` result), so read it
before either. **The tier that a profile actually authenticates with is not
visible in `doctor`'s configured/complete report — a profile can be complete
and live on a tier that no static or non-interactive check exercises.**

| Modality | Tier 1 | Tier 2 | Tier 3 | Reached by a *non-interactive* acquisition |
| --- | --- | --- | --- | --- |
| `google` | explicit key — `application_credentials` (service-account JSON string or file path) | Application Default Credentials (ADC) — env / metadata server / `gcloud auth application-default login` | cached **interactive** browser login via `pydata_google_auth`, cached under `%APPDATA%\<app_name>` (`app_name` = the library's configured app name), used only when `allow_interactive=true` | tiers 1–2 only — **never tier 3** |
| `msal` | confidential client (service principal) — `client_id` + `tenant_id` + `client_secret` | — | public client — interactive user flow + platform-encrypted **cached** user token (DPAPI / Keychain / libsecret), used only when `allow_interactive=true` | the service-principal tier only — **not the interactive/cached tier** |
| `bearer` | the static token in the profile | — | — | yes (static) |
| `databricks` | the databricks-sdk unified credential chain (host / profile) | — | — | per the SDK chain |

Two consequences a consumer hits in local development:

- A `google` profile with **no** explicit key and **no** ADC on the machine is
  **normally tier 3** — a cached browser login — not broken. "No ADC found" is
  an expected step on the way to tier 3, not a failure.
- Any liveness check that acquires **non-interactively** (that is what
  `validate --connect` does — see step 6) can only reach the tiers in the last
  column. It therefore reports a profile that is live **on the interactive tier**
  as not-live. That verdict is *non-definitive* for an interactive-capable
  profile, and is not grounds to reconfigure the profile or set up ADC.

---

## Prerequisite

The tooling lives in the installed `treasuryutils` package. The CLI needs the
`cli` extra (typer). If `python -m treasuryutils.authenticator doctor` fails with a
"requires the typer package" message, install it first:

```bash
uv add 'treasuryutils[cli]' --index https://packages.stone.tech/repository/pypi-group/simple/
```

(If you only have the Python API, `from treasuryutils.authenticator import auth_status, scaffold_auth_profile, validate_auth` works without the `cli` extra.)

> **Corporate networks (TLS interception).** On a network that intercepts TLS with
> its own CA (a corporate proxy such as Netskope/Zscaler), the cloud SDKs' HTTP
> clients (`google-auth` / `httpx` / gRPC) may reject the intercepted certificate,
> so token acquisition and reads fail with a TLS/SSL verification error even though
> the profile is correct. Point the clients at the corporate CA bundle by exporting
> `REQUESTS_CA_BUNDLE`, `SSL_CERT_FILE`, and `GRPC_DEFAULT_SSL_ROOTS_FILE_PATH` at
> that bundle path. This is a *workaround*: treasuryutils not honoring a custom-CA
> setting on its own is a library-side truststore gap tracked separately — do not
> treat a TLS failure here as a broken auth profile.

---

## Workflow

Run the steps in order. Stop and report if any step cannot proceed.

### 1. Find which profile the work needs

A consumer configures auth because *something they read* requires it. Identify the
target profile name from the source side:

```bash
# Which datasets reference which auth_profile (and is it configured)?
python -m treasuryutils.datatools doctor
```

The dataset whose source you need to read declares an `auth_profile` (e.g.
`gcp-identity` for `cdi_daily` / `di_curve` / `market_fixings`, or `msal-prod` for
`frc_raw` / `sofr_curve_raw`). That is the profile **name** you must configure.
Then see the auth-side truth:

```bash
python -m treasuryutils.authenticator doctor
```

Read the report to the user: the configured profiles, which are complete, and
which secret env-var **names** each expects. A profile the source needs but that
is absent here is the gap to fill.

### 2. Choose the modality — WITH the user

This is the judgment a tool cannot make. The profile **type** determines which
credentials are needed; pick it from how the user actually authenticates to that
source — never default to one. Each interactive-capable type resolves through the
tiers in *Credential tiers per modality* above; the fields below are what the
chosen tier needs:

- `msal` — Azure AD. Service-principal (tier 1): `client_id` + `tenant_id` +
  `client_secret`. User flow (public-client tier): `client_id` + `tenant_id` +
  `allow_interactive=true` (a cached user token, no secret).
- `google` — Google Cloud. Tier 1 an explicit service-account JSON via
  `application_credentials`; tier 2 ADC; tier 3 a cached interactive browser login
  when `allow_interactive=true`. A `google` profile with no explicit key is
  normally tier 2 or 3 — not under-configured.
- `bearer` — a static token issued elsewhere (CI secret store, etc.).
- `databricks` — Databricks unified auth (host / profile via the SDK chain).

If the catalog source names a profile (e.g. `gcp-identity`), its name hints the
modality (`google`), but **confirm with the user** — the name is a convention, not
a guarantee. Ask which modality and which identity they use for that source.

### 3. Scaffold the `.env` skeleton

Generate the variable-name skeleton for the chosen type and name:

```bash
# Print the skeleton to review first
python -m treasuryutils.authenticator scaffold-profile --type google --name gcp-identity
```

Every secret field is flagged `# secret — do NOT commit a real value` and every
value is a placeholder, so the skeleton is safe to write. It lists exactly the
`AUTHENTICATOR__PROFILES__<name>__<field>` names the runtime reads, plus an
`AUTHENTICATOR__DEFAULT_PROFILE` line.

### 4. Interact — fill what cannot be inferred

Uncomment and fill the judgment fields that match the flow you chose in step 2 —
`scaffold-profile` emits every field the modality *could* need, but only
uncomments the ones required for the type's default shape, so a flow that needs
more (e.g. `msal` confidential/service-principal) leaves them commented-out and
optional. For `msal` confidential/service-principal specifically, that means
uncommenting and filling `TENANT_ID` **and** `CLIENT_SECRET`, not just the
uncommented `CLIENT_ID` — leaving them commented silently falls through to the
public-client flow at runtime instead of the one you and the user chose.

For each required field, obtain the value from the user (or a confirmed secret
store reference). Use env indirection for secrets — keep the real token / key /
client_secret out of any file you write and out of your reply. **Set
`allow_interactive=false` for any headless / CI runtime** so an un-provisioned
environment fails fast instead of blocking on a browser prompt. **Do not guess** a
tenant ID, client ID, host, or credential: an unconfirmed value produces a profile
that fails at connect time or, worse, authenticates as the wrong identity.

### 5. Write the artifacts

Write the filled values into the consumer's `.env` / secret store (the variable
names from step 3). **The library reads the `.env` directly (python-dotenv) — do NOT
`source`/`export` it in a shell:** a hyphen in a profile name (e.g. `gcp-identity`)
makes `AUTHENTICATOR__PROFILES__GCP-IDENTITY__*` an invalid shell variable name, so
`source`/`export` silently skips it and the doctor then reports "0 profiles". Point
the process at the file (the library finds `.env` via `find_dotenv`), or set the vars
through your secret store / `os.environ`. Optionally write the skeleton with the CLI:

```bash
python -m treasuryutils.authenticator scaffold-profile --type google --name gcp-identity --path ./auth.env
# then fill in the real values out-of-band; scaffold-profile refuses to clobber without --overwrite
```

Relevant config env vars to mention:

| Env var | Controls |
| --- | --- |
| `AUTHENTICATOR__DEFAULT_PROFILE` | Which configured profile is used when none is named. |
| `AUTHENTICATOR__PROFILES__<name>__type` | The profile modality (`msal` / `google` / `bearer` / `databricks`). |
| `AUTHENTICATOR__PROFILES__<name>__<field>` | The per-modality fields (the scaffold lists them). |

### 6. Verify — `validate --connect`, then reconcile with the tiers model

Confirm the profile is complete and can acquire a token:

```bash
python -m treasuryutils.authenticator validate --connect
python -m treasuryutils.authenticator doctor
```

**What `--connect` actually tests.** It acquires a token *non-interactively* — it
forces `allow_interactive=false` for the probe regardless of the profile's own
setting. Per *Credential tiers per modality*, that reaches only the non-interactive
tiers (for `google`, the explicit-key and ADC tiers; for `msal`, the
service-principal tier). So a `pass` is a real liveness signal, but a **failure on
an interactive-capable profile is non-definitive** — the profile may be live on its
interactive/cached tier, which the probe cannot see. Classify the result:

- **`error_kind: config`** — a required secret is unset, or the profile is not
  configured. Fix the env vars and re-run.
- **`error_kind: auth`** — credentials were rejected (bad secret, expired, wrong
  tenant/host). Correct the value with the user and re-run.
- **`error_kind: unknown`** — an unexpected provider/SDK error; surface the
  message and investigate.
- **A failure on an interactive-capable profile** — a `google` profile with no
  explicit key (`application_credentials` unset) or any profile with
  `allow_interactive=true` — is expected when the profile is meant to run on its
  cached interactive tier, and is **not** grounds to reconfigure it. Acquire a
  token through the profile's **own** allowed flow before concluding anything:

  ```bash
  python -c "from treasuryutils.authenticator import get_authenticator; print(bool(get_authenticator('gcp-identity').get_token()))"
  ```

  If that returns a token, the profile is live (tier 3 / cached interactive) and
  `--connect`'s verdict was a false negative — report it as set up. If it prompts a
  browser and none is available, the interactive login has not been completed on
  this machine yet; complete it once (it caches) rather than switching modality.
  **Do not respond to a failing `google` connect probe by setting up ADC or running
  `gcloud auth application-default login`** — ADC is only tier 2 of 3, and the
  cached interactive login is a first-class tier-3 path that a working profile may
  rely on exclusively.

- The follow-up `doctor` should show the profile complete with its secrets set —
  but remember `doctor` reports *configured/complete*, not *which tier is live*.

`validate` exits non-zero if any profile fails, so it is safe to gate on in a
script — but gate on it for **non-interactive** deployments (CI, headless), where a
`--connect` failure *is* definitive. **Read the structured result fields** (`r.ok`,
`r.error_kind`, `r.connected`) — never treat a printed summary as the pass signal.

### 7. Report status + next steps

Summarize: which profiles are now configured and complete, the verification
result, and which sources they unblock. If a source still cannot be read, route to
the `setup-source-bindings` skill (the source may also need rebinding) — auth and
binding are distinct: auth supplies *credentials*, a binding repoints the *source*.

---

## Guardrails

- **Orchestrate, don't reimplement.** Use `doctor`, `scaffold-profile`, and
  `validate` for every mechanical step. Never hand-derive the profile schema or
  which fields a modality needs from memory — the tooling is the source of truth
  for the installed version.
- **You choose the modality WITH the user, never alone.** The tool will not pick
  `msal` vs `google` vs `bearer` vs `databricks` — that is your judgment, made
  from how the user authenticates, and confirmed with them.
- **Never read, write, or echo a secret value.** The contract is env-var *names* +
  a boolean "set / unset". Reference secrets by name; keep real values in the
  user's secret store. The tooling already enforces this — do not work around it.
- **Never guess an identifier.** Tenant IDs, client IDs, hosts, and credentials
  come from the user — not from assumptions. An unconfirmed identifier can
  silently authenticate as the wrong principal.
- **Non-interactive by default for CI.** Set `allow_interactive=false` on any
  headless profile; `validate --connect` already forces non-interactive token
  acquisition so it never blocks on a browser.
- **`validate --connect` is not definitive for an interactive-capable profile.**
  It only reaches the non-interactive tiers (see *Credential tiers per modality*),
  so it reports a profile that is live on its cached interactive tier as not-live. On
  a `google` profile with no explicit key, or any `allow_interactive=true` profile, a
  connect failure is non-definitive — acquire through the profile's own flow
  (`get_authenticator(name).get_token()`) before concluding misconfiguration, and
  **never default to `gcloud auth application-default login`** (ADC is one tier, not
  the only path). The probe *is* definitive for a headless/CI profile.
- **Verify before claiming success.** Report a profile as set up when it can acquire
  a token: for a headless/service-principal profile, `validate --connect` returns `ok`
  (read the `error_kind`); for an interactive-capable profile, either `--connect` is
  `ok` or a token acquired through its own flow. In both cases `doctor` should show
  its secrets set — while noting `doctor` shows configured/complete, not which tier is live.

---

## Fallback Rules

- If `python -m treasuryutils.authenticator doctor` fails because the CLI is
  unavailable, install the `cli` extra (see Prerequisite) or drive the Python API
  (`auth_status` / `render_auth_status`) instead.
- If `treasuryutils` is not installed at all, stop and provide the install command
  from the Prerequisite section.
- If `doctor` shows **no profiles** but a source needs one, that is the gap to fill
  — proceed from step 2.
- If the issue is that a *source* cannot be reached (not a credential problem),
  route to the `setup-source-bindings` skill. For broader treasuryutils usage,
  route to the `treasuryutils-usage` skill.
