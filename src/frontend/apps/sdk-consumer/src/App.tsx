import "./App.css";
import { openPicker, type Item } from "@gouvfr-lasuite/drive-sdk";
import { useState } from "react";

function App() {
  const [items, setItems] = useState<Item[]>([]);

  const pick = async () => {
    const { items } = await openPicker();
    console.log("Selected items:", items);
    setItems(items);
  };

  return (
    <div>
      <button onClick={pick}>Open picker</button>
      {items.length > 0 && (
        <div>
          <h3>Selected items:</h3>
          <ul>
            {items?.map((item) => (
              <li key={item.id}>
                {item.title} - {item.size} bytes
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default App;
