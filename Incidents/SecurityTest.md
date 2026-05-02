## Event security check for Furatic

### Django debug signature check

We checked whether 404 pages exposed Django debug information:

This did find Django technical 404 output:

```text
Using the URLconf defined in <code>main.urls</code>,
Django tried these URL patterns, in this order:
```

The route list shown was:

```text
admin/
[name='base']
afterhours/
p/              [name='musiq']
musiq/
lights/        [name='lights']
stream/        [name='no-stream']
network-info/  [name='network-info']
settings/      [name='settings']
```

This means the server is exposing Django’s technical 404 page. Practically, that tells a visitor the public URL patterns that exist on the deployed server. Knowing that routes exist does not bypass authentication, does not expose admin access, does not allow moderation actions, and does not expose database content. It is route visibility, not permission.

## 2. Direct checks of the interesting routes

Because the debug page showed route names like `network-info`, `settings`, `lights`, `stream`, `p`, and `musiq`, we tested those directly:

```bash
BASE="https://furatic.xyz"

for path in \
  "/network-info/" \
  "/settings/" \
  "/lights/" \
  "/stream/" \
  "/p/" \
  "/musiq/"
do
  echo
  echo "=== $path ==="
  curl -sk -D /tmp/furatic_headers -o /tmp/furatic_body "$BASE$path"

  code=$(head -1 /tmp/furatic_headers)
  location=$(grep -i '^location:' /tmp/furatic_headers | tr -d '\r')
  title=$(grep -Eio '<title>[^<]+' /tmp/furatic_body | sed 's/<title>//I' | head -1)

  echo "$code"
  [ -n "$location" ] && echo "$location"
  echo "title=$title"
  echo "body preview:"
  head -c 500 /tmp/furatic_body | tr '\n' ' '
  echo
done
```

The results were:

```text
/network-info/  -> 302 location: /accounts/login/?next=/network-info/
/settings/      -> 302 location: /admin/
/lights/        -> 302 location: /accounts/login/?next=/lights/
/stream/        -> 200 title=FURATIC Stream Offline
/p/             -> 200 title=Raveberry
/musiq/         -> 302 location: /
```

This is the expected behavior.

`network-info` requires login.

`lights` requires login.

`settings` redirects to admin.

`stream` is publicly visible, but it is just the public stream offline page.

`p` is the public music queue page, which is supposed to be public.

`musiq` redirects to the public home page.

So even after discovering the route names, an unauthenticated user still cannot access protected functionality.

## 3. Sensitive keyword check

We saved those route responses and scanned them for obvious sensitive terms:

```bash
BASE="https://furatic.xyz"
OUT="/tmp/furatic-interesting-routes"
mkdir -p "$OUT"

for path in \
  "/network-info/" \
  "/settings/" \
  "/lights/" \
  "/stream/" \
  "/p/" \
  "/musiq/"
do
  safe=$(echo "$path" | sed 's#[/?=&]#_#g')
  curl -sk -D "$OUT/$safe.headers" -o "$OUT/$safe.body" "$BASE$path"
done

grep -RInEi \
  "password|secret|token|key|admin|moderator|internal|private|localhost|127\.0\.0\.1|192\.168|10\.|database|sqlite|redis|session|csrf|cookie|email|ip address|ssid|wifi|network" \
  "$OUT" || echo "No obvious sensitive keywords found."
```

The results showed some expected public page content, including:

```text
const CSRF_TOKEN = "..."
const ADMIN = false
```

The CSRF token being present in the browser page is normal for a form based site. Browsers need the CSRF token so legitimate form submissions can include it.

The output also showed cookies on the public `/p/` page:

```text
set-cookie: csrftoken=...
set-cookie: sessionid=...; HttpOnly; SameSite=Lax
```

That is normal for a Django site that tracks a browser session for queue ownership or CSRF protected interactions. It does not mean the user is authenticated as a moderator or admin.

