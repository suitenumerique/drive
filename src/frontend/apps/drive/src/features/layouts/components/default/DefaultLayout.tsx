import { Header } from "../header/Header";

/**
 * It is used to display the header.
 */

export const DefaultLayout = ({ children }: { children: React.ReactNode }) => {
  return (
    <div>
      <Header />
      {children}
    </div>
  );
};
