import React from 'react';
import {
  Laptop,
  Monitor,
  Server,
  Smartphone,
  Tablet,
  Tv,
  Cpu,
  HardDrive,
  Usb,
  Disc,
  Radio,
  Boxes,
  HelpCircle,
  LucideProps,
} from 'lucide-react';
import { DeviceCategory } from '../../types';

interface CategoryIconProps extends LucideProps {
  category?: DeviceCategory | string;
}

export const CategoryIcon: React.FC<CategoryIconProps> = ({ category, ...props }) => {
  switch (category) {
    case 'LAPTOP':
      return <Laptop {...props} />;
    case 'DESKTOP':
    case 'ALL_IN_ONE':
      return <Monitor {...props} />;
    case 'WORKSTATION':
    case 'SERVER':
      return <Server {...props} />;
    case 'PHONE':
      return <Smartphone {...props} />;
    case 'TABLET':
      return <Tablet {...props} />;
    case 'SMART_TV':
      return <Tv {...props} />;
    case 'SINGLE_BOARD_COMPUTER':
      return <Cpu {...props} />;
    case 'EXTERNAL_DRIVE':
      return <HardDrive {...props} />;
    case 'USB_FLASH':
      return <Usb {...props} />;
    case 'SD_CARD':
      return <Disc {...props} />;
    case 'NETWORK_DEVICE':
      return <Radio {...props} />;
    case 'OTHER':
      return <Boxes {...props} />;
    default:
      return <HelpCircle {...props} />;
  }
};