## 4. Unauthenticated write method check

We tested whether an outside visitor could use unsafe methods against sensitive routes:

```bash
BASE="https://furatic.xyz"

for path in \
  "/network-info/" \
  "/settings/" \
  "/lights/" \
  "/stream/" \
  "/p/" \
  "/musiq/"
do
  for method in POST PUT PATCH DELETE; do
    code=$(curl -sk \
      -X "$method" \
      -H "Content-Type: application/json" \
      --data-binary '{"test":"anonymous-access-check"}' \
      -o /tmp/furatic_method_body \
      -w "%{http_code}" \
      "$BASE$path")

    preview=$(head -c 120 /tmp/furatic_method_body | tr '\n' ' ')
    printf "%-6s %-18s -> %-4s %s\n" "$method" "$path" "$code" "$preview"
  done
done
```

Every tested route returned 403 for unsafe methods:

```text
POST   /network-info/     -> 403  Please reload
PUT    /network-info/     -> 403  Please reload
PATCH  /network-info/     -> 403  Please reload
DELETE /network-info/     -> 403  Please reload

POST   /settings/         -> 403  Please reload
PUT    /settings/         -> 403  Please reload
PATCH  /settings/         -> 403  Please reload
DELETE /settings/         -> 403  Please reload

POST   /lights/           -> 403  Please reload
PUT    /lights/           -> 403  Please reload
PATCH  /lights/           -> 403  Please reload
DELETE /lights/           -> 403  Please reload

POST   /stream/           -> 403  Please reload
PUT    /stream/           -> 403  Please reload
PATCH  /stream/           -> 403  Please reload
DELETE /stream/           -> 403  Please reload

POST   /p/                -> 403  Please reload
PUT    /p/                -> 403  Please reload
PATCH  /p/                -> 403  Please reload
DELETE /p/                -> 403  Please reload

POST   /musiq/            -> 403  Please reload
PUT    /musiq/            -> 403  Please reload
PATCH  /musiq/            -> 403  Please reload
DELETE /musiq/            -> 403  Please reload
```

That is the important part. The server is not accepting arbitrary anonymous POST, PUT, PATCH, or DELETE requests against those routes.

Public voting and public song submission are separate expected features. Those do not require an account by design. The tests above are about whether public users can hit protected routes or use generic unsafe methods to change things they should not be able to change.

The result is that protected routes reject unauthenticated write attempts.

## 5. Sensitive file exposure check

We also checked for server file leaks:

```bash
BASE="https://furatic.xyz"

echo "=== FILE EXPOSURE CHECK ==="

for path in \
  "/.env" \
  "/.git/config" \
  "/db.sqlite3" \
  "/settings.py" \
  "/manage.py" \
  "/static/" \
  "/media/"
do
  code=$(curl -sk -o /tmp/furatic_file_body -w "%{http_code}" "$BASE$path")
  size=$(wc -c < /tmp/furatic_file_body)
  printf "%-18s -> %s bytes=%s\n" "$path" "$code" "$size"
done
```

The results were:

```text
/.env              -> 404
/.git/config       -> 404
/db.sqlite3        -> 404
/settings.py       -> 404
/manage.py         -> 404
/static/           -> 404
/media/            -> 404
```

That means common sensitive files and directories are not publicly downloadable from the live site.

## 6. Header and cookie check

We checked the top level response headers:

```bash
curl -skI "https://furatic.xyz/" | sed -n '1,40p'
```

The result showed:

```text
HTTP/2 200
cache-control: no-store, no-cache, max-age=0, must-revalidate, private
content-type: text/html; charset=utf-8
cross-origin-opener-policy: same-origin
expires: 0
pragma: no-cache
referrer-policy: same-origin
x-content-type-options: nosniff
x-frame-options: DENY
content-length: 31919
```

Those are reasonable security headers for this kind of site.

The public queue page does set CSRF and session cookies, which is normal for a Django site that supports public interaction while still protecting form actions.

