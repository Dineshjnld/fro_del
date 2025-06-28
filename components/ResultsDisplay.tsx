
import React from 'react';
import type { QueryResult, Status } from '../types';
import { DataTable } from './DataTable';
import { SpinnerIcon } from './icons/SpinnerIcon';
import { DatabaseIcon } from './icons/DatabaseIcon';

interface ResultsDisplayProps {
  result: QueryResult | null;
  status: Status;
}

export const ResultsDisplay: React.FC<ResultsDisplayProps> = ({ result, status }) => {
  const renderContent = () => {
    if (status === 'loading' && !result) {
      return (
        <div className="flex flex-col items-center justify-center h-full text-gray-500">
          <SpinnerIcon className="w-12 h-12" />
          <p className="mt-4 text-lg">Executing Query...</p>
        </div>
      );
    }
    if (result) {
      return <DataTable data={result} />;
    }
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-400 text-center px-8">
        <DatabaseIcon />
        <h3 className="mt-4 text-2xl font-semibold text-gray-600">Results Panel</h3>
        <p className="mt-2">Query results and visualizations will appear here.</p>
      </div>
    );
  };

  return (
    <aside className="w-1/2 border-l border-gray-200 bg-white shadow-lg flex flex-col overflow-hidden">
        {renderContent()}
    </aside>
  );
};
