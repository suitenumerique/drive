# Status: Source notes (do not edit; see _bmad-output/planning-artifacts/ for the current plan)

# Self-host “La Suite Numérique” — état des lieux & notes d’architecture (focus Drive)

Date: 2026-02-02  
But: documenter un **état des lieux précis** (sans faire de dev) pour préparer un déploiement **Docker (dev)** puis **Docker ou Kubernetes (prod)**, en commençant par **Drive** et en gardant une trajectoire “suite complète” (People/Find/Docs/Messages/Meet/…).

Conventions de lecture:
- **État actuel (upstream)**: ce qui est visible dans le repo Drive tel quel (code + docs + compose/helm).
- **Décision v1 (selfhost)**: choix verrouillés pour la v1 (même si upstream fait autrement).
- **À valider**: points qui nécessitent un test E2E / une mesure / un PoC (ex: compat exact S3, flow proxy).

---

## 0) Résumé exécutif (ce qui est déjà acté)

- Priorité: **Drive** d’abord, mais on pense “suite complète” dès le design.
- Déploiements cibles:
  - **Dev**: Docker (mono-machine) avec **Nginx** en reverse-proxy edge.
  - **Prod**: doit pouvoir tourner en **Docker** (mono-machine / multi-VM) **ou** en **Kubernetes** (multi-nœuds, scaling).
- Reverse-proxy edge: l’utilisateur final doit pouvoir choisir **Nginx ou Traefik** (pas de dépendance à un proxy “interne” spécifique si on peut l’éviter).
- Identité: compat **OIDC générique** (IdP au choix). En dev, **Keycloak** est l’IdP le plus “référence” car déjà utilisé upstream.
- Stockage: Drive est **S3-first** (object storage obligatoire). Décision v1: **SeaweedFS (S3 gateway)** au lieu de MinIO pour Docker; en Kubernetes: **Ceph RGW** (via Rook).
- Volumétrie: plusieurs **To minimum**, fichiers petits et gros (usage “cloud drive”).
- Besoin v1: en plus du S3 “principal”, exposer un **2ᵉ montage SMB** dans l’UI (non synchronisé, sans historique de versions).
- WOPI: compat **Collabora Online** souhaitée dès v1 (à valider E2E).
- Langages/frameworks: **Python/Django** (backend) + **TypeScript/Next.js** (frontend) verrouillés (pas de réécriture “core”).

---

## 1) Objectif & périmètre

### 1.1 Objectif final

Self-host d’une “suite” cohérente inspirée de l’org GitHub `suitenumerique`:
- `drive` (priorité)
- puis selon besoins: `docs`, `people`, `find`, `messages`, `meet`, `conversations`, `integration`, `ui-kit`, `django-lasuite`, `calc`, etc.

### 1.2 Hors-périmètre immédiat

- Pas de dev maintenant: uniquement **review**, décisions d’architecture et préparation du terrain.

---

## 2) Repos & briques (vue d’ensemble)

Repos `suitenumerique` jugés centraux/actifs:
- `drive`: plateforme fichiers (Django + Next.js).
- `docs`: édition collaborative (Django + frontend + y-provider).
- `people`: annuaire / organisations / équipes (Django + frontend).
- `find`: recherche cross-app (Django + OpenSearch).
- `messages`: messagerie/inbox (stack lourde: DB/Redis/OpenSearch/S3/workers…).
- `meet`: visio (dépend LiveKit + services associés).
- `conversations`: chatbot/IA.
- `integration`: widgets + API (gaufre / UI transverses).
- `ui-kit`: design system / composants UI.
- `django-lasuite`: briques Django communes (OIDC login, resource server, etc.).

Constat: la plupart des repos ont un **compose “dev”**, mais le “prod” upstream est souvent documenté côté **Kubernetes** (au moins pour Drive).

---

## 3) Drive — état technique (architecture & implications)

### 3.0 Langages & frameworks (verrouillés)

Objectif: éviter toute dérive “réécriture” qui compliquerait l’intégration suite + la maintenance. Les choix suivants sont **verrouillés** pour Drive (v1 et au-delà), sauf décision explicite contraire:

- **Backend**: **Python 3.13** + **Django 5** (API via **Django REST Framework**).
  - Async/queue: **Celery** (+ Redis broker/backend).
  - S3 client: **boto3** (via `django-storages[s3]`).