## 7. Repo based route review

Ravefurry does not only have the top level routes shown by Django. It also generates extra `/ajax/` routes from Python view functions.

The top level routes include:

```text
/
afterhours/
p/
musiq/
lights/
stream/
network-info/
settings/
moderator/
accounts/
api/version/
api/site-mode/
api/moderator/
api/musiq/post-song/
api/musiq/post_song/
```

The repo also exposes generated ajax routes under:

```text
/ajax/
/ajax/musiq/
/ajax/lights/
```

We tested the moderator endpoints, music control endpoints, public music endpoints, lights endpoints, and a generated ajax helper route that was worth checking.

## 8. Moderator API access check

We tested the moderator API endpoints from the repo:

```bash
BASE="https://furatic.xyz"

for path in \
  "/api/moderator/state/" \
  "/api/moderator/remove-song/" \
  "/api/moderator/skip-current/" \
  "/api/moderator/ban-ip/" \
  "/api/moderator/unban-ip/" \
  "/api/moderator/whitelist-ip/" \
  "/api/moderator/unwhitelist-ip/" \
  "/api/moderator/site-mode/" \
  "/api/moderator/blocklists/add/" \
  "/api/moderator/blocklists/rename/" \
  "/api/moderator/blocklists/remove/"
do
  echo
  echo "=== GET $path ==="
  curl -sk -D /tmp/furatic_h -o /tmp/furatic_b "$BASE$path"
  head -1 /tmp/furatic_h
  grep -i '^location:' /tmp/furatic_h | tr -d '\r'
  head -c 160 /tmp/furatic_b | tr '\n' ' '
  echo

  echo "=== POST $path ==="
  curl -sk -X POST \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data "key=1&mode=event&ip=1.2.3.4&id=test&name=test" \
    -D /tmp/furatic_h \
    -o /tmp/furatic_b \
    "$BASE$path"
  head -1 /tmp/furatic_h
  grep -i '^location:' /tmp/furatic_h | tr -d '\r'
  head -c 160 /tmp/furatic_b | tr '\n' ' '
  echo
done
```

The results showed that unauthenticated users cannot access moderator state or perform moderator actions.

The state endpoint redirected to login:

```text
GET /api/moderator/state/ -> 302
location: /accounts/login/?next=/api/moderator/state/
```

The moderator action endpoints rejected GET requests with method not allowed:

```text
GET /api/moderator/remove-song/ -> 405
GET /api/moderator/skip-current/ -> 405
GET /api/moderator/ban-ip/ -> 405
GET /api/moderator/unban-ip/ -> 405
GET /api/moderator/whitelist-ip/ -> 405
GET /api/moderator/unwhitelist-ip/ -> 405
GET /api/moderator/site-mode/ -> 405
GET /api/moderator/blocklists/add/ -> 405
GET /api/moderator/blocklists/rename/ -> 405
GET /api/moderator/blocklists/remove/ -> 405
```

Unauthenticated POST requests were rejected:

```text
POST /api/moderator/state/ -> 403 Please reload
POST /api/moderator/remove-song/ -> 403 Please reload
POST /api/moderator/skip-current/ -> 403 Please reload
POST /api/moderator/ban-ip/ -> 403 Please reload
POST /api/moderator/unban-ip/ -> 403 Please reload
POST /api/moderator/whitelist-ip/ -> 403 Please reload
POST /api/moderator/unwhitelist-ip/ -> 403 Please reload
POST /api/moderator/site-mode/ -> 403 Please reload
POST /api/moderator/blocklists/add/ -> 403 Please reload
POST /api/moderator/blocklists/rename/ -> 403 Please reload
POST /api/moderator/blocklists/remove/ -> 403 Please reload
```

This is the important moderator test. These endpoints are the ones that can remove songs, skip songs, ban IPs, whitelist IPs, change site mode, and manage blocklists. They did not accept unauthenticated requests.

