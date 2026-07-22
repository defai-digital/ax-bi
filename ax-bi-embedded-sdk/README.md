<!--
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
-->

[![Version](https://img.shields.io/npm/v/%40ax-bi%2Fembedded-sdk?style=flat)](https://www.npmjs.com/package/@ax-bi/embedded-sdk)
[![Libraries.io](https://img.shields.io/librariesio/release/npm/%40ax-bi%2Fembedded-sdk?style=flat)](https://libraries.io/npm/@ax-bi%2Fembedded-sdk)

# AX BI Embedded SDK

The AX BI Embedded SDK mounts AX BI dashboards inside your application with
an iframe and a guest-token based authentication flow.

Use it when you want users to view an AX BI dashboard from your product without
signing in to AX BI directly. Your application remains responsible for
authenticating the user, requesting or minting an AX BI guest token, and passing
that token to the SDK.

## Quick Start

### 1. Enable Embedded AX BI

In your AX BI configuration (`axbi_config.py`):

- Enable the `EMBEDDED_AXBI` feature flag.
- Set a strong `GUEST_TOKEN_JWT_SECRET`.
- Configure `GUEST_TOKEN_JWT_AUDIENCE` if you mint guest tokens outside the
  AX BI API.
- Make sure the dashboard's embedded settings allow the host application domain.

### 2. Install the SDK

```sh
npm install --save @ax-bi/embedded-sdk
```

For local testing from this repository:

```sh
cd ax-bi-embedded-sdk
npm ci
npm run build
npm link

cd /path/to/your/test-app
npm link @ax-bi/embedded-sdk
```

### 3. Embed a Dashboard

```ts
import { embedDashboard } from '@ax-bi/embedded-sdk';

const embeddedDashboard = await embedDashboard({
  id: 'abc123', // given by the AX BI embedding UI
  axbiDomain: 'https://axbi.example.com',
  mountPoint: document.getElementById('my-axbi-container')!,
  fetchGuestToken: () => fetchGuestTokenFromBackend(),
  dashboardUiConfig: {
    hideTitle: true,
    filters: {
      visible: true,
      expanded: true,
    },
    urlParams: {
      foo: 'value1',
      bar: 'value2',
      themeMode: 'dark',
    },
  },
  iframeTitle: 'Sales Dashboard',
  iframeSandboxExtras: ['allow-top-navigation'],
  iframeAllowExtras: ['clipboard-write', 'fullscreen'],
  referrerPolicy: 'same-origin',
  resolvePermalinkUrl: ({ key }) => `https://my-app.com/analytics/share/${key}`,
});

embeddedDashboard.setThemeMode('system');
```

## Browser Script Usage

You can load the SDK from a CDN. The package exposes
`axbiEmbeddedSdk` on `window`.

```html
<script src="https://unpkg.com/@ax-bi/embedded-sdk"></script>

<script>
  axbiEmbeddedSdk.embedDashboard({
    id: 'abc123',
    axbiDomain: 'https://axbi.example.com',
    mountPoint: document.getElementById('my-axbi-container'),
    fetchGuestToken: () => fetchGuestTokenFromBackend(),
  });
</script>
```

## Guest Token Flow

Embedded resources use guest tokens to grant limited AX BI access to users
authenticated by your application. Your frontend supplies the SDK with a
`fetchGuestToken` function. That function should call your backend, not AX BI
directly, so your AX BI credentials and token-signing secrets stay server-side.

The SDK sends the guest token into the embedded iframe and refreshes it before it
expires. If a refresh call fails, the SDK retries. If `fetchGuestToken` never
settles, the SDK times it out after 30 seconds by default.

### Requesting a Guest Token from AX BI

From your backend, send a `POST` request to AX BI's
`/security/guest_token` endpoint. The caller must be authenticated with the
`can_grant_guest_token` permission.

The `user` object is optional. Its values can be used in Jinja templates inside
charts. The `rls` clauses apply row-level security filters for the guest user.

Example `POST /security/guest_token` payload:

```json
{
  "user": {
    "username": "stan_lee",
    "first_name": "Stan",
    "last_name": "Lee"
  },
  "resources": [
    {
      "type": "dashboard",
      "id": "abc123"
    }
  ],
  "rls": [{ "clause": "publisher = 'Nintendo'" }]
}
```

### Minting a Guest Token Directly

You can also mint a guest token in your backend without calling the AX BI API.
Use the same `GUEST_TOKEN_JWT_SECRET` configured in AX BI. If you set
`GUEST_TOKEN_JWT_AUDIENCE`, the JWT `aud` claim must match it.

```json
{
  "user": {
    "username": "embedded@embedded.fr",
    "first_name": "embedded",
    "last_name": "embedded"
  },
  "resources": [
    {
      "type": "dashboard",
      "id": "d73e7841-9342-4afd-8e29-b4a416a2498c"
    }
  ],
  "rls_rules": [],
  "iat": 1730883214,
  "exp": 1732956814,
  "aud": "superset",
  "type": "guest"
}
```

Matching AX BI configuration:

```python
GUEST_TOKEN_JWT_AUDIENCE = "superset"
```

## Configuration Reference

### `embedDashboard(params)`

| Parameter | Type | Required | Description |
| --------- | ---- | -------- | ----------- |
| `id` | `string` | Yes | Dashboard embed ID from AX BI's embedding UI. |
| `axbiDomain` | `string` | Yes | AX BI origin, including protocol. Example: `https://axbi.example.com`. |
| `mountPoint` | `HTMLElement` | Yes | Container element that will be replaced with the embedded iframe. |
| `fetchGuestToken` | `() => Promise<string>` | Yes | Host callback that returns a valid guest token. |
| `dashboardUiConfig` | `UiConfigType` | No | Dashboard display options and URL parameters. |
| `debug` | `boolean` | No | Enables console debug logs from the SDK. |
| `iframeTitle` | `string` | No | iframe `title` attribute. Defaults to `Embedded Dashboard`. |
| `iframeSandboxExtras` | `string[]` | No | Additional iframe sandbox tokens. |
| `iframeAllowExtras` | `string[]` | No | Additional iframe Permissions Policy features. `fullscreen` and `clipboard-write` are included by default. |
| `referrerPolicy` | `ReferrerPolicy` | No | iframe `referrerPolicy` value. |
| `resolvePermalinkUrl` | `({ key }) => string \| Promise<string>` | No | Callback used to rewrite dashboard permalink URLs. |
| `guestTokenFetchTimeoutMs` | `number` | No | Timeout for each `fetchGuestToken` call. Defaults to `30000`. Set to `0` to disable. |

### Dashboard UI Config

```ts
type UiConfigType = {
  hideTitle?: boolean;
  hideTab?: boolean;
  hideChartControls?: boolean;
  emitDataMasks?: boolean;
  filters?: {
    visible?: boolean;
    expanded?: boolean;
  };
  urlParams?: Record<string, string | number | boolean>;
  showRowLimitWarning?: boolean;
};
```

Common `urlParams` values:

| Parameter | Description |
| --------- | ----------- |
| `themeMode` | Initial theme mode: `default`, `dark`, or `system`. |
| `permalink_key` | Restores dashboard state from a permalink key. |
| Any custom key | Forwarded to the embedded dashboard URL. |

### Returned Dashboard API

`embedDashboard` resolves to an `EmbeddedDashboard` object.

| Method | Description |
| ------ | ----------- |
| `getScrollSize()` | Returns the embedded dashboard scroll width and height. |
| `unmount()` | Removes the iframe and stops guest token refresh timers. |
| `getDashboardPermalink(anchor)` | Creates a dashboard permalink for the given anchor. |
| `getActiveTabs()` | Returns active dashboard tab IDs. |
| `observeDataMask(callback)` | Subscribes to data mask changes emitted by the embedded dashboard. |
| `getDataMask()` | Returns the dashboard data mask. |
| `getChartStates()` | Returns chart state metadata. |
| `getChartDataPayloads(params?)` | Returns chart data payloads, optionally for one `chartId`. |
| `setThemeConfig(themeConfig)` | Sends a runtime theme config to the embedded dashboard. |
| `setThemeMode(mode)` | Sets runtime theme mode to `default`, `dark`, or `system`. |

## Theme Mode

Use the `themeMode` URL parameter to control the embedded dashboard's initial colour scheme:

```ts
embedDashboard({
  id: 'abc123',
  axbiDomain: 'https://axbi.example.com',
  mountPoint: document.getElementById('my-axbi-container')!,
  fetchGuestToken: () => fetchGuestTokenFromBackend(),
  dashboardUiConfig: {
    urlParams: {
      themeMode: 'dark',
    },
  },
});
```

The supported values are:

| Value     | Behaviour                                                 |
| --------- | --------------------------------------------------------- |
| `default` | Light theme (AX BI default)                              |
| `dark`    | Dark theme                                                |
| `system`  | Follows the user's OS preference (`prefers-color-scheme`) |

You can also change the theme at runtime:

```ts
embeddedDashboard.setThemeMode('system');
```

## iframe Security Options

### Sandbox

The SDK creates an iframe with sandbox mode enabled. It always includes the
sandbox tokens needed for embedded dashboards to run. Add extra tokens only when
your host application requires them.

```ts
embedDashboard({
  // ...
  iframeSandboxExtras: ['allow-top-navigation', 'allow-popups-to-escape-sandbox'],
});
```

### Permissions Policy

Use `iframeAllowExtras` to add browser features to the iframe's
[Permissions Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/Permissions_Policy)
through the `allow` attribute.

```ts
embedDashboard({
  // ...
  iframeAllowExtras: ['clipboard-write', 'fullscreen'],
});
```

Common permissions you might need:

- `clipboard-write`: copy permalink to clipboard.
- `fullscreen`: fullscreen chart viewing.
- `camera`, `microphone`: dashboards that use media capture features.

### Referrer Policy

AX BI validates the host domain for embedded dashboards using the `Referer`
header. If your host app applies a restrictive referrer policy, AX BI may not
receive the header it needs.

Set `referrerPolicy` when the host page policy would otherwise omit the
`Referer` header.

```ts
embedDashboard({
  // ...
  referrerPolicy: 'same-origin',
});
```

## Permalink URLs

When users click share buttons inside an embedded dashboard, AX BI generates
permalinks using AX BI's domain. Use `resolvePermalinkUrl` to map those links
to your application's domain.

```ts
embedDashboard({
  id: 'abc123',
  axbiDomain: 'https://axbi.example.com',
  mountPoint: document.getElementById('my-axbi-container')!,
  fetchGuestToken: () => fetchGuestTokenFromBackend(),
  resolvePermalinkUrl: ({ key }) => {
    return `https://my-app.com/analytics/share/${key}`;
  },
});
```

To restore the dashboard state from a permalink in your app:

```ts
const permalinkKey = routeParams.key;

