import "./App.css";
import {
  openPicker,
  openSaver,
  type Item,
  type PickerResult,
} from "@gouvfr-lasuite/drive-sdk";
import { useState } from "react";

const CONFIG = {
  // url: "https://fichiers.sardinepq.fr/sdk",
  // apiUrl: "https://fichiers.sardinepq.fr/api/v1.0",
};

function App() {
  const [pickerResult, setPickerResult] = useState<PickerResult | null>(null);
  const [picking, setPicking] = useState(false);

  const pick = async () => {
    setPicking(true);
    const result = await openPicker(CONFIG);
    console.log("Picker result:", result);
    setPickerResult(result);
    setPicking(false);
  };

  const save = async () => {
    // Example base64 image data
    const base64Image = "";

    // Convert base64 to blob
    const base64Response = await fetch(base64Image);
    const blob = await base64Response.blob();

    // Create File object from blob
    const file = new File([blob], "mon fichier.png", { type: "image/png" });

    await openSaver({
      files: [
        {
          title: "mon fichier.png",
          object: file,
        },
      ],
    });
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "1rem",
      }}
    >
      <button onClick={pick}>{picking ? "Picking..." : "Open picker"}</button>
      {pickerResult?.type === "cancelled" && (
        <div>
          <h3>Cancelled :(</h3>
        </div>
      )}
      {pickerResult?.type === "picked" && (
        <div>
          <h3>Selected items:</h3>
          <ul>
            {pickerResult.items?.map((item) => (
              <li key={item.id}>
                {item.title} - {item.size} bytes{" "}
                <a href={item.url}>{item.url}</a>
              </li>
            ))}
          </ul>
        </div>
      )}
      <button onClick={save}>Open saver</button>
    </div>
  );
}

export default App;