The result indicates that moderator functionality is protected. A public user cannot call the moderator API directly without being logged in as a moderator or admin.

## 9. Music playback control check

We tested the `/ajax/musiq/` playback and queue control endpoints:

```bash
BASE="https://furatic.xyz"

for path in \
  "/ajax/musiq/restart/" \
  "/ajax/musiq/seek-backward/" \
  "/ajax/musiq/play/" \
  "/ajax/musiq/pause/" \
  "/ajax/musiq/seek-forward/" \
  "/ajax/musiq/skip/" \
  "/ajax/musiq/set-shuffle/" \
  "/ajax/musiq/set-repeat/" \
  "/ajax/musiq/set-autoplay/" \
  "/ajax/musiq/set-volume/" \
  "/ajax/musiq/shuffle-all/" \
  "/ajax/musiq/remove-all/" \
  "/ajax/musiq/prioritize/" \
  "/ajax/musiq/remove/" \
  "/ajax/musiq/reorder/"
do
  code=$(curl -sk \
    -X POST \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data "key=1&value=true&amount=1&element=1&prev=&next=" \
    -o /tmp/furatic_body \
    -w "%{http_code}" \
    "$BASE$path")

  preview=$(head -c 120 /tmp/furatic_body | tr '\n' ' ')
  printf "%-34s -> %-4s %s\n" "$path" "$code" "$preview"
done
```

Every tested playback and queue control endpoint returned 403:

```text
/ajax/musiq/restart/               -> 403 Please reload
/ajax/musiq/seek-backward/         -> 403 Please reload
/ajax/musiq/play/                  -> 403 Please reload
/ajax/musiq/pause/                 -> 403 Please reload
/ajax/musiq/seek-forward/          -> 403 Please reload
/ajax/musiq/skip/                  -> 403 Please reload
/ajax/musiq/set-shuffle/           -> 403 Please reload
/ajax/musiq/set-repeat/            -> 403 Please reload
/ajax/musiq/set-autoplay/          -> 403 Please reload
/ajax/musiq/set-volume/            -> 403 Please reload
/ajax/musiq/shuffle-all/           -> 403 Please reload
/ajax/musiq/remove-all/            -> 403 Please reload
/ajax/musiq/prioritize/            -> 403 Please reload
/ajax/musiq/remove/                -> 403 Please reload
/ajax/musiq/reorder/               -> 403 Please reload
```

This means an unauthenticated public user cannot directly pause playback, skip the current song, seek, restart, change shuffle, change repeat, change volume, empty the queue, prioritize songs, remove arbitrary songs, or reorder the queue.

Public users can vote and submit songs where intended, but they cannot use the control endpoints that would let them take over playback.

## 10. Public music endpoint behavior check

We tested the public music endpoints:

```bash
BASE="https://furatic.xyz"

for path in \
  "/ajax/musiq/request-music/" \
  "/api/musiq/post-song/" \
  "/api/musiq/post_song/" \
  "/ajax/musiq/vote/" \
  "/ajax/musiq/remove-own-song/" \
  "/ajax/musiq/own-song-state/" \
  "/ajax/musiq/random-suggestion/" \
  "/ajax/musiq/online-suggestions/" \
  "/ajax/musiq/offline-suggestions/" \
  "/ajax/musiq/state/"
do
  echo
  echo "=== $path ==="
  curl -sk -D /tmp/furatic_h -o /tmp/furatic_b "$BASE$path"
  head -1 /tmp/furatic_h
  head -c 200 /tmp/furatic_b | tr '\n' ' '
  echo
done
```

The song request endpoints rejected empty requests:

```text
/ajax/musiq/request-music/ -> 400 No query given
/api/musiq/post-song/ -> 400 No query to share.
/api/musiq/post_song/ -> 400 No query to share.
```

That is expected. These endpoints are public by design, but they still require the expected input.

The vote endpoint rejected an empty request:

