# AudioPlayer Component

Un lecteur audio personnalisé basé sur l'élément HTML `<audio>` avec une interface moderne et des contrôles complets.

## Fonctionnalités

- ✅ Lecture/Pause avec bouton central
- ✅ Barre de progression interactive (seek)
- ✅ Contrôle du volume avec bouton mute
- ✅ Affichage du temps écoulé/total
- ✅ Design responsive
- ✅ Support du mode sombre
- ✅ Accessibilité (focus, aria-labels)
- ✅ Callbacks pour synchronisation
- ✅ Auto-play optionnel
- ✅ Gestion des événements audio

## Utilisation

### Import

```tsx
import { AudioPlayer } from '@/features/ui/components/audio-player';
```

### Exemple basique

```tsx
<AudioPlayer
  src="/path/to/audio.mp3"
  title="Nom de la piste"
  artist="Nom de l'artiste"
/>
```

### Exemple complet avec callbacks

```tsx
<AudioPlayer
  src="/path/to/audio.mp3"
  title="Nom de la piste"
  artist="Nom de l'artiste"
  autoPlay={false}
  onPlay={() => console.log('Audio started')}
  onPause={() => console.log('Audio paused')}
  onEnded={() => console.log('Audio ended')}
  onTimeUpdate={(currentTime) => console.log('Current time:', currentTime)}
/>
```

## Props

| Prop | Type | Défaut | Description |
|------|------|--------|-------------|
| `src` | `string` | **requis** | URL du fichier audio |
| `title` | `string` | `'Audio Track'` | Titre de la piste |
| `artist` | `string` | `'Unknown Artist'` | Nom de l'artiste |
| `className` | `string` | `undefined` | Classe CSS personnalisée |
| `autoPlay` | `boolean` | `false` | Lecture automatique au chargement |
| `onPlay` | `() => void` | `undefined` | Callback appelé lors de la lecture |
| `onPause` | `() => void` | `undefined` | Callback appelé lors de la pause |
| `onEnded` | `() => void` | `undefined` | Callback appelé à la fin de l'audio |
| `onTimeUpdate` | `(currentTime: number) => void` | `undefined` | Callback appelé à chaque mise à jour du temps |

## Événements

Le composant utilise l'élément HTML `<audio>` en arrière-plan et expose les événements suivants :

- `onLoadedMetadata` : Déclenché quand les métadonnées sont chargées
- `onTimeUpdate` : Déclenché à chaque mise à jour du temps de lecture
- `onPlay` : Déclenché quand l'audio commence à jouer
- `onPause` : Déclenché quand l'audio est mis en pause
- `onEnded` : Déclenché quand l'audio se termine

## Styles

Le composant utilise les variables CSS de Cunningham pour s'adapter automatiquement au thème :

- `--c--theme--colors--primary-500` : Couleur principale
- `--c--theme--colors--background-500` : Couleur de fond
- `--c--theme--colors--border-500` : Couleur des bordures
- `--c--theme--colors--text-500` : Couleur du texte

## Accessibilité

- Tous les boutons ont des `aria-label` appropriés
- Support de la navigation au clavier
- Indicateurs de focus visibles
- Structure sémantique correcte

## Responsive

Le composant s'adapte automatiquement aux écrans mobiles :
- Réorganisation des contrôles en mode portrait
- Tailles adaptées pour les écrans tactiles
- Optimisation de l'espace disponible

## Exemple d'intégration dans une playlist

```tsx
import React, { useState } from 'react';
import { AudioPlayer } from '@/features/ui/components/audio-player';

const PlaylistExample: React.FC = () => {
  const [currentTrack, setCurrentTrack] = useState(0);
  
  const tracks = [
    { src: '/audio/1.mp3', title: 'Track 1', artist: 'Artist 1' },
    { src: '/audio/2.mp3', title: 'Track 2', artist: 'Artist 2' },
    { src: '/audio/3.mp3', title: 'Track 3', artist: 'Artist 3' },
  ];

  const handleEnded = () => {
    setCurrentTrack((prev) => (prev + 1) % tracks.length);
  };

  return (
    <div>
      <AudioPlayer
        src={tracks[currentTrack].src}
        title={tracks[currentTrack].title}
        artist={tracks[currentTrack].artist}
        onEnded={handleEnded}
      />
      
      <div>
        {tracks.map((track, index) => (
          <button
            key={index}
            onClick={() => setCurrentTrack(index)}
            className={currentTrack === index ? 'active' : ''}
          >
            {track.title} - {track.artist}
          </button>
        ))}
      </div>
    </div>
  );
};
```

## Support des formats

Le composant supporte tous les formats audio supportés par le navigateur :
- MP3
- WAV
- OGG
- AAC
- WebM

## Limitations

- Dépend des capacités audio du navigateur
- L'auto-play peut être bloqué par les politiques du navigateur
- Le volume peut être limité par les paramètres système 