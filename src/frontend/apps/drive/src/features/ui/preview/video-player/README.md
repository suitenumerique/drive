# VideoPlayer Component

Un lecteur vidéo personnalisé avec des contrôles custom pour React/Next.js, utilisant l'API HTML5 Video et les styles Cunningham.

## Fonctionnalités

- 🎮 Contrôles personnalisés avec design moderne
- ⏯️ Lecture/Pause avec icônes Material Design
- 🔊 Contrôle du volume avec barre de progression
- 🔇 Bouton mute/unmute
- ⏱️ Affichage du temps de lecture
- 📊 Barre de progression pour naviguer dans la vidéo
- 🖥️ Mode plein écran avec contrôles natifs du navigateur
- 📱 Design responsive pour mobile
- 🌙 Support du thème sombre
- ⏰ Auto-hide des contrôles après 3 secondes (mode normal uniquement)
- 📍 Contrôles positionnés en dessous du lecteur (mode normal)

## Installation

Le composant utilise les dépendances déjà présentes dans le projet :
- `@openfun/cunningham-react` pour les composants UI
- `clsx` pour la gestion des classes CSS
- `react` et `react-dom` pour React

## Utilisation

```tsx
import { VideoPlayer } from './components/VideoPlayer';

function MyComponent() {
  const handlePlay = () => {
    console.log('Video started playing');
  };

  const handlePause = () => {
    console.log('Video paused');
  };

  const handleEnded = () => {
    console.log('Video ended');
  };

  const handleTimeUpdate = (currentTime: number) => {
    console.log('Current time:', currentTime);
  };

  return (
    <VideoPlayer
      src="https://example.com/video.mp4"
      poster="https://example.com/poster.jpg"
      autoPlay={false}
      muted={false}
      loop={false}
      controls={true}
      width="100%"
      height="auto"
      onPlay={handlePlay}
      onPause={handlePause}
      onEnded={handleEnded}
      onTimeUpdate={handleTimeUpdate}
    />
  );
}
```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `src` | `string` | **requis** | URL de la vidéo |
| `poster` | `string` | `undefined` | URL de l'image de poster |
| `className` | `string` | `undefined` | Classe CSS personnalisée |
| `autoPlay` | `boolean` | `false` | Lecture automatique |
| `muted` | `boolean` | `false` | Vidéo en sourdine |
| `loop` | `boolean` | `false` | Lecture en boucle |
| `controls` | `boolean` | `true` | Afficher les contrôles |
| `width` | `string \| number` | `'100%'` | Largeur du lecteur |
| `height` | `string \| number` | `'auto'` | Hauteur du lecteur |
| `onPlay` | `() => void` | `undefined` | Callback appelé au début de la lecture |
| `onPause` | `() => void` | `undefined` | Callback appelé à la pause |
| `onEnded` | `() => void` | `undefined` | Callback appelé à la fin de la vidéo |
| `onTimeUpdate` | `(currentTime: number) => void` | `undefined` | Callback appelé à chaque mise à jour du temps |

## Événements

Le composant émet plusieurs événements que vous pouvez écouter :

- `onPlay` : Déclenché quand la vidéo commence à jouer
- `onPause` : Déclenché quand la vidéo est mise en pause
- `onEnded` : Déclenché quand la vidéo se termine
- `onTimeUpdate` : Déclenché à chaque mise à jour du temps de lecture

## Modes d'affichage

### Mode normal
- Les contrôles personnalisés sont affichés en dessous du lecteur vidéo
- Design moderne avec fond clair et bordures
- Auto-hide des contrôles après 3 secondes d'inactivité
- Contrôles réapparaissent au survol de la souris

### Mode plein écran
- Utilise automatiquement les contrôles natifs du navigateur
- Les contrôles personnalisés sont masqués
- Meilleure compatibilité avec les raccourcis clavier du navigateur
- Retour automatique aux contrôles personnalisés en sortant du plein écran

## Styles

Le composant utilise SCSS avec la méthodologie BEM. Les styles sont inclus dans `VideoPlayer.scss` et incluent :

- Design responsive pour mobile et desktop
- Contrôles positionnés en dessous du lecteur
- Support du mode plein écran avec contrôles natifs
- Thème sombre automatique
- Animations et transitions fluides
- Contrôles avec effet hover

## Personnalisation

Vous pouvez personnaliser l'apparence en modifiant le fichier `VideoPlayer.scss` ou en passant une classe CSS personnalisée via la prop `className`.

## Exemple complet

Voir `VideoPlayerExample.tsx` pour un exemple complet d'utilisation avec plusieurs vidéos et fonctionnalités avancées.

## Compatibilité

- React 18+
- Next.js 13+
- Navigateurs modernes supportant l'API HTML5 Video
- Support complet des formats vidéo web standards (MP4, WebM, Ogg)

## Notes techniques

- Utilise l'API HTML5 Video native pour de meilleures performances
- Gestion automatique du plein écran avec l'API Fullscreen
- Basculement automatique entre contrôles personnalisés et natifs
- Optimisé pour les performances avec `useCallback` et `useMemo`
- Support des contrôles tactiles pour les appareils mobiles 