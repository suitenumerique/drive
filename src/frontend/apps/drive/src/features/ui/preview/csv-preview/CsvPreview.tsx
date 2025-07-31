import React, { useEffect, useState } from 'react';

interface PreviewCsvProps {
    title?: string;
    src?: string;
  }
  
  export const PreviewCsv = ({ src, title }: PreviewCsvProps) => {

    const [csvContent, setCsvContent] = useState<string | null>(null);

    // Get grist-static csv script
    useEffect(() => {
      if (src) {
        // Load the grist csv viewer script dynamically
        const script = document.createElement('script');
        script.src = 'https://grist-static.com/csv-viewer.js';
        script.async = true;
        document.body.appendChild(script);
        
        // fetch CSV content
        fetch(src, { credentials: 'include' })
        .then(response => {
          if (!response.ok) {
            throw new Error(`Failed to fetch CSV content: ${response.statusText}`);
          }
          return response.text();
        })
        .then(text => {
          console.log("Fetched CSV content:", text);
          setCsvContent(text);
        })
        .catch(err => {
          console.error(err); // Optional: fallback or error handling
        });
      }
    }, [src]);

    return (
        <div className='csv-preview'>
        <div className='csv-preview__app'>
          {!!csvContent &&
            <csv-viewer className='csv-preview' initial-content={csvContent} single-page="true" loader="true"></csv-viewer>
          }
        </div>
    </div>
    );
  };