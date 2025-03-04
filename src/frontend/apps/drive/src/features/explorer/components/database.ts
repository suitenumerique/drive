import { Item } from "@/features/drivers/types";

import { ItemType } from "@/features/drivers/types";

export const database: Item[] = [
  {
    id: "1",
    type: ItemType.FOLDER,
    name: "Projets en cours",
    lastUpdate: "Il y a 5h",
  },
  {
    id: "2",
    type: ItemType.FOLDER,
    name: "Archives dernières années",
    lastUpdate: "Il y a 5h",
  },
  {
    id: "3",
    type: ItemType.FOLDER,
    name: "Resources juridiques",
    lastUpdate: "Il y a 5h",
  },
  {
    id: "4",
    type: ItemType.FOLDER,
    name: "Présentation nouveau logo",
    lastUpdate: "Il y a 5h",
  },
  {
    id: "5",
    type: ItemType.FOLDER,
    name: "Comptabilité hebdomadaire",
    lastUpdate: "Il y a 5h",
  },
  {
    id: "6",
    type: ItemType.FOLDER,
    name: "Présentation nouveau logo",
    lastUpdate: "Il y a 5h",
  },
  {
    id: "7",
    type: ItemType.FILE,
    name: "Rapport annuel 2024",
    lastUpdate: "Il y a 5h",
  },
  {
    id: "8",
    type: ItemType.FILE,
    name: "Fond d'écran",
    lastUpdate: "Il y a 5h",
  },
  {
    id: "9",
    type: ItemType.FILE,
    name: "Export utilisateurs",
    lastUpdate: "Il y a 5h",
  },
];
