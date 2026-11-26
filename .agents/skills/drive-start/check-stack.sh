#!/usr/bin/env bash
# Read-only report on the Drive development stack, for the drive-start skill.
#
# It changes nothing: no build, no pull, no container of the stack started or
# stopped (only short-lived `docker run --rm ... cat` ones, to read a file baked
# in an image).
# It prints what is missing, stale or running, then a suggested plan made of
# Makefile targets where one exists. Run it from anywhere in the repository:
#
#   bash .agents/skills/drive-start/check-stack.sh
#
# Works on Linux and macOS.

# no `set -u`: empty arrays are "unbound" under bash 3.2 (macOS)

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || {
  echo "Not inside the Drive repository"
  exit 2
}
cd "$ROOT" || exit 2

# Same user the Makefile runs the containers with: plain `docker compose`
# commands have to pass it too, or the bind-mounted files end up unwritable.
DOCKER_USER="$(id -u):$(id -g)"

PLAN=()
NOTES=()
plan() { PLAN+=("$1"); }
note() { NOTES+=("$1"); }

# -- portable helpers ---------------------------------------------------------

to_epoch() { # docker ISO 8601 date, "...Z" or "...+02:00" -> seconds
  date -d "$1" +%s 2>/dev/null && return
  # BSD date (macOS): no fractional seconds, and the offset spelled +hhmm
  local tz
  tz=$(echo "${1:19}" | sed 's/^\.[0-9]*//; s/^Z$/+00:00/; s/://')
  date -j -f '%Y-%m-%dT%H:%M:%S%z' "${1:0:19}${tz}" +%s 2>/dev/null || echo 0
}
mtime() { stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null || echo 0; }
# `version = ` lines are dropped: a release bumps the version of the project
# itself in pyproject.toml and uv.lock, which installs nothing new. A bumped
# dependency still shows, through its pin (pyproject.toml) or its URLs and
# hashes (uv.lock).
fhash() { grep -v '^version = ' | git hash-object --stdin; }
img_cat() { docker run --rm --entrypoint cat "$1" "$2" 2>/dev/null; }
head_at() { # commit HEAD pointed to at a given epoch, from the reflog
  git log -g --date=unix --format='%gd %H' HEAD 2>/dev/null |
    sed -n 's/^HEAD@{\([0-9]*\)} \(.*\)/\1 \2/p' |
    awk -v t="$1" '$1 <= t { print $2; exit }'
}

# -- docker -------------------------------------------------------------------

echo "== Docker"
if ! docker info >/dev/null 2>&1; then
  echo "daemon: NOT REACHABLE"
  echo
  echo "== Suggested plan"
  echo "1. Start Docker, then run this check again"
  exit 1
fi
echo "daemon: ok"
if docker network inspect lasuite-network >/dev/null 2>&1; then
  echo "network lasuite-network: ok"
else
  echo "network lasuite-network: MISSING"
fi

# -- local setup files --------------------------------------------------------
# Docker creates a missing bind-mounted directory as root: the containers,
# which run as the host user, then cannot write to it.

echo
echo "== Local setup files"
missing_local=()
for f in $(sed -n 's#^[[:space:]]*@touch \(env\.d/development/[^[:space:]]*\.local\).*#\1#p' Makefile) \
  data/postgresql.local src/frontend/node_modules src/frontend/apps/drive/node_modules; do
  [ -e "$f" ] || missing_local+=("$f")
