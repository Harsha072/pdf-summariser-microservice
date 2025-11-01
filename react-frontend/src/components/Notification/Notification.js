import React from 'react';
import './Notification.css';
import { useNotification } from '../../context/NotificationContext';

const Notification = () => {
  const { notifications, removeNotification } = useNotification();

  if (notifications.length === 0) return null;

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'success':
        return 'fas fa-check-circle';
      case 'error':
        return 'fas fa-exclamation-circle';
      case 'warning':
        return 'fas fa-exclamation-triangle';
      default:
        return 'fas fa-info-circle';
    }
  };

  return (
    <div className="notification-container">
      {notifications.map((notification) => (
        <div 
          key={notification.id}
          className={`notification notification-${notification.type}`}
        >
          <div className="notification-content">
            <i className={`notification-icon ${getNotificationIcon(notification.type)}`}></i>
            <span className="notification-message">{notification.message}</span>
          </div>
          <button 
            className="notification-close"
            onClick={() => removeNotification(notification.id)}
          >
            <i className="fas fa-times"></i>
          </button>
        </div>
      ))}
    </div>
  );
};

export default Notification;