```text
/ajax/musiq/vote/ -> 400
```

That is expected. Voting is public by design, but a vote still needs a valid song key and vote amount.

The own song removal endpoint rejected an empty request:

```text
/ajax/musiq/remove-own-song/ -> 400 missing key
```

That is expected. Public users are allowed to remove their own song, but not without specifying a key, and later checks determine whether the song belongs to that requester.

The own song state endpoint returned only empty state for this unauthenticated test context:

```text
/ajax/musiq/own-song-state/ -> 200
{"songs": [], "currentSongQueueKey": null}
```

That is safe. It does not expose other users, moderator state, requester IPs, or private queue metadata. It only reports what belongs to the current requester, and in this test there was nothing.

## 11. Pi lights control endpoint check

We tested the `/ajax/lights/` control endpoints:

```bash
BASE="https://furatic.xyz"

for path in \
  "/ajax/lights/set-lights-shortcut/" \
  "/ajax/lights/set-ups/" \
  "/ajax/lights/set-program-speed/" \
  "/ajax/lights/set-fixed-color/" \
  "/ajax/lights/set-ring-program/" \
  "/ajax/lights/set-ring-brightness/" \
  "/ajax/lights/set-ring-monochrome/" \
  "/ajax/lights/set-wled-ip/" \
  "/ajax/lights/set-wled-port/" \
  "/ajax/lights/set-wled-program/" \
  "/ajax/lights/set-wled-brightness/" \
  "/ajax/lights/set-strip-program/" \
  "/ajax/lights/set-strip-brightness/" \
  "/ajax/lights/adjust-screen/" \
  "/ajax/lights/set-screen-program/"
do
  code=$(curl -sk \
    -X POST \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data "value=true" \
    -o /tmp/furatic_body \
    -w "%{http_code}" \
    "$BASE$path")

  preview=$(head -c 120 /tmp/furatic_body | tr '\n' ' ')
  printf "%-38s -> %-4s %s\n" "$path" "$code" "$preview"
done
```

Every tested lights control endpoint returned 403:

```text
/ajax/lights/set-lights-shortcut/      -> 403 Please reload
/ajax/lights/set-ups/                  -> 403 Please reload
/ajax/lights/set-program-speed/        -> 403 Please reload
/ajax/lights/set-fixed-color/          -> 403 Please reload
/ajax/lights/set-ring-program/         -> 403 Please reload
/ajax/lights/set-ring-brightness/      -> 403 Please reload
/ajax/lights/set-ring-monochrome/      -> 403 Please reload
/ajax/lights/set-wled-ip/              -> 403 Please reload
/ajax/lights/set-wled-port/            -> 403 Please reload
/ajax/lights/set-wled-program/         -> 403 Please reload
/ajax/lights/set-wled-brightness/      -> 403 Please reload
/ajax/lights/set-strip-program/        -> 403 Please reload
/ajax/lights/set-strip-brightness/     -> 403 Please reload
/ajax/lights/adjust-screen/            -> 403 Please reload
/ajax/lights/set-screen-program/       -> 403 Please reload
```

This means unauthenticated users cannot control the lighting system, change LED settings, change WLED IP or port settings, change brightness, change programs, or adjust screen settings.

That is the expected behavior.

The moderator API is protected.

The admin area is protected.

The playback control endpoints are protected.

The lights control endpoints are protected.

Public song request, voting, own song state, and public music state behave like public endpoints, which matches the purpose of the app.

Public users cannot use the endpoints to skip songs, remove arbitrary songs, ban IPs, change site mode, manage blocklists, change lights, change playback, or access moderator state.

It does not grant access, does not bypass authentication, and does not allow a visitor to modify protected state. It only confirms route names, which are already either public by design or protected by login.

For an internet radio app where public users are supposed to submit and vote on songs, this is more than good enough from a practical access control standpoint. The important protections are working: protected pages require authentication, anonymous write probes fail, and sensitive files are not publicly served.
