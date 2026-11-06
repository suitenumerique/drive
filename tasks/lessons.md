# Lessons learned

## Versioning (issue #638)
- Versioning s'applique uniquement aux fichiers (`ItemTypeChoices.FILE`), jamais aux dossiers — vérifier le type dans le service et dans les abilities.
- La clé de stockage d'une version doit être un **sous-chemin de l'item** (`item/{pk}/versions/{n}/{filename}`) pour que le mécanisme de media-auth (pattern nginx `item/{pk}/...`) continue de fonctionner sans config supplémentaire.
- `snapshot_version` doit se garder de copier si l'objet source (`item.file_key`) n'existe pas encore dans l'object storage, sinon S3 lève `ClientError` ; retourner `None` et laisser l'écrasement se produire normalement.
- Le cap de versions (`MAX_ITEM_VERSIONS`, défaut 5) porte sur les versions **stockées** ; le fichier courant est distinct et n'est pas compté dans le cap.
- Restaurer une version doit d'abord auteuriser l'état courant (sinon on perdrait le contenu actuel) puis supprimer l'enregistrement de version restaurée pour éviter les doublons.
- Recharger `settings.MAX_ITEM_VERSIONS` au moment de l'appel (pas à l'import) pour que les tests puissent le surpasser via un override de settings.
- Le `ItemVersionPermission` doit lire `view.item` (défini pendant le lookup) plutôt qu'un attribut sur l'item, car le viewset nested expose l'item via `view.item`.
- Frontend : les icônes ui-kit (`History`, `Restore`, `Download`, `Trash`) sont des exports nommés Material PascalCase du bundle `@gouvfr-lasuite/ui-kit/icons` — à vérifier dans le bundle publié quand node_modules n'est pas installé (`curl unpkg .../dist/icons.js`).
- La modale est câblée via `useItemActionMenuItems` (modale ajoutée à `isModalOpen` + rendu dans `modals`), elle même réutilisée par `ItemActionDropdown`.
- Les mutations versioning passent par le **Driver** (interface + `StandardDriver`) et non par des appels fetch directs, conformément à l'architecture du frontend.