- **Frontend Drive**: **TypeScript (5.x)** + **React (19)** via **Next.js (15)**.
  - Styles: **SCSS/Sass**.
- Runtime/outillage JS: **Node.js (>=22 <25)** + **Yarn classic (1.22.x)**.
- **Build d’emails** (outillage repo): **Node.js** + **MJML** (génération templates HTML/TXT).
- **Déploiement/ops**: **Docker/Compose**, **Helm (Kubernetes)**, config **Nginx**, scripts **shell**.

Règle: on évite d’introduire un 2ᵉ langage/framework “core” (ex: réécriture backend en Go/Java, frontend en Vue/Svelte, etc.). Les exceptions possibles (outillage, scripts) doivent rester périphériques et justifiées.

### 3.1 Maturité / packaging

- `drive` est versionné (tags `v0.1.0` → `v0.11.1`) et a une CI (lint/tests/build images/helm).
- Le dépôt fournit `compose.yaml` et un `Makefile` (ciblés dev).
- Upstream indique que **Kubernetes est utilisé en prod** (donc la voie la plus “supportée”).

### 3.2 Modèle de stockage (le point clé)

Drive est un “drive web” **API + object storage**, pas un NAS:
- Métadonnées/arbre/ACL: **PostgreSQL**
- Tâches async: **Celery + Redis**
- Contenu fichiers: **S3-compatible** (MinIO upstream; SeaweedFS choisi en dev) via `django-storages[s3]` + `boto3`

Flux important:
- Download/preview: URLs `/media/<key>` et `/media/preview/<key>` passent par un proxy qui:
  - fait une sous-requête d’auth (`/api/v1.0/items/media-auth/`)
  - récupère des **headers signés** (AWS SigV4)
  - proxifie ensuite vers l’object storage avec ces headers
- Upload: presigned PUT vers l’object storage, puis callback “upload ended”

### 3.3 “Stockage en clair”, SMB/WebDAV, montage disque

- Drive **n’est pas conçu** pour écrire une arborescence POSIX “lisible” par l’utilisateur final.
- Même si un S3 server écrit “sur disque”, la structure **n’est pas** une arbo utilisateur.
- Drive ne fournit pas (à ce stade) un accès type **SMB/WebDAV** pour monter le drive comme un disque.
- Chiffrement au repos: option `ds-proxy` (proxy S3 chiffrant/déchiffrant): dans ce cas le stockage contient des blobs chiffrés.

### 3.4 WOPI / Collabora Online (cible v1)

- Drive embarque une implémentation **WOPI** (endpoints backend + config via variables `WOPI_*`).
- L’intégration se configure via `WOPI_CLIENTS` + `WOPI_<CLIENT>_DISCOVERY_URL` (discovery XML).
- Point d’attention: l’implémentation utilise `VersionId` côté S3 → **bucket versioning requis** si WOPI est activé.
- À valider E2E: Collabora Online, discovery URL, reverse-proxy, `WOPI_SRC_BASE_URL`, permissions/locks, et comportement sur gros fichiers.

---

## 4) Identité & IAM — OIDC (IdP au choix), Keycloak (dev), People (v2)

### 4.1 Pourquoi Keycloak apparaît dans les repos

- Keycloak est surtout un **IdP de dev/démo** dans les `docker-compose` des repos.
- Drive n’a pas Keycloak “codé en dur”: il dépend d’un OP via variables `OIDC_OP_*`.

### 4.2 Contrat OIDC attendu (compat n’importe quel IdP)

Drive est compatible avec un IdP OIDC standard tant que tu fournis les endpoints/claims attendus, typiquement:
- `OIDC_OP_AUTHORIZATION_ENDPOINT`, `OIDC_OP_TOKEN_ENDPOINT`, `OIDC_OP_USER_ENDPOINT`, `OIDC_OP_JWKS_ENDPOINT`
- `OIDC_RP_CLIENT_ID`, `OIDC_RP_CLIENT_SECRET`
- optionnels: `OIDC_OP_LOGOUT_ENDPOINT`, `OIDC_RP_SCOPES`, `OIDC_AUTH_REQUEST_EXTRA_PARAMS`

