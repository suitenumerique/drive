import React, { useEffect } from 'react';

interface PreviewGristProps {
    title?: string;
    src?: string;
  }
  
  export const PreviewGrist = ({ src, title }: PreviewGristProps) => {
    useEffect(() => {
      if (src) {
        const script = document.createElement('script');
        script.src = 'https://grist-static.com/latest.js';
        script.onload = () => {
        // Assuming bootstrapGrist is globally available
          if (window) {
            window.bootstrapGrist?.({
                initialFile: "/gristtest.grist", // Todo: use src instead (gots to figure out that CORS issue with NGINX...)
                name: title || "Grist document",
                elementId: 'grist-app',
                singlePage: false,
          });
        }};
        document.body.appendChild(script);
      }
    }, [src]);
    return (
    <div className='grist-preview'>
        <div id="grist-app" className='grist-preview__app'></div>
    </div>
    );
  };