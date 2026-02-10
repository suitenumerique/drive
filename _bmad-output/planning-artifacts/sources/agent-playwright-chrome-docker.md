# Status: Source notes (do not edit; see _bmad-output/planning-artifacts/ for the current plan)

# Setup (Drive) : agent sur le host + Chrome uniquement + Playwright Test + Playwright MCP

**Contexte Drive** : dans ce repo, le frontend **Drive** est un **Next.js** (`frontend-dev` sur `:3000`) et l’auth passe par **Keycloak** (reverse-proxy via `nginx` sur `:8083`).  
L’objectif est que **l’agent** (et les tests) tournent **sur le host**, tout en testant une stack qui tourne dans **Docker Compose**.

---

## 0) Objectif

- L’agent **exécute automatiquement** tes tests frontend (E2E, et éventuellement component tests).
- L’agent dispose d’un navigateur “outil” via **Playwright MCP** pour :
  - explorer un parcours
  - reproduire un bug
  - diagnostiquer (DOM/états/interaction)
  - puis **écrire/mettre à jour** les tests Playwright Test et les relancer

👉 **Chrome uniquement** : les tests et le navigateur MCP doivent utiliser **Google Chrome** (pas Firefox/WebKit).

---

## 1) Ce qui tourne où (pour éviter les confusions)

- **Docker** :
  - `frontend-dev` : Next.js Drive (port publié `3000:3000`)
  - `app-dev` : backend Django API (port publié `8071:8000`)
  - `nginx` : reverse-proxy dev pour Keycloak + `/media` (port publié `8083:8083`)
  - `keycloak` : OIDC realm importé (exposé via `nginx:8083`)
  - `seaweedfs-s3` : S3 gateway (port publié `9000:8333`)
- **Host** :
  - Playwright Test (runner E2E)
  - Playwright MCP (navigateur “outil”) -> installé
  - Google Chrome installé localement (channel Playwright = `chrome`)

---

## 2) Prérequis (sur le host)

- Node.js (LTS recommandé)
- Google **Chrome** installé sur le host
- Yarn (car le repo frontend est en Yarn workspaces)

Installation Playwright (recommandée dans le workspace Drive) :

```bash
cd src/frontend/apps/drive
yarn add -D @playwright/test
```

> Note : Playwright peut cibler des navigateurs “branded” comme **Google Chrome** via `channel: "chrome"`.  
> Doc : https://playwright.dev/docs/browsers

---

## 3) Docker : URLs utiles depuis le host (Drive)

Les ports sont déjà publiés dans `compose.yaml` :
- UI Drive : `http://127.0.0.1:3000`
- Keycloak (via Nginx) : `http://127.0.0.1:8083`
- API backend : `http://127.0.0.1:8071`
- Media (proxy S3 signé) : `http://127.0.0.1:8083/media/...`

Démarrage stack :

```bash
docker compose up -d
```

Vérifs rapides :

```bash
curl -fsSI http://127.0.0.1:3000 >/dev/null
curl -fsSI http://127.0.0.1:8083/realms/drive/.well-known/openid-configuration >/dev/null
curl -fsSI http://127.0.0.1:8071/api/v1.0/ >/dev/null || true
```

### 3.1 Important : écoute réseau dans le conteneur

Si le host n’arrive pas à joindre le serveur Next.js (rare, mais possible selon versions/config), forcer l’écoute sur `0.0.0.0` :
- soit en ajustant la commande `next dev` (ex: `next dev -H 0.0.0.0 -p 3000`)
- soit via variable `HOSTNAME=0.0.0.0`

---

## 4) Playwright Test : config “Chrome only” + baseURL + artefacts

Créer/mettre à jour `src/frontend/apps/drive/playwright.config.ts` :

```ts
import { defineConfig } from '@playwright/test';

export default defineConfig({
  use: {
    // UI Next.js (conteneur Docker) vue depuis le host
    baseURL: process.env.BASE_URL ?? 'http://127.0.0.1:3000',

    // Chrome uniquement (Chrome installé sur le host)
    browserName: 'chromium',
    channel: 'chrome',

    // Artefacts pour debug autonome de l’agent
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
});
```

Docs :
- `baseURL` et options `use`: https://playwright.dev/docs/test-use-options  
- Options Playwright Test : https://playwright.dev/docs/api/class-testoptions

### Scripts Yarn recommandés

Dans `src/frontend/apps/drive/package.json` :

```json
{
  "scripts": {
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui"
  }
}
```