Décision v1 (selfhost):
- **Dev**: garder **Keycloak** comme IdP “référence” (c’est ce qui apparaît le plus souvent upstream) pour simplifier les tests/bootstraps.
- **Prod**: laisser **le choix libre** (tout IdP OIDC qui respecte le contrat OIDC + claims requis).
  - Important: Drive ne doit pas contenir de logique “IdP-specific” (Keycloak-only, etc.). Tout doit rester configuré via variables OIDC.

### 4.3 People: rôle réel vs “People = IdP”

- **People n’est pas requis** pour que Drive fonctionne (Drive consomme un IdP OIDC directement).
- People sert surtout pour une suite: **annuaire / organisations / équipes** (et potentiellement distribution de droits).
- People peut aussi être configuré comme **Identity Provider OIDC pour une fédération** (cf. doc People “People as an Identity Provider”): dans ce schéma, les applications parlent à un “hub” (souvent Keycloak en dev), et People est un IdP amont (auth email/password de `Mailbox`).
  - Donc: People peut “faire de l’OIDC”, mais son rôle typique dans la suite est plutôt **source d’identité / annuaire** et **IdP amont**, pas forcément “IdP unique” consommé directement par toutes les apps.

### 4.4 Point d’attention: “teams” cross-suite

Drive a un concept `team`, mais dans l’état actuel:
- `User.teams` retourne `[]` (stub)
- donc le RBAC “par équipes People → Drive” n’est pas plug & play à ce stade

Conclusion: prévoir People est logique pour la suite, mais l’intégration “teams” restera à cadrer/valider plus tard.

---

## 5) Reverse-proxy edge — contraintes Drive (et Docs)

### 5.1 Le besoin non négociable: `/media` (auth subrequest + headers signés)

Le pattern `/media` implique une fonctionnalité équivalente à `auth_request` + “propagation de headers de la réponse d’auth” vers l’object storage.
- C’est nativement simple avec **Nginx**.
- Pour **Traefik**, c’est faisable en théorie (ForwardAuth + propagation de headers), mais il faudra valider le “fit” exact avec le flow SigV4.
  - Concrètement, il faut pouvoir injecter (au minimum) `Authorization`, `X-Amz-Date`, `X-Amz-Content-SHA256` dans la requête vers S3 à partir de la réponse d’auth.

Note: ce pattern n’est **pas forcément unique à Drive** (Docs a un besoin similaire pour ses médias).

### 5.2 Décision d’architecture proxy

- On vise un **reverse-proxy edge unique** (pas un Nginx par app).
- V1/dev: edge **Nginx** (référence de base, “simple et compatible”).
- Objectif: supporter **Traefik** en edge (à valider sur le pattern `/media`).
- On évite un proxy interne dédié; plan B uniquement si Traefik ne peut pas couvrir proprement `/media`: un “media-gateway” Nginx optionnel.

---

## 6) Stockage — exigences, choix v1, et option “FS/SMB”

### 6.1 Exigences de stockage (cibles)

- Capacité: **plusieurs To minimum**
- Mix: beaucoup de petits fichiers + quelques gros fichiers
- Objectif fonctionnel: “cloud drive” via web (type Google Drive/OneDrive)
- Option demandée: pouvoir **présenter** des stockages locaux/SMB (type Filestash)
  - Besoin non prioritaire mais à anticiper: **sync desktop/mobile** (ou montage réseau) à long terme

### 6.2 Contrainte Drive: S3 obligatoire (aujourd’hui)

Dans l’état actuel, Drive est conçu autour d’un stockage **S3-compatible**:
- remplacer S3 par un storage “filesystem direct” n’est pas un simple paramétrage (cela demanderait du dev)
- si WOPI/OnlyOffice/Collabora est utilisé, la présence de `VersionId` rend le support du **bucket versioning** important côté S3

### 6.3 Choix v1: SeaweedFS (verrouillé) — et pourquoi pas MinIO

Décision: **ne pas partir sur MinIO** si possible (malgré son côté pratique en dev), et basculer directement sur **SeaweedFS (S3 gateway)** pour Docker.

À valider pour sécuriser le choix:
- valider compat S3 sur les opérations critiques (presigned PUT, GET/Range, HEAD, CopyObject, multipart, versioning…)
- valider le comportement `VersionId` requis par WOPI/Collabora

### 6.4 Alternatives S3 open-source à évaluer (ordre indicatif)

