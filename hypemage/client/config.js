/**
 * Robot Configuration
 * 
 * Edit this file to configure your robots' IP addresses and ports.
 */

const ROBOT_CONFIG = {
    storm: {
        name: 'Storm',
        // Change this to your Storm robot's IP address or hostname
        host: '192.168.1.100',  // or 'storm.local'
        interfacePort: 8080,
        debugPort: 8765,
        icon: '⚡',
        color: '#00d4ff'
    },
    
    necron: {
        name: 'Necron',
        // Change this to your Necron robot's IP address or hostname
        host: '192.168.1.101',  // or 'necron.local'
        interfacePort: 8080,
        debugPort: 8765,
        icon: '💀',
        color: '#b74dff'
    }
};

// Default visible widgets for each robot
const DEFAULT_WIDGETS = ['controls', 'camera', 'motors', 'status'];

// Available widget types (easily add more!)
const WIDGET_TYPES = [
    { id: 'controls', name: 'Controls', icon: '🎮', defaultVisible: true },
    { id: 'camera', name: 'Camera', icon: '📷', defaultVisible: true },
    { id: 'motors', name: 'Motors', icon: '⚙️', defaultVisible: true },
    { id: 'localization', name: 'Position', icon: '📍', defaultVisible: false },
    { id: 'tof', name: 'ToF Sensors', icon: '📡', defaultVisible: false },
    { id: 'logs', name: 'Logs', icon: '📝', defaultVisible: false },
    { id: 'status', name: 'Status', icon: 'ℹ️', defaultVisible: true }
];

// Export configuration
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ROBOT_CONFIG, DEFAULT_WIDGETS, WIDGET_TYPES };
}
