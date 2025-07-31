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
              // Todo: need to make a PR in grist-static to fetch with credentials
                initialFile: "/gristtest.grist",
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