- **SeaweedFS (S3 gateway)**: choisi pour Docker (plus léger) — à valider: compat exacte, versioning, perfs.
- **Ceph RGW**: candidat pour Kubernetes/multi-nœuds (robuste), mais plus “lourd” à opérer.
- **Zenko CloudServer**: S3 server complet (stack plus lourde).
- **Versity S3 Gateway (`versitygw`)**: gateway S3 (à valider selon besoins Drive).
- **RustFS**: prometteur mais à valider (maturité/compat).
- (Non-candidats si versioning requis): solutions sans bucket versioning (ex: Garage, Apache Ozone S3 gateway).

### 6.5 Option “filesystem local / SMB” (type Filestash): clarifier le périmètre

Il y a 2 façons très différentes d’interpréter ton besoin:

1) **Sans dev Drive** (le plus simple): utiliser un S3 server dont le “backend” est un volume local, éventuellement monté SMB (le S3 reste l’API officielle).
   - Avantage: compatible avec Drive aujourd’hui.
   - Risques: performances/locking si SMB, sémantique POSIX vs objet, sauvegardes.

2) **Avec dev Drive** (le plus ambitieux): ajouter une notion de “mounts” (S3 + filesystem + SMB + …) visibles dans l’UI (vraiment “comme Filestash”).
   - Impacts: modèle de droits, versioning, preview/indexation, quotas, audit, partages, etc.
   - Il faudra probablement désactiver ou adapter certaines fonctionnalités selon le type de storage.

Décision:
- v1: rester **S3-first** (Drive fonctionne “as-is” pour le storage principal) **et** ajouter un **mount SMB** séparé (non synchronisé, sans historique de versions).
- v2+: généraliser vers des “drives virtuels / mounts” multi-providers type Filestash (S3/SMB/FS/SFTP/WebDAV…) + matrice de capacités.

### 6.6 “Virtual drives” (Filestash-like) — objectif v2+ (gros chantier)

Objectif: un “disque virtuel” unique dans l’UI, derrière lequel on peut brancher plusieurs stockages (S3, FS local, SMB, SFTP, WebDAV, …) à la manière de Filestash.

État actuel:
- Drive est construit autour d’un **storage backend unique** (S3) et n’a pas aujourd’hui la notion de “mounts” multi-providers.
- Implémenter des “virtual drives” dans Drive = **refactor structurel** (modèle de données + API + services).

Approches possibles:
1) **Approche pragmatique (sans refactor Drive)**: garder Drive S3-only, et déployer Filestash (ou équivalent) à côté, avec SSO, et une intégration “soft” (liens, app-menu, etc.).
2) **Approche native (dans Drive)**: introduire une abstraction “StorageProvider” et des “Mounts/VirtualDrives”.

Pour “prévoir sans redesign” (même si v2+):
- Centraliser tous les accès au stockage derrière un service (ex: `StorageService`) au lieu d’appeler S3 partout.
- Modéliser un futur `StorageProvider` (type + config + “capabilities”) et un `Mount` (owner/team + chemin racine).
- Prévoir une matrice de capacités (ex: versioning, share-links, preview, search-indexing, locks WOPI…) et désactiver ce qui n’est pas supporté selon le provider.

Versioning (point dur):
- S3: versioning natif (via `VersionId`) → compatible WOPI.
- FS/SMB: pas de versioning standard. Options:
  - **émuler** (copie des versions dans un store S3 “canonical”) → coûteux en espace mais simple conceptuellement,
  - **snapshots** (ZFS/Btrfs) → dépend du FS, pas portable,
  - ou **désactiver** l’historique de versions sur ces mounts.

WOPI (point à clarifier):
- WOPI n’exige pas un “historique de versions” côté storage; il faut surtout exposer un identifiant de version (ou un timestamp) qui change quand le fichier change.
- Donc un mount SMB peut rester “sans historique de versions” tout en restant compatible WOPI, si Drive calcule une version applicative (ex: `mtime+size` ou compteur “revision”) et implémente les opérations WOPI nécessaires (read/write/locks).

### 6.7 Migration de backend S3 (SeaweedFS → Ceph RGW)

Oui, c’est possible car Drive parle “S3”, mais la difficulté dépend de ce que tu veux préserver:
- **Sans préserver l’historique des versions**: migration “classique” (copie des objets) + bascule endpoint.
- **Avec versioning (requis pour WOPI)**: il faut copier **toutes les versions** (et idéalement métadonnées), ce qui demande des outils/flows spécifiques et plus de temps.

