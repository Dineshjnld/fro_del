import React from 'react';
import { PoliceIcon } from './icons/PoliceIcon';

export const Header: React.FC = () => {
  return (
    <header className="bg-white shadow-md px-6 py-3 flex items-center justify-between z-10">
      <div className="flex items-center space-x-3">
        <div className="text-blue-800">
          <PoliceIcon />
        </div>
        <h1 className="text-2xl font-bold text-gray-800 tracking-tight">
          CCTNS Copilot
        </h1>
      </div>
       <div className="text-sm text-gray-500">
        Andhra Pradesh Police
      </div>
    </header>
  );
};
