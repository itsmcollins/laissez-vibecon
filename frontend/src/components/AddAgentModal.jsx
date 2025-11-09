import React from 'react';
import { X } from 'lucide-react';
import { Button } from './ui/button';

export default function AddAgentModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div 
        className="bg-[#0f0f0f] border border-gray-700 rounded-lg max-w-2xl w-full p-8 relative"
        onClick={(e) => e.stopPropagation()}
        data-testid="add-agent-modal"
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-200"
          data-testid="close-modal-button"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Modal content */}
        <div className="space-y-6">
          <h2 className="text-2xl font-light text-gray-200 tracking-wide">Add New Agent</h2>
          <p className="text-sm text-gray-500">Content coming soon...</p>
        </div>
      </div>
    </div>
  );
}