done
if [ ${#missing_local[@]} -eq 0 ]; then
  echo "local files and directories: ok"
else
  echo "MISSING: ${missing_local[*]}"
fi
missing_data=()
for d in data/media data/static; do
  [ -d "$d" ] || missing_data+=("$d")
done
[ ${#missing_data[@]} -gt 0 ] && echo "MISSING: ${missing_data[*]}"

# -- containers ---------------------------------------------------------------

PS=$(docker compose ps -a --format '{{.Service}} {{.State}}' 2>/dev/null)
state() { # no associative array: macOS still ships bash 3.2
  local s
  s=$(echo "$PS" | awk -v svc="$1" '$1 == svc { print $2; exit }')
  echo "${s:-absent}"
}

# -- backend database ---------------------------------------------------------
# `make run-backend-e2e` runs the same services on another database, selected
# by ENV_OVERRIDE=e2e. Every command of the plan has to keep that choice, or
# it recreates the containers on the development database.

echo
echo "== Backend database"
env_of() { # environment of the container of a service, running or stopped
  local cid
  cid=$(docker compose ps -a -q "$1" 2>/dev/null | head -1)
  [ -n "$cid" ] && docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$cid" 2>/dev/null
}
# stopped containers count too: they tell which database was used last
BACKEND_MODE=dev
if [ "${ENV_OVERRIDE:-}" = "e2e" ] ||
  env_of app-dev | grep -q '^DB_NAME=drive_e2e$' ||
  env_of postgresql | grep -q '^POSTGRES_DB=drive_e2e$'; then
  BACKEND_MODE=e2e
fi
if [ "$BACKEND_MODE" = "e2e" ]; then
  echo "mode: e2e (the backend containers are set on the drive_e2e database)"
  ENVP="ENV_OVERRIDE=e2e "
  RUN_BACKEND="make run-backend-e2e"
  note "the backend containers are set on the E2E database: \`make run-backend\` (or \`make run\`) switches back to the development one, \`make run-backend-e2e\` keeps this one"
else
  echo "mode: dev"
  ENVP=""
  RUN_BACKEND="make run-backend"
fi
COMPOSE="${ENVP}DOCKER_USER=$DOCKER_USER docker compose"

# -- frontend mode ------------------------------------------------------------

echo
echo "== Frontend (:3000)"
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://localhost:3000/ 2>/dev/null)
fe_state=$(state frontend-dev)
have_yarn=0
command -v yarn >/dev/null 2>&1 && have_yarn=1
if [ "$fe_state" = "running" ]; then
  FRONTEND_MODE=container
  echo "served by the frontend-dev container (http $code)"
elif [ "$code" != "000" ] && [ -n "$code" ] &&
  curl -sI --max-time 3 http://localhost:3000/ 2>/dev/null | grep -qi '^x-powered-by: next'; then
  FRONTEND_MODE=local
  echo "served by a process on the host, not by docker (http $code): local \`yarn dev\`"
elif [ "$have_yarn" -eq 1 ]; then
  FRONTEND_MODE=undecided
  echo "nothing on :3000; yarn is installed on the host"
else
  # `make run-frontend-development` needs yarn on the host
  FRONTEND_MODE=container
  echo "nothing on :3000; yarn is not installed: the container will serve it"
fi
if [ "$fe_state" != "running" ] && [ "$code" != "000" ] && [ -n "$code" ] && [ "$FRONTEND_MODE" != "local" ]; then
  note "something that is not a Next.js dev server answers on :3000 (http $code): free the port before starting the frontend"
fi
echo "mode: $FRONTEND_MODE"

# The container and a local `yarn dev` share the same node_modules: the bind
# mount of src/frontend hides the ones installed in the image.
FE_DEPS=ok
integrity=src/frontend/node_modules/.yarn-integrity
if [ ! -f "$integrity" ]; then
  FE_DEPS=missing
  echo "node_modules: NOT INSTALLED"
elif [ "$have_yarn" -eq 1 ]; then
  if (cd src/frontend && yarn check --integrity >/dev/null 2>&1); then
    echo "node_modules: in sync with yarn.lock"
  else
    FE_DEPS=stale
    echo "node_modules: OUT OF SYNC with package.json/yarn.lock"
  fi
elif [ "$(mtime src/frontend/yarn.lock)" -gt "$(mtime "$integrity")" ]; then
  FE_DEPS=stale
  echo "node_modules: older than yarn.lock, probably OUT OF SYNC"
else
  echo "node_modules: newer than yarn.lock"
fi

# -- images -------------------------------------------------------------------
# A dev image only goes stale when its dependency manifests or its Dockerfile
# change: the sources are bind-mounted. A file on disk newer than the image is
# a candidate; it is confirmed by comparing it with the copy baked in the image.
# A heuristic: a file whose mtime is not newer than the image is not compared.
#
# spec: name|image|make target|services|image:local pairs|build files
# build files: copied in the image but not readable back from it as they are
IMAGES=(
  "backend|drive:backend-development|build-backend|app-dev celery-dev|/app/uv.lock:src/backend/uv.lock /app/pyproject.toml:src/backend/pyproject.toml|Dockerfile docker/files/etc/mime.types docker/files/usr/local/bin/entrypoint"
  # no pair: the bind-mounted node_modules hide the dependencies of the image
  "frontend|drive:frontend-development|build-frontend|frontend-dev||src/frontend/Dockerfile"
)

echo
echo "== Images"
BUILD=()
RENEW=()
any_image=0
for spec in "${IMAGES[@]}"; do
  IFS='|' read -r name image target services pairs buildfiles <<<"$spec"
  created=$(docker image inspect -f '{{.Created}}' "$image" 2>/dev/null)
  [ -n "$created" ] && any_image=1
  if [ "$name" = "frontend" ] && [ "$FRONTEND_MODE" = "local" ]; then
    echo "$name: skipped (frontend runs locally)"
    continue
  fi
  if [ -z "$created" ]; then
    echo "$name ($image): MISSING -> make $target"
    BUILD+=("$name:$target")
    continue
  fi
  ctime=$(to_epoch "$created")
  reasons=()
  for pair in $pairs; do
    in=${pair%%:*}
    loc=${pair#*:}
    [ "$(mtime "$loc")" -gt "$ctime" ] || continue
    [ "$(img_cat "$image" "$in" | fhash)" = "$(fhash <"$loc")" ] || reasons+=("$loc changed")
  done
  # a build file is not in the image: diff it against the commit checked out
  # when the image was built (a branch switch touches files it does not
  # change), and trust the mtime alone only when the reflog does not go back.
  # An edit that was not committed when the image was built shows as a change.
  for bf in $buildfiles; do
    [ "$(mtime "$bf")" -gt "$ctime" ] || continue
    built_from=$(head_at "$ctime")
    if [ -z "$built_from" ]; then
      reasons+=("$bf touched since the build (no reflog to confirm)")
    elif ! git diff --quiet "$built_from" -- "$bf" 2>/dev/null; then
      reasons+=("$bf changed since the build")
    fi
  done
  if [ ${#reasons[@]} -gt 0 ]; then
    echo "$name ($image, built ${created%%.*}): STALE -> make $target"
    printf '    - %s\n' "${reasons[@]}"
    BUILD+=("$name:$target")
  else
    echo "$name ($image, built ${created%%.*}): up to date"
  fi
done

# -- containers vs images -----------------------------------------------------
# `docker compose up --force-recreate` (what `make run` does) keeps each
# container's anonymous volumes. The Python dependencies installed in the
# backend image live in one (/app/.venv): a volume older than the image hides
# what the image installed, so the container keeps running the old ones.
# Only the dates are compared: what the volume holds is not inspected.

echo
echo "== Dependency volumes of the backend containers"
created=$(docker image inspect -f '{{.Created}}' drive:backend-development 2>/dev/null)
if [ -n "$created" ]; then
  ctime=$(to_epoch "$created")
  for svc in app-dev celery-dev; do
    cid=$(docker compose ps -a -q "$svc" 2>/dev/null | head -1)
    [ -z "$cid" ] && { echo "$svc: no container yet"; continue; }
    stale=""
    for vol in $(docker inspect -f '{{range .Mounts}}{{if eq .Type "volume"}}{{.Name}}={{.Destination}} {{end}}{{end}}' "$cid"); do
      vcreated=$(docker volume inspect -f '{{.CreatedAt}}' "${vol%%=*}" 2>/dev/null)
      [ -n "$vcreated" ] && [ "$(to_epoch "$vcreated")" -lt "$ctime" ] && stale+=" ${vol#*=}"
    done
    if [ -n "$stale" ]; then
      echo "$svc: STALE dependency volume(s):$stale (older than the image)"
      RENEW+=("$svc")
    else
      echo "$svc: ok"
    fi
  done
else
  echo "no backend image yet"
fi

# -- services and databases ---------------------------------------------------

# what `make run-backend` leaves running: nginx and all it depends on
BACKEND_SERVICES="postgresql redis rustfs mailcatcher kc_postgresql keycloak collabora onlyoffice celery-dev app-dev nginx"

echo
echo "== Services"
for svc in $BACKEND_SERVICES frontend-dev; do
  printf '%-16s %s\n' "$svc" "$(state "$svc")"
done

echo
echo "== Database"
app_db=unknown
if [ "$(state postgresql)" = "running" ]; then
  # "<django_migrations tables>|<tables in the public schema>"
  n=$(echo "select (select count(*) from pg_tables where schemaname = 'public' and tablename = 'django_migrations') || '|' || (select count(*) from pg_tables where schemaname = 'public');" |
    docker compose exec -T postgresql sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tA' 2>/dev/null | tr -d '\r[:space:]')
  case "$n" in
    1\|*) app_db=migrated ;;
    0\|0) app_db=empty ;;
    0\|*) app_db=foreign ;;
  esac
fi
echo "backend database: $app_db"
[ "$app_db" = "foreign" ] &&
  note "the backend database holds tables but no django_migrations: do not run make migrate, ask the user"
pending_migrations=0
if [ "$app_db" = "migrated" ] && [ "$(state app-dev)" = "running" ]; then
  if docker compose exec -T app-dev python manage.py migrate --check >/dev/null 2>&1; then
    echo "backend migrations: all applied"
  else
    echo "backend migrations: PENDING (or the check failed) -> ${ENVP}make migrate"
    pending_migrations=1
  fi
fi

echo
echo "== Endpoints"
endpoints_ok=1
probe() {
  local c
  c=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$2" 2>/dev/null)
  printf '%-34s %s\n' "$1" "$c"
  [ "$c" = "200" ] || [ "$3" = "optional" ] || endpoints_ok=0
}
probe "backend  :8071/api/v1.0/config/" http://localhost:8071/api/v1.0/config/
probe "keycloak :8083 (via nginx)" http://localhost:8083/realms/drive/.well-known/openid-configuration
probe "frontend :3000" http://localhost:3000/ optional
# a frontend container that is up but does not answer (still compiling, or
# crashed), or answers an error
fe_bad=""
if [ "$FRONTEND_MODE" = "container" ] && [ "$fe_state" = "running" ]; then
  fe_code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://localhost:3000/ 2>/dev/null)
  case "$fe_code" in
    000) fe_bad="does not answer: it may still be compiling" ;;
    5*) fe_bad="answers http $fe_code" ;;
  esac
fi

# up = everything `make run-backend` starts is running, and the two probed
# endpoints answer
stack_up=$endpoints_ok
for svc in $BACKEND_SERVICES; do
  [ "$(state "$svc")" = "running" ] || stack_up=0
done

# -- plan ---------------------------------------------------------------------

echo
echo "== Suggested plan"
if [ "$any_image" -eq 0 ] && [ "$(state postgresql)" = "absent" ]; then
  echo "1. make bootstrap    # first run: nothing is built yet"
  [ "$FRONTEND_MODE" = "local" ] &&
    echo "   (:3000 is taken by the local frontend and bootstrap starts the frontend container, which would fail: stop the local \`yarn dev\` first and start it again after)"
else
  docker network inspect lasuite-network >/dev/null 2>&1 || plan "make create-docker-network"
  [ ${#missing_local[@]} -gt 0 ] && plan "make create-dev-local-files"
  [ ${#missing_data[@]} -gt 0 ] && plan "make ${missing_data[*]}"
  fe_built=0
  for b in "${BUILD[@]}"; do
    [ "${b%%:*}" = "frontend" ] && [ "$FRONTEND_MODE" != "container" ] && continue
    plan "make ${b#*:}"
    # `make build-frontend` also installs the dependencies
    [ "${b%%:*}" = "frontend" ] && fe_built=1
  done
  if [ "$FE_DEPS" != "ok" ] && [ "$fe_built" -eq 0 ]; then
    if [ "$FRONTEND_MODE" = "container" ]; then
      plan "$COMPOSE run --rm frontend-dev yarn install --frozen-lockfile"
      [ "$fe_state" = "running" ] && plan "$COMPOSE restart frontend-dev"
    else
      note "frontend dependencies to install: \`cd src/frontend && yarn install --frozen-lockfile\` before \`yarn dev\`"
    fi
  fi
  # already up: only what changed is recreated below, `make run-backend` would
  # restart every container for nothing
  if [ "$stack_up" -ne 1 ]; then
    if [ "$FRONTEND_MODE" = "container" ] && [ "$BACKEND_MODE" = "dev" ]; then
      plan "make run"
    else
      plan "$RUN_BACKEND"
      [ "$FRONTEND_MODE" = "container" ] && plan "$COMPOSE up -d --no-deps frontend-dev"
    fi
  elif [ "$FRONTEND_MODE" = "container" ] && { [ "$fe_state" != "running" ] || [ "$fe_built" -eq 1 ]; }; then
    # also after a rebuild: `up` recreates a container whose image changed
    plan "$COMPOSE up -d --no-deps frontend-dev"
  fi
  # services whose image gets rebuilt, and those already on stale volumes,
  # must be recreated with fresh anonymous volumes: `make run` keeps them.
  # --no-deps: --renew-anon-volumes would otherwise also renew the volumes of
  # a dependency recreated in the same run, Keycloak's database included
  for b in "${BUILD[@]}"; do
    [ "${b%%:*}" = "backend" ] && RENEW+=(app-dev celery-dev)
  done
  if [ ${#RENEW[@]} -gt 0 ]; then
    uniq_renew=$(printf '%s\n' "${RENEW[@]}" | sort -u | tr '\n' ' ')
    plan "$COMPOSE up -d --force-recreate --renew-anon-volumes --no-deps ${uniq_renew% }"
  fi
  { [ "$pending_migrations" -eq 1 ] || [ "$app_db" = "empty" ]; } && plan "${ENVP}make migrate"
  [ "$FRONTEND_MODE" = "undecided" ] &&
    plan "ASK the user: frontend locally (make run-frontend-development, in the background) or in docker (make build-frontend if the image is missing or stale, then $COMPOSE up -d --no-deps frontend-dev)"
  if [ -n "$fe_bad" ]; then
    note "the frontend-dev container is running but :3000 $fe_bad: read \`docker compose logs --tail 80 frontend-dev\`"
  fi
  if [ ${#PLAN[@]} -eq 0 ]; then
    if [ -n "$fe_bad" ]; then
      echo "Nothing to run: see the notes below."
    else
      echo "Nothing to do: the stack is up and current."
    fi
  else
    i=1
    for step in "${PLAN[@]}"; do
      echo "$i. $step"
      i=$((i + 1))
    done
  fi
fi

if [ ${#NOTES[@]} -gt 0 ]; then
  echo
  echo "== Notes"
  printf -- '- %s\n' "${NOTES[@]}"
fi
