# ImageViewer

Un composant React moderne pour visualiser des images avec fonctionnalités de zoom et de déplacement intelligent.

## Fonctionnalités

- **Zoom intelligent** : Zoom = 1 correspond à la taille originale de l'image quand possible
- **Adaptation automatique** : Si l'image originale ne rentre pas dans le conteneur, le zoom initial est ajusté
- **Zoom interactif** : Utilisez la molette de la souris ou les boutons pour zoomer/dézoomer
- **Déplacement intelligent** : Le déplacement ne s'active que quand l'image dépasse les limites du conteneur
- **Contraintes de déplacement** : L'image reste toujours visible, impossible de la faire sortir du conteneur
- **Raccourcis clavier** : + (zoom avant), - (zoom arrière), 0 (réinitialiser)
- **Interface responsive** : S'adapte aux différentes tailles d'écran
- **Accessibilité** : Support des préférences utilisateur (mode sombre, mouvement réduit, contraste élevé)
- **Chargement progressif** : Indicateur de chargement pendant le téléchargement de l'image

## Installation

Le composant est déjà inclus dans le projet. Importez-le simplement :

```typescript
import { ImageViewer } from '@/features/ui/components/image-viewer';
```

## Utilisation

### Utilisation basique

```tsx
import { ImageViewer } from '@/features/ui/components/image-viewer';

function MyComponent() {
  return (
    <div style={{ height: '500px' }}>
      <ImageViewer
        src="/path/to/your/image.jpg"
        alt="Description de l'image"
      />
    </div>
  );
}
```

### Utilisation avec options personnalisées

```tsx
<ImageViewer
  src="/path/to/your/image.jpg"
  alt="Description de l'image"
  initialZoom={1.5}
  minZoom={0.1}
  maxZoom={5}
  zoomStep={0.25}
  className="my-custom-class"
/>
```

## Props

| Prop | Type | Défaut | Description |
|------|------|--------|-------------|
| `src` | `string` | **requis** | URL de l'image à afficher |
| `alt` | `string` | `"Image"` | Texte alternatif pour l'accessibilité |
| `className` | `string` | `""` | Classe CSS personnalisée |
| `initialZoom` | `number` | `1` | Niveau de zoom initial (peut être recalculé automatiquement) |
| `minZoom` | `number` | `0.1` | Zoom minimum autorisé |
| `maxZoom` | `number` | `5` | Zoom maximum autorisé |
| `zoomStep` | `number` | `0.25` | Pas d'incrémentation du zoom |

## Comportement du zoom

### Zoom intelligent
Le composant calcule automatiquement le zoom optimal au chargement de l'image :

1. **Si l'image originale rentre dans le conteneur** :
   - Zoom = 1 correspond à la taille originale de l'image
   - L'image s'affiche à sa taille naturelle

2. **Si l'image originale ne rentre pas dans le conteneur** :
   - Le zoom initial est calculé pour que l'image s'adapte parfaitement au conteneur
   - Zoom = 1 correspond toujours à la taille originale, mais le zoom initial peut être < 1
   - L'image est redimensionnée pour tenir dans le conteneur

### Exemples de comportement
- **Image 800x600 dans un conteneur 1000x800** : Zoom initial = 1 (taille originale)
- **Image 1200x900 dans un conteneur 800x600** : Zoom initial = 0.67 (adapté au conteneur)
- **Image 2000x1500 dans un conteneur 500x400** : Zoom initial = 0.25 (adapté au conteneur)

## Interactions

### Souris
- **Molette** : Zoom avant/arrière
- **Clic + glisser** : Déplacement dans l'image (seulement si l'image dépasse les limites du conteneur)

### Clavier
- **+** ou **=** : Zoom avant
- **-** : Zoom arrière  
- **0** : Réinitialiser la vue (retour au zoom calculé automatiquement)

### Boutons
- **Bouton -** : Zoom arrière
- **Bouton +** : Zoom avant
- **Bouton reset** : Réinitialiser la vue

## Comportement intelligent

### Déplacement conditionnel
Le déplacement ne s'active que quand l'image dépasse les limites du conteneur (horizontalement ou verticalement). Cela signifie que :
- Si l'image est plus petite que le conteneur, le déplacement est désactivé
- Si l'image est zoomée et dépasse le conteneur, le déplacement devient disponible
- Le curseur change automatiquement pour indiquer si le déplacement est possible

### Contraintes de déplacement
L'image reste toujours visible dans le conteneur :
- Impossible de faire sortir l'image complètement du conteneur
- Les limites sont calculées automatiquement en fonction de la taille de l'image et du zoom
- Le déplacement est fluide et contraint aux limites calculées

### Calcul automatique des dimensions
- L'image s'affiche toujours à sa taille originale quand zoom = 1
- Si l'image originale ne rentre pas, le zoom initial est ajusté automatiquement
- Les proportions sont toujours préservées
- Le bouton reset ramène au zoom optimal calculé automatiquement

## Styles

Le composant utilise SCSS avec la méthodologie BEM. Les styles incluent :

- Design moderne et épuré
- Support du mode sombre
- Responsive design
- Animations fluides
- Support des préférences d'accessibilité
- Transitions de curseur intelligentes

### Personnalisation

Vous pouvez personnaliser l'apparence en surchargeant les classes CSS :

```scss
.image-viewer {
  // Vos styles personnalisés
  &__controls {
    // Personnalisation des contrôles
  }
  
  &__container {
    // Personnalisation du conteneur
  }
}
```

## Exemple complet

Voir `ImageViewerExample.tsx` pour un exemple d'utilisation complet avec sélection d'images.

## Accessibilité

Le composant respecte les standards d'accessibilité :

- Support des préférences `prefers-color-scheme: dark`
- Support des préférences `prefers-reduced-motion: reduce`
- Support des préférences `prefers-contrast: high`
- Navigation au clavier
- Textes alternatifs pour les images
- Indicateurs visuels pour les états interactifs
- Curseurs adaptatifs selon l'état de l'image

## Performance

- Utilisation de `useCallback` et `useMemo` pour optimiser les performances
- Gestion efficace des événements de souris et clavier
- Transitions CSS optimisées avec `will-change`
- Chargement progressif des images
- Calculs de contraintes optimisés
- Prévention de la sélection de texte pour une meilleure UX
- Calcul automatique du zoom optimal au chargement 