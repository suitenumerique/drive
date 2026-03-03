# Feature: Custom Columns

> **Note** : Ce fichier est une documentation temporaire de la feature. Il sera supprimé avant le merge.

## Vue d'ensemble

La feature permet aux utilisateurs de **personnaliser les 2 colonnes d'information** affichées dans le tableau de l'explorateur de fichiers, et de **trier** par n'importe quelle colonne. Les préférences sont persistées en `localStorage`.

Les 5 types de colonnes disponibles sont :
- **Dernière modification** (`updated_at`)
- **Date de création** (`created_at`)
- **Créé par** (`creator__full_name`)
- **Type de fichier** (`type`)
- **Taille** (`size`)

---

## Architecture en couches

```
┌─────────────────────────────────────────────────┐
│  ExplorerLayout (ColumnPreferencesProvider)      │  ← Context React global
├─────────────────────────────────────────────────┤
│  Pages: [id].tsx, recent.tsx, trash/index.tsx    │  ← Appelle useGridColumns()
│         WorkspacesExplorer.tsx                   │
├─────────────────────────────────────────────────┤
│  AppExplorer → AppExplorerGrid                   │  ← Passe les props
├─────────────────────────────────────────────────┤
│  EmbeddedExplorerGrid                            │  ← Rend les colonnes dynamiques
├──────────┬──────────┬───────────────────────────┤
│  Headers │  Cells   │  Config/Store/Utils        │  ← Briques de base
└──────────┴──────────┴───────────────────────────┘
```

---

## Arborescence des nouveaux fichiers

```
src/frontend/apps/drive/src/features/explorer/
├── types/
│   ├── columns.ts              # ColumnType enum, SortState, ColumnPreferences, ColumnConfig
│   └── viewConfig.ts           # FolderMode, ViewConfig
├── config/
│   ├── columnRegistry.tsx      # Registre central ColumnType → ColumnConfig
│   └── viewConfigs.ts          # Config par vue (tri par défaut, mode dossier)
├── store/
│   ├── columnPreferences.ts    # Persistance localStorage
│   └── __tests__/
│       └── columnPreferences.test.ts
├── hooks/
│   ├── useColumnPreferences.tsx  # React Context (Provider + hook)
│   └── useGridColumns.ts        # Hook principal d'orchestration
├── utils/
│   ├── ordering.ts              # computeOrdering(), computeFilters()
│   └── __tests__/
│       └── ordering.test.ts
├── components/embedded-explorer/
│   ├── cells/
│   │   ├── LastModifiedCell.tsx
│   │   ├── CreatedCell.tsx
│   │   ├── CreatedByCell.tsx
│   │   ├── FileTypeCell.tsx
│   │   └── FileSizeCell.tsx
│   └── headers/
│       ├── SortColumnButton.tsx
│       ├── SortableColumnHeader.tsx
│       └── CustomizableColumnHeader.tsx

src/frontend/apps/drive/src/features/ui/components/icon/
├── Clock.tsx
├── PersoIcon.tsx
├── FileIcon.tsx
├── WeightIcon.tsx
└── sorting/
    ├── sort-asc.tsx
    ├── sort-desc.tsx
    └── sort-neutral.tsx
```

---

## Détail par couche

### 1. Types (`types/`)

#### `types/columns.ts`

Définit le vocabulaire de la feature :
- **`ColumnType`** : enum avec les 5 types (`LAST_MODIFIED`, `CREATED`, `CREATED_BY`, `FILE_TYPE`, `FILE_SIZE`)
- **`SortState`** : `{ columnId, direction }` ou `null` (pas de tri)
- **`ColumnPreferences`** : `{ column1: ColumnType, column2: ColumnType }`
- **`ColumnConfig`** : structure décrivant une colonne (label i18n, icone, champ backend, composant cell)
- **`DEFAULT_COLUMN_PREFERENCES`** : dernière modif + créé par

#### `types/viewConfig.ts`