Recommandation: si tu penses passer à Ceph RGW en k8s, fais-le soit:
- très tôt (avant volumétrie importante), soit
- avec une fenêtre de maintenance + procédure de migration testée.

### 6.8 SMB mount v1 (non synchronisé) — cohérence “live” (approche recommandée)

Objectif v1 (confirmé): un 2ᵉ montage SMB visible dans l’UI, sans sync avec S3 et sans “version history”.

Approche de cohérence (inspirée des file managers “storage agnostic” type Filestash):
- Le SMB est la **source de vérité**: un refresh UI doit relister le répertoire **depuis SMB** (pas depuis une copie en DB).
- Le backend ne garde au plus qu’un cache “best-effort” (TTL court) pour des raisons de perf, mais doit toujours pouvoir revalider (ETag/mtime/size) et récupérer l’état actuel.
- Les droits restent ceux de Drive: le backend accède au SMB via un **compte de service**, et Drive filtre/autorise au niveau applicatif.
- Modèle de droits v1 (simplifié): **permissions au niveau du mount** (pas de RBAC par dossier/fichier dans le mount). Les actions (upload/download/rename/delete/share/WOPI) sont autorisées ou non selon le rôle sur le mount.

Configuration du mount SMB (attendu):
- `host`: IP ou FQDN du serveur SMB
- `path`: chemin racine exposé dans Drive (sous-chemin dans le share)
- `username` / `password`: compte de service SMB utilisé par Drive
- Optionnels: `port` (défaut 445), `domain`, `share` (nom du share)

#### Hypothèses acceptées (SMB mount v1)

- Les utilisateurs peuvent accéder au partage SMB directement (depuis leur PC). Les ACL Drive ne protègent donc que l’accès via Drive (UI/API) et peuvent être contournées via un accès SMB direct.
- Si un fichier est renommé/supprimé hors Drive, les liens/partages Drive basés sur l’ancien chemin peuvent casser (comportement accepté).

Uploads/écriture (gros fichiers):
- Pour SMB, l’upload “direct S3 presigned” ne s’applique pas: il faut un upload via backend, idéalement **resumable (type TUS)**, puis écriture streamée sur SMB.
- Uploads “chunked/résumables”: pouvoir **activer** un mode chunked et **définir la taille des chunks** (objectif: applicable à S3 et SMB, même si les mécanismes diffèrent: multipart S3 vs upload resumable backend pour SMB).

WOPI/Collabora sur SMB sans versioning:
- Pas d’historique requis, mais il faut exposer une “version” qui change quand le fichier change (ex: `mtime+size` ou une révision applicative).

### 6.9 SMB mount v1 — points à verrouiller (avant dev)

- **Rôles au niveau du mount**: définir le set (ex: viewer/editor/manager) et la matrice d’actions autorisées (CRUD, partage, WOPI).
- **Gestion des nouveautés SMB**: comportement attendu si un fichier apparaît hors Drive (visibilité immédiate au refresh).
- **Téléversement gros fichiers**: protocole résumable (type TUS ou chunk upload), timeouts, reprise, et écriture **atomique** sur SMB (temp + rename).
- **Chunk size**: définir une config explicite (ex: `UPLOAD_CHUNK_SIZE_BYTES`) et les limites (min/max), et clarifier l’effet:
  - S3: impacte multipart (threshold/chunk size) côté backend et/ou stratégie côté client
  - SMB: impacte la granularité des chunks côté upload resumable backend
- **Lecture streaming / Range**: nécessaire pour preview, médias, et perf; décider du fallback si le backend SMB ne permet pas un seek efficace.
- **WOPI locks**: stratégie de verrouillage (WOPI Lock/Unlock/RefreshLock) côté Drive pour éviter les conflits d’édition.
- **Fonctionnalités Drive à capacité réduite**: préciser ce qui est désactivé ou “best effort” sur SMB (version history, indexation/recherche, antivirus, préviews/thumbnails, quotas).
- **Partage (liens/invitations)**: préciser si le partage donne accès uniquement à un chemin (token) ou requiert l’appartenance au mount (dans tous les cas, pas de RBAC interne).