embedDashboard({
  id: 'abc123',
  axbiDomain: 'https://axbi.example.com',
  mountPoint: document.getElementById('my-axbi-container')!,
  fetchGuestToken: () => fetchGuestTokenFromBackend(),
  resolvePermalinkUrl: ({ key }) => `https://my-app.com/analytics/share/${key}`,
  dashboardUiConfig: {
    urlParams: {
      permalink_key: permalinkKey,
    },
  },
});
```

## Build Outputs

The package build creates three output directories:

| Directory | Purpose |
| --------- | ------- |
| `lib` | Babel output for package-manager consumers. |
| `bundle` | Webpack browser bundle used by the package `main` field and CDN usage. |
| `dist` | TypeScript declaration files. |

Run the package build with:

```sh
npm run build
```

## Troubleshooting

| Symptom | Check |
| ------- | ----- |
| The iframe loads an AX BI error page | Confirm `EMBEDDED_AXBI` is enabled and the dashboard is configured for embedding. |
| The dashboard is rejected by domain validation | Confirm the host app domain is allowed in AX BI and the iframe sends a `Referer` header. |
| The iframe stays blank | Confirm `fetchGuestToken` resolves to a valid guest token and watch the browser console with `debug: true`. |
| The session expires | Confirm guest tokens have a valid `exp` claim and `fetchGuestToken` can refresh them. |
| Clipboard or fullscreen features fail | Add the needed feature to `iframeAllowExtras`. |
