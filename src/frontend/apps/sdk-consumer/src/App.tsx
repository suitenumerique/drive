import "./App.css";
import { openPicker, type PickerResult } from "@gouvfr-lasuite/drive-sdk";
import { useState } from "react";

const CONFIG = {};

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
    </div>
  );
}

export default App;
