import { useEffect, useState } from "react";

// How long the pointer rests on an element before its tooltip shows, as a
// `title` would.
const TOOLTIP_REST_MS = 500;

/** Pass to the Tooltip whose content is a RestedTooltipText. */
export const RESTED_TOOLTIP_CLASS = "drive__encryption-rested-tooltip";

/**
 * A tooltip's content, mounted when the tooltip opens: marks itself rested
 * once the pointer stayed, which reveals the tooltip (see
 * .drive__encryption-rested-tooltip). The design system's Tooltip has no delay.
 */
export const RestedTooltipText = ({ text }: { text: string }) => {
  const [rested, setRested] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setRested(true), TOOLTIP_REST_MS);
    return () => clearTimeout(timer);
  }, []);

  return (
    <span
      className={
        rested ? "drive__encryption-rested-tooltip__rested" : undefined
      }
    >
      {text}
    </span>
  );
};
