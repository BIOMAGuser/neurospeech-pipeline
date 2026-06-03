import * as React from 'react';
import { Button } from '@/components/ui/button';
import { X } from 'lucide-react';

interface CookieTheftPictureProps {
  isVisible: boolean;
  onClose: () => void;
}

const CookieTheftPicture: React.FC<CookieTheftPictureProps> = ({ isVisible, onClose }) => {
  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg p-6 max-w-4xl max-h-[90vh] w-full mx-4 flex flex-col">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-gray-800">Bildbeschreibung</h2>
          <Button
            onClick={onClose}
            variant="outline"
            size="sm"
            className="hover:bg-gray-100"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
        
        <div className="flex-1 overflow-y-auto">
          <div className="flex justify-center">
            <div className="border-2 border-gray-300 rounded-lg p-4 bg-gray-50">
              <img 
                src="/cookie-theft-picture.png"
                alt="Cookie Theft Picture - Klassisches neuropsychologisches Testbild"
                className="max-w-full h-auto border border-gray-300 rounded shadow-sm"
                style={{ maxHeight: '400px', maxWidth: '600px' }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CookieTheftPicture;