### 6.10 SMB mount v1 — scope fonctionnel exact (cible)

Objectif: le mount SMB doit être utilisable “comme un drive” dans l’UI Drive, avec un maximum de fonctionnalités, tout en acceptant les limites connues (pas de version history SMB, contournement possible via accès SMB direct, chemins qui peuvent casser si renommés hors Drive).

Fonctionnel en v1 (attendu):
- **Navigation & listing**: workspace/mount visibles, navigation dossiers, tri, refresh “live” (état SMB actuel).
- **CRUD fichiers/dossiers**: créer dossier, renommer, déplacer, supprimer, téléverser, télécharger.
- **Gros fichiers**: upload & download stables (streaming), avec reprise si possible (résumable recommandé).
  - Option: mode upload chunked activable + taille de chunk configurable.
- **Prévisualisation**: ouverture/preview des formats supportés par Drive (au minimum via download/stream).
- **Partage**: liens de partage, invitations/partages par rôle, avec enforcement côté Drive (UI/API).
- **Permissions Drive**: droits **globaux au mount** appliqués côté Drive sur toutes les opérations (même si contournables via SMB direct).
- **WOPI/Collabora**: édition en ligne via WOPI (read/write) sur le contenu SMB, avec gestion des locks et une “version” calculée (ex: `mtime+size`).

Fonctionnel en v1 mais potentiellement “best effort” (à cadrer):
- **Recherche**: recherche dans le mount SMB (au moins par nom). Indexation full-text peut être différée.
- **Thumbnails/preview avancées**: dépend des pipelines existants (génération) et de la capacité à lire/seek efficacement sur SMB.
- **Antivirus / DLP / analyse**: peut être plus complexe car l’upload passe par le backend et les chemins SMB ne sont pas versionnés.

Non objectif v1 (explicitement):
- **Historique de versions** sur SMB (pas de versioning/rollback multi-versions).
- **Garantie de stabilité des liens** si renommage/déplacement effectué hors Drive (accepté).

### 6.11 Prévoir Sync Desktop/Mobile (v2+) — précautions anti-rework

Objectif: pouvoir ajouter plus tard un agent desktop (type Google Drive) et une app mobile sans refondre le backend.

Invariants à prévoir dès maintenant:
- **Identité stable**: un identifiant immutable par item (fichier/dossier) distinct du `path` (le `path` change lors des rename/move).
- **Change feed**: un journal/delta API “changes since cursor” (append-only) pour éviter les rescans complets.
- **Conflits**: un `etag`/`revision` serveur + règles de résolution (ex: “conflict copy”) quand deux écritures concurrentes arrivent.
- **Uploads robustes**: uploads résumables + idempotence (session upload + commit atomique) pour réseaux instables (mobile).
- **Locks**: sémantique claire de verrouillage (au minimum cohérente avec WOPI) et comportement en cas d’écriture pendant un lock.
- **Capabilities par mount**: exposer une matrice de capacités (resume, atomic rename, range reads, copy server-side…) pour que les clients adaptent leur stratégie selon S3 vs SMB.

Note SMB:
- Un mount SMB accessible directement (hors Drive) complique le sync (changements externes non journalisés). Si on vise un sync “solide”, il faudra accepter une stratégie “best effort” (scan périodique) ou restreindre l’accès SMB direct.

### 6.12 Préparation interop People v2 (sans activer) — checklist

Objectif: pouvoir intégrer People (org/teams/service providers) en v2 sans rework massif de Drive, tout en gardant en v1 le comportement actuel (notamment `User.teams == []`).

Checklist v1 (à respecter):
- **OIDC générique**: ne pas introduire de dépendance “Keycloak-only” (tout doit rester basé sur config OIDC via variables).
- **Identité**: conserver `sub` comme identifiant stable (avec fallback email déjà existant selon config), et éviter les règles dépendantes d’un claim optionnel.
- **Teams (v2)**: garder le comportement actuel: `User.teams` retourne `[]` (stub). Ne pas supprimer les champs/structures liés aux teams dans Drive; prévoir seulement un point d’extension pour brancher People plus tard.
- **Multi-storage**: éviter de disperser du code “S3-only” dans le backend; centraliser l’accès storage derrière une couche unique (ex: `StorageService`) et router les opérations par `mount_id` (au minimum distinguer `s3-main` vs `smb-1`).
- **Claims stockables**: garder la possibilité de stocker des claims via `OIDC_STORE_CLAIMS` même si Drive n’en a pas l’usage immédiat (utile pour v2 People/interop).
- **Partage/WOPI**: garder le partage “Drive-side” et une stratégie de version WOPI distincte selon backend (S3 `VersionId` vs SMB “version string”).