- **`FolderMode`** : `"files_only"` | `"folders_first"` | `"mixed"`
- **`ViewConfig`** : configuration par vue (tri par défaut + mode dossier)

---

### 2. Configuration (`config/`)

#### `config/columnRegistry.tsx`

Le **registre central** qui mappe chaque `ColumnType` vers sa config complète :

```
LAST_MODIFIED → { label: "...", icon: <Clock/>, orderingField: "updated_at", cell: LastModifiedCell }
FILE_SIZE     → { label: "...", icon: <Weight/>, orderingField: "size", cell: FileSizeCell }
...
```

Pour ajouter une nouvelle colonne, il suffit d'ajouter une entrée ici.

#### `config/viewConfigs.ts`

Configuration par route/vue :
- **Recent** : `files_only`, tri par `-updated_at`
- **My Files** : `folders_first`, tri par `-type,title`
- **Trash** : `folders_first`, tri par `-type,-updated_at`
- etc.

Chaque vue a son propre tri par défaut et son comportement dossiers/fichiers.

---

### 3. Store (`store/`)

#### `store/columnPreferences.ts`

Couche de persistance `localStorage` :
- Clé : `"drive:column-preferences"`
- `get()` : lit les prefs ou retourne les defaults
- `set(prefs)` : sauvegarde
- Gère le JSON corrompu gracieusement

#### `store/__tests__/columnPreferences.test.ts`

Tests unitaires : localStorage vide, JSON corrompu, persistence correcte, persistence entre instances.

---

### 4. Hooks (`hooks/`)

#### `hooks/useColumnPreferences.tsx`

**React Context** qui fournit les préférences à toute l'app :
- `ColumnPreferencesProvider` : wraps l'app, initialisé avec le store localStorage
- `useColumnPreferences()` : retourne `{ prefs, setColumn(slot, type) }`
- Quand on change une colonne, met à jour le state React ET le localStorage

#### `hooks/useGridColumns.ts`

**Le hook principal** qui orchestre tout :
- Prend un `viewConfigKey` (ex: `"RECENT"`) et un `navigationId` optionnel
- Retourne :
  - `col1Config`, `col2Config` : configs des 2 colonnes
  - `sortState` : état du tri
  - `cycleSortForColumn()` : bascule `null → asc → desc → null`
  - `setColumn()` : change une colonne
  - `ordering` : string d'ordering pour l'API (ex: `"-updated_at"`)
  - `viewConfig` : config de la vue courante
- Reset le tri quand on change de vue/navigation

---

### 5. Utilitaires (`utils/`)

#### `utils/ordering.ts`

Logique métier pure (pas de React) :
- **`computeOrdering(viewConfig, sortState)`** : calcule la string d'ordering
  - Pas de tri actif → utilise le `defaultOrdering` de la vue
  - Tri actif → retourne le champ avec préfixe `-` si descendant
- **`computeFilters(viewConfig, baseFilters, sortState)`** : merge le tri dans les filtres API
  - Ajoute `type=file` pour les vues `files_only`
  - Préserve tous les filtres existants

#### `utils/__tests__/ordering.test.ts`

~65 assertions : tri par défaut par vue, asc/desc par colonne, filtrage par mode dossier.

---

### 6. Composants Cell (`cells/`)

Chacun rend le contenu d'une cellule du tableau pour un type de colonne :

| Composant | Données affichées |
|-----------|-------------------|
| `LastModifiedCell` | Temps relatif (il y a 2h) + tooltip date complète |
| `CreatedCell` | Idem mais `created_at` |
| `CreatedByCell` | Nom complet du créateur |
| `FileSizeCell` | Taille formatée, ou "-" pour les dossiers |
| `FileTypeCell` | Type traduit, ou "Dossier" |

Tous wrappent leur contenu dans `<Draggable>` pour le drag-and-drop.

---

### 7. Composants Header (`headers/`)

#### `SortableColumnHeader.tsx`