### Exécuter les tests (depuis le host)

```bash
cd src/frontend/apps/drive
BASE_URL=http://127.0.0.1:3000 yarn test:e2e
```

---

## 5) Auth (Drive + Keycloak) : comptes E2E et “storageState”

Ce repo embarque déjà des utilisateurs Keycloak importés (voir `docker/auth/realm.json`). Pour Chrome, tu peux utiliser par exemple :
- `user-e2e-chromium` / `password-e2e-chromium`

Recommandation anti-flakiness : générer un `storageState.json` (cookies/session) et le réutiliser dans les tests.
Deux approches :
1) **Global setup** Playwright (recommandé) : un script de login Keycloak qui sauvegarde `storageState`.
2) **Codegen / UI** Playwright pour capturer une session (utile pour bootstrap rapide).

Option codegen (Chrome) :

```bash
cd src/frontend/apps/drive
npx playwright codegen --channel=chrome http://127.0.0.1:3000
```

---

## 6) Playwright MCP : donner un navigateur “outil” à l’agent (sur le host)

Playwright MCP est un serveur MCP qui expose des actions navigateur via Playwright.  
Repo/README : https://github.com/microsoft/playwright-mcp

### 6.1 Démarrage simple (stdio, local)

Dans beaucoup de clients MCP, une config “standard” ressemble à ceci (exemple JSON) :

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"]
    }
  }
}
```

> Variante utile (isolation + storage state) montrée dans le README :  
> `--isolated` et `--storage-state=...` pour contrôler l’état de session (cookies/login).  
> Voir README : https://raw.githubusercontent.com/microsoft/playwright-mcp/main/README.md

### 6.2 Utiliser Chrome côté MCP

- Si ton host a Google Chrome installé, Playwright peut le lancer via `channel: "chrome"` (même principe que les tests).
- Selon le client MCP/agent, tu peux :
  1) laisser Playwright MCP utiliser sa config par défaut, **ou**
  2) fournir une config/flags pour forcer Chrome (si ton agent le supporte), **ou**
  3) dire à l’agent d’utiliser le même environnement que Playwright Test (Chrome installé sur host).

*(Les options exactes dépendent du client MCP utilisé. L’essentiel pour toi : Chrome doit être présent sur le host.)*

---

## 7) Runbook : ce que l’agent doit faire “sans toi”

### 7.1 Démarrage
1) Démarrer la stack Docker :
   ```bash
   docker compose up -d
   ```
2) Attendre que l’UI réponde :
   ```bash
   curl -fsSI http://127.0.0.1:3000 >/dev/null
   ```
3) Explorer via Playwright MCP si nécessaire (repro/inspection).
4) (Re)générer/mettre à jour les tests Playwright dans `src/frontend/apps/drive/` (ex: dossier `e2e/`).
5) Lancer les tests (Chrome only) :
   ```bash
   cd src/frontend/apps/drive
   BASE_URL=http://127.0.0.1:3000 yarn test:e2e
   ```
6) Si échec :
   - lire la trace/screenshot/video
   - proposer un correctif (test ou app)
   - relancer jusqu’à succès

### 7.2 Conventions anti-flakiness (à imposer à l’agent)
- Préférer des sélecteurs stables : `data-testid`
- Éviter les `sleep` arbitraires ; utiliser les attentes Playwright
- Toujours conserver des artefacts à l’échec (déjà configuré)

---

## 8) Dépannage rapide (Drive)

### “Le host ne voit pas le serveur”
- Vérifier `ports:` dans docker compose
- Vérifier que Next.js écoute `0.0.0.0` dans le conteneur (voir section 3.1)

### “Playwright n’utilise pas Chrome”
- Vérifier que Google Chrome est installé sur le host
- Vérifier `browserName: "chromium"` + `channel: "chrome"`  
  Doc Playwright browsers : https://playwright.dev/docs/browsers

---

## 9) Checklist (copier/coller)

- [ ] `docker compose up -d` OK
- [ ] Depuis le host : `curl -I http://127.0.0.1:3000` OK
- [ ] Keycloak OK : `curl -I http://127.0.0.1:8083/realms/drive/.well-known/openid-configuration` OK
- [ ] `src/frontend/apps/drive/playwright.config.ts` : `channel: "chrome"` + `baseURL`
- [ ] `cd src/frontend/apps/drive && yarn test:e2e` marche depuis le host
- [ ] Playwright MCP déclaré dans la config MCP du client/agent
