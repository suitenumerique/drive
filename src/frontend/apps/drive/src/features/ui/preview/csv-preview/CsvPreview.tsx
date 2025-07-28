import React, { useEffect } from 'react';

interface PreviewCsvProps {
    title?: string;
    src?: string;
  }
  
  export const PreviewCsv = ({ src, title }: PreviewCsvProps) => {
    useEffect(() => {
      if (src) {
        const script = document.createElement('script');
        script.src = 'https://grist-static.com/csv-viewer.js';
        document.body.appendChild(script);
      }
    }, [src]);
    return (
        <div className='csv-preview'>
        <div className='csv-preview__app'>
            <csv-viewer className='csv-preview' initial-data="/csvtest.csv" single-page="true" loader="true">
            </csv-viewer>
        </div>
    </div>
    );
  };