Header simple (pour la colonne "Name") : label + bouton de tri.

#### `SortColumnButton.tsx`

Bouton de tri avec 3 états visuels :
- Neutre (gris) → clic = asc
- Asc (bleu, flèche haut) → clic = desc
- Desc (bleu, flèche bas) → clic = reset

#### `CustomizableColumnHeader.tsx`

Header des colonnes configurables avec **dropdown** :
- Affiche l'icone + nom de la colonne actuelle
- Menu déroulant pour choisir parmi les 5 types
- Marque "(default)" sur les colonnes par défaut
- Inclut le bouton de tri

---

### 8. Icones (`ui/components/icon/`)

- `Clock.tsx` : pour Last Modified / Created
- `PersoIcon.tsx` : pour Created By
- `FileIcon.tsx` : pour File Type
- `WeightIcon.tsx` : pour File Size
- `sorting/sort-asc.tsx`, `sort-desc.tsx`, `sort-neutral.tsx` : icones de tri

---

### 9. Fichiers modifiés existants

#### Pages (`pages/explorer/`)

**`[id].tsx`**, **`recent.tsx`**, **`trash/index.tsx`** : chaque page utilise maintenant `useGridColumns(route)` pour obtenir l'état des colonnes, appelle `computeFilters()` pour merger le tri dans les filtres API, et passe toutes les props colonnes à `AppExplorer`.

#### `WorkspacesExplorer.tsx`

Même pattern que les pages ci-dessus.

#### `AppExplorer.tsx` → `AppExplorerGrid.tsx`

Ajout de props pour faire transiter les données colonnes : `sortState`, `onSort`, `prefs`, `onChangeColumn`, `col1Config`, `col2Config`.

#### `EmbeddedExplorerGrid.tsx`

**Le plus gros changement** : remplace la colonne "Last Update" en dur par 2 colonnes dynamiques dont le contenu vient de `col1Config`/`col2Config`. Largeurs : Name 40%, col1 22%, col2 22%, actions 5%.

#### `ExplorerLayout.tsx`

Wrappe toute l'app avec `<ColumnPreferencesProvider>` pour que le context soit disponible partout.

#### `Driver.ts` / `StandardDriver.ts`

- Ajout des valeurs `SIZE_ASC/DESC`, `CREATOR_ASC/DESC` dans l'enum d'ordering
- Suppression de l'ordering par défaut hardcodé pour permettre l'ordering dynamique

#### `translations.json`

Traductions FR/EN/NL pour les noms de colonnes, labels de tri, etc.

#### `EmbeddedExplorer.scss`

Styles des headers, boutons de tri, et gestion responsive.

---

### 10. Backend

#### `viewsets.py`

Ajout de `"creator__full_name"` et `"size"` dans `ordering_fields` du viewset Django REST Framework.

#### Tests backend

Tests pour valider le tri par taille et par créateur (asc/desc) sur les endpoints `list` et `children`.

---

## Flux de données

### Quand l'utilisateur clique sur le bouton de tri

```
SortColumnButton.onClick
  → cycleSortForColumn(columnId)
  → setSortState()
  → computeOrdering()
  → computeFilters()
  → API call avec ?ordering=-size
  → Backend trie
  → Résultats affichés
```

### Quand l'utilisateur change une colonne

```
CustomizableColumnHeader.dropdown
  → setColumn(slot, type)
  → ColumnPreferencesProvider.setState + localStorage.set
  → useGridColumns lit les nouvelles prefs
  → col1Config/col2Config changent
  → EmbeddedExplorerGrid re-render avec le nouveau cell component
```

---

## Extensibilité

Pour ajouter un 6e type de colonne, il faut :
1. Ajouter une valeur dans l'enum `ColumnType`
2. Créer un composant cell (`cells/NewCell.tsx`)
3. Ajouter une entrée dans `columnRegistry.tsx`
4. Ajouter le champ backend dans `ordering_fields` si nécessaire