---

## 7) Déploiements cibles — Docker (dev/prod) et Kubernetes (prod)

### 7.1 Docker (dev) — mono-machine

- Drive sur une machine unique (le plus simple pour itérer).
- Edge reverse-proxy: Nginx.
- Domaine dev: `drive.dev.lan` (via DNS LAN ou `/etc/hosts`).
- TLS dev: fournir un `make certs` (mkcert) qui génère et place les certs dans un chemin stable (gitignored), automatiquement monté/utilisé par Nginx.
- Stockage: S3 local via **SeaweedFS** (S3 gateway) sur disque local.

### 7.2 Docker (prod) — mono-machine et/ou multi-VM

Objectif: pouvoir isoler les composants sur plusieurs VMs:
- VM “edge”: reverse-proxy + TLS
- VMs “apps”: Drive/Docs/People/Find/…
- Object storage: local à une VM dédiée ou externe (selon infra)

À prendre en charge en “Docker prod” (hors support upstream):
- TLS, headers, cookies `Secure/SameSite`, politiques CORS si besoin
- sauvegardes/restores: PostgreSQL + object storage (Redis souvent jetable)
- upgrades/migrations: stratégie de rollout, fenêtre, compat montées de version
- observabilité: logs, métriques, traces (au minimum logs + healthchecks)

### 7.3 Kubernetes (prod) — multi-nœuds, scaling

- K8s est la voie “amont” la plus documentée pour Drive.
- Reverse-proxy/Ingress: on privilégie **Traefik** (Ingress ou Gateway API).
- Stockage S3: choix actuel en k8s: **Ceph RGW** (via Rook).

### 7.4 “Double-cible” Docker + K8s sans diverger (principe)

Principe: même contrat de configuration et mêmes dépendances, seuls changent les manifests.

Checklist:
- **Contrat d’env unique**: mêmes clés en `.env` (Docker) et `Secret/ConfigMap` (K8s).
- **Dépendances identiques**: PostgreSQL / Redis / S3 / workers / OpenSearch (si Find).
- **Point spécial `/media`**: design edge compatible Nginx et Traefik (et plan B media-gateway si besoin).
- **Init/migrations**: jobs reproductibles (buckets/DB migrations) dans les deux mondes.
- **Build/images**: mêmes images backend/frontend, tags versionnés, mode dev séparé.

---

### 7.5 Un seul backend S3 pour Docker + K8s ?

Possible, mais pas obligatoire.
- Côté apps: oui (mêmes images + même contrat S3/OIDC), seul “l’emballage” change.
- Côté object storage: options réalistes:
  - **SeaweedFS partout** (Docker + K8s): homogène et léger, mais à valider sérieusement pour prod.
  - **Ceph RGW partout**: homogène et robuste, mais lourd pour dev/mono-machine.

Décision actuelle: **SeaweedFS en Docker**, **Ceph RGW en Kubernetes** (même API S3, donc pas de redesign applicatif).

## 8) Intégration “suite complète” — trajectoire recommandée

Décision de principe: préparer l’intégration dès le départ, mais livrer étape par étape.

Proposition de séquencement (à ajuster):
1) **Drive seul** (auth, stockage, reverse-proxy, sauvegardes, upgrades)
2) **Find + OpenSearch** (recherche) dès le départ si l’impact infra est acceptable
3) **Docs + People** (dès que Drive est stable), puis harmonisation SSO/UX
4) `messages`, `meet`, `conversations`, `integration` selon besoins

### 8.1 Notes d’intégration (points techniques utiles)

- `find`: apporte recherche cross-app; nécessite **OpenSearch**; Drive s’interface via variables `SEARCH_INDEXER_*` (indexation async).
- `docs`: ajoute un temps réel (y-provider) + S3; et a aussi un pattern proxy/auth pour ses médias (à traiter comme Drive côté edge).
- `integration` / `ui-kit`: certains tokens/configs pointent vers des endpoints publics; en selfhost il faut décider: désactiver, repointer vers `integration`, ou remplacer.
- `messages`: stack plus lourde (workers, indexation, ingestion), à repousser tant que la base SSO/stockage/proxy n’est pas solide.
- `meet`: dépend LiveKit + réseau (TURN/STUN selon contexte), à traiter comme un chantier à part.

Point “gaufre/UI” (à décider):
- soit on désactive les endpoints officiels,
- soit on déploie `integration` et on repointe la config/thème,
- soit on remplace par une implémentation interne.

---

## 9) Gouvernance du projet (fork, upstream, qualité)

### 9.1 Fork vs clone

Objectif:
- pouvoir proposer des PR upstream si pertinent
- garder une trajectoire selfhost stable (même si upstream change)

À décider: fork (recommandé si contribution upstream) vs clone (plus simple mais moins structurant).
Licensing cible: **MIT** (à confirmer compatibilité et stratégie de “vendoring”).

### 9.2 Respecter `CONTRIBUTING.md`

Objectif: respecter les guidelines des repos officiels pour faciliter les PR.
À faire plus tard: lister les exigences (lint, format, CI, conventions, tests, etc.) pour chaque repo.

### 9.3 Suivi des issues/PR upstream

Objectif: récupérer et suivre les issues/PR ouvertes upstream pour:
- identifier bugs connus
- identifier features en cours
- éviter de diverger inutilement

### 9.4 Exigences qualité & documentation

- Prioriser une qualité de code élevée (structures, naming, routes API, tests).
- Documenter au fur et à mesure (architecture, décisions, runbooks, opérations).
- Structurer la gestion GitHub (issues/PR, roadmap, synchronisation upstream).
- Convention: tout le **code** et tous les **commentaires dans le code** doivent être en **anglais** (aucun commentaire en français).

---

## 10) Décisions verrouillées (réponses)

1) URLs/DNS (dev): `drive.dev.lan`. Idéalement via un fichier d’override compose (ex: `compose.dev.yaml`) et/ou une conf Nginx dédiée.
2) TLS (dev): fournir un `make certs` (mkcert) qui génère des certificats dans un dossier **gitignored**, et les fait utiliser automatiquement par Nginx (pas de “copier/coller” manuel).
3) Reverse-proxy v1: partir sur **Nginx edge** (simple). Support Traefik: objectif, mais à valider; on évite un proxy interne supplémentaire.
4) Stockage v1: **remplacer MinIO par SeaweedFS** (S3 gateway) dès le début.
5) “Filestash-like” (FS/SMB): v1 **S3-first + mount SMB** (non synchronisé, sans historique de versions). v2+: généraliser vers des “drives virtuels/mounts” multi-providers et une matrice de capacités.
6) WOPI/Collabora: souhaité **dès v1**, mais à vérifier E2E avec une instance Collabora Online. Conséquence: **bucket versioning requis**.
7) SMTP: **différé** (à prévoir sans redesign, mais pas dans v1).
8) SMB mount (v1): ajouter un 2ᵉ “montage” visible dans l’UI, **sans synchronisation** avec S3 et **sans historique de versions**. Accès via un compte de service SMB; **permissions globales au niveau du mount** (pas de RBAC interne par dossier/fichier).
9) People/teams (v2): conserver en v1 le comportement actuel: `User.teams` retourne `[]` (stub). L’interconnexion People → Drive (teams/service providers) est reportée à v2; ne pas casser les structures existantes côté Drive.
10) Langages/frameworks (Drive): conserver **Python/Django** côté backend et **TypeScript/Next.js** côté frontend (pas de réécriture “core”).

---

## 11) Sources (où regarder dans ce repo)

- Drive:
  - Compose dev: `compose.yaml`
  - Variables OIDC: `env.d/development/common`
  - Settings OIDC: `src/backend/drive/settings.py`
  - Backend auth OIDC: `src/backend/core/authentication/backends.py`
  - Media auth/proxy pattern: `docker/files/development/etc/nginx/conf.d/default.conf` + endpoint `/api/v1.0/items/media-auth/`
  - ds-proxy: `docs/ds_proxy.md`
  - Install prod upstream: `docs/installation/kubernetes.md` + `docs/installation/README.md`
- People (référence upstream, pas dans ce repo):
  - “People as an Identity Provider”: `docs/identityProvider.